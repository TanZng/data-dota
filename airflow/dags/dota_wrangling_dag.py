import airflow
import datetime
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.postgres_operator import PostgresOperator

def select_attributes():
    import time, pymongo as pm, pandas as pd
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

task_select_attributes = PythonOperator(
    task_id='get_match_ids',
    dag=first_dag,
    python_callable=select_attributes,
)

task_last = DummyOperator(
    task_id='end',
    dag=first_dag,
    trigger_rule='none_failed',
    depends_on_past=False,
)

task_select_attributes >> task_last