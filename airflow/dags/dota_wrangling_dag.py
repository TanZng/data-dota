import airflow
import datetime
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.postgres_operator import PostgresOperator

def mock_injestions(stash_file):
    import json, pymongo as pm
    mongo_client = pm.MongoClient("mongodb://mongo:27017/")
    id_db = mongo_client['match_ids']

    id_db.match_details.drop()

    match_details = json.loads(open(stash_file,'r').read())

    id_db.match_details.insert_many(match_details)


def select_attributes():
    import pymongo as pm
    mongo_client = pm.MongoClient("mongodb://mongo:27017/")
    id_db = mongo_client['match_ids']

    wrangling_db = mongo_client['wrangling_match_details']
    wrangling_db.match_details.drop()

    match_details = id_db.match_details.find()

    for match_detail in match_details:

        if ("comeback" in match_detail):
            comeback = match_detail["comeback"]
        else:
            comeback = "null"

        if ("stomp" in match_detail):
            stomp = match_detail["stomp"]
        else:
            stomp = "null"

        selected = {'match_id':match_detail['match_id'],
                'duration': match_detail['duration'],
                'players': [],
                # 'game_mode':match_detail['game_mode'],
                'human_players':match_detail['human_players'],
                'start_time':match_detail['start_time'],
                'region':match_detail['region'],
                "comeback":comeback,
                "stomp":stomp
                }

        player_list = []
        for player in match_detail['players']:
            player_list.append({"account_id":player['account_id'],
                                "player_slot":player['player_slot'],
                                "hero_id":player['hero_id']})
        selected['players'] = player_list
        wrangling_db.match_details.insert_one(selected)

def filter_data():
    import pymongo as pm, pandas as pd, numpy as np

    mongo_client = pm.MongoClient("mongodb://mongo:27017/")
    wrangling_db = mongo_client['wrangling_match_details']
    wrangling_db.match_details_filtered.drop()

    match_details = pd.DataFrame(wrangling_db.match_details.find())

    match_details = match_details[match_details['stomp']!='null'].drop('_id',axis=1)

    match_details['duration'] = np.ceil(match_details['duration']/900).apply(lambda x: min(int(x),5))

    match_details_dict = match_details.to_dict(orient='index')

    for _, match_detail_item in match_details_dict.items():
        wrangling_db.match_details_filtered.insert_one(match_detail_item)

default_args_dict = {
    'start_date': datetime.datetime(2022,10,14),
    'concurrency': 1,
    'schedule_interval': None,
    'retries': 1,
    'retry_delay': datetime.timedelta(seconds=5),
}

first_dag = DAG(
    dag_id='dota_wrangling_dag',
    default_args=default_args_dict,
    catchup=False,
)

task_create_match_table = PostgresOperator(
    task_id='create_match_table',
    dag=first_dag,
    postgres_conn_id='postgres_default',
    sql='DROP TABLE IF EXISTS match; '\
        'CREATE TABLE match ('\
        '   match_id INT,'\
        '   duration INT,'\
        '   human_players INT,'\
        '   start_time TIMESTAMP,'\
        '   region INT,'\
        '   sunlight INT,'\
        '   comeback INT,'\
        '   stomp INT);',
    trigger_rule='all_success',
    autocommit=True,
)

task_create_duration_table = PostgresOperator(
    task_id='create_duration_table',
    dag=first_dag,
    postgres_conn_id='postgres_default',
    sql='DROP TABLE IF EXISTS duration; '\
        'CREATE TABLE duration ('\
        '   duration_id INT,'\
        '   name VARCHAR,'\
        '   lower_bound INT,'\
        '   upper_bound INT);'\
        'INSERT INTO duration VALUES(1,\'VERY SHORT\', 0, 900),'\
        '   (2, \'SHORT\', 900, 1800),'\
        '   (3, \'MEDIUM\', 1800, 2700),'\
        '   (4, \'LONG\', 2700, 3600),'\
        '   (5, \'VERY LONG\', 3600, 1000000);',
    trigger_rule='all_success',
    autocommit=True,
)

task_mock_injestions = PythonOperator(
    task_id='mock_injestions',
    dag=first_dag,
    python_callable=mock_injestions,
    op_kwargs={
        "stash_file": "./dags/data/match_details_stash/matchDetails1"
    },
)

task_select_attributes = PythonOperator(
    task_id='select_attributes',
    dag=first_dag,
    python_callable=select_attributes,
)

task_filter_data = PythonOperator(
    task_id='filter_data',
    dag=first_dag,
    python_callable=filter_data,
)

task_last = DummyOperator(
    task_id='end',
    dag=first_dag,
    trigger_rule='none_failed',
    depends_on_past=False,
)

[task_mock_injestions, task_create_match_table >> task_create_duration_table] >> task_select_attributes >> task_filter_data >> task_last