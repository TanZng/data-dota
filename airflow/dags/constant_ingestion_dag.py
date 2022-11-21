import airflow
import datetime
# from pymongo import MongoClient
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.postgres_operator import PostgresOperator
import faker, requests, random, json

# def get_match_ids(outputFile):

#     # randomise a name
#     name = faker.Faker().name()

#     # write to file
#     file = open(outputFile, "w+")
#     file.write(json.dumps({'name':name}))
    
# def cache_data(uploadFile, tableName, postgresConnID):
#     from airflow.hooks.postgres_hook import PostgresHook

#     pg_hook = PostgresHook.get_hook(postgresConnID)
#     pg_conn = pg_hook.get_conn()
#     pg_hook.copy_expert("""COPY """+tableName+""" FROM stdin WITH CSV HEADER
#                         DELIMITER as ',' """,
#                         uploadFile)
#     pg_conn.commit()

def add_JSON_file_to_mongo(**context):
    # print("***TEST*** attribut context in python function : " + context["region_file"])
    # myclient = MongoClient("http://localhost::27017/")
    # constant_db = myclient["constant_db"]
    # region_coll = constant_db["region"]
    # heros_coll = constant_db["heroes"]
    region_json = open(context["region_file"], 'r+')
    print(region_json)
    # region_dict = 
    # constant_db.region_coll.insert(region_dict)

default_args_dict = {
    'start_date': datetime.datetime(2022,10,14),
    'concurrency': 1,
    'schedule_interval': None,
    'retries': 1,
    'retry_delay': datetime.timedelta(seconds=5),
}

first_dag = DAG(
    dag_id='dota_init_dag',
    default_args=default_args_dict,
    catchup=False,
)

# task_create_table = PostgresOperator(
#     task_id='create_table',
#     dag=first_dag,
#     postgres_conn_id='postgres_default',
#     sql='DROP TABLE IF EXISTS match_id; '\
#         'CREATE TABLE match_id ('\
#         '   match_id int,'\
#         '   match_seq_num int,'\
#         '   counter int);',
#     trigger_rule='all_success',
#     autocommit=True,
# )

# task_get_match_ids = PythonOperator(
#     task_id='get_match_ids',
#     dag=first_dag,
#     python_callable=get_match_ids,
#     op_kwargs={
#         "outputFile": "./dags/tmp/name.txt"
#     },
# )

# task_cache_data = PythonOperator(
#     task_id='cache_data',
#     dag=first_dag,
#     python_callable=cache_data,
#     op_kwargs={
#         "outputFile": "./dags/tmp/name.txt"
#     },
# )

# task_last = DummyOperator(
#     task_id='end',
#     dag=first_dag,
#     trigger_rule='none_failed',
#     depends_on_past=False,
# )

# download_constant = BashOperator(
#     task_id = 'download_constant',
#     dag = first_dag,
#     bash_command = """curl -o /home/cachou/Documents/fundation_data_engineering/data-dota/data/region.json 
#     https://raw.githubusercontent.com/odota/dotaconstants/master/build/region.json | 
#     curl -o /home/cachou/Documents/fundation_data_engineering/data-dota/data/heroes.json 
#     https://raw.githubusercontent.com/odota/dotaconstants/master/build/heroes.json"""
# )

add_constant_to_mongo = PythonOperator(
    task_id = "add_contant_to_mongo",
    dag = first_dag,
    python_callable = add_JSON_file_to_mongo,
    op_kwargs={
        "region_file":"/home/cachou/Documents/fundation_data_engineering/data-dota/data/region.json",
        "heroes_file":"/home/cachou/Documents/fundation_data_engineering/data-dota/data/heroes.json"
    }
)
# task_create_table >> task_get_match_ids >> task_cache_data >> task_last
# download_constant
add_constant_to_mongo




