import datetime
import pymongo as py
import json
from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
import json
from pandas import DataFrame

def add_JSON_file_to_mongo(**context):
    myclient = py.MongoClient("mongodb://mongo:27017/")
    constant_db = myclient["constant_db"]
    region_coll = constant_db["region"]
    heros_coll = constant_db["heroes"]

    # Open and read local JSON region file
    region_file = open(context["region_file"], 'r')
    region_json = json.load(region_file)  
    region_coll.insert_one(region_json)
    region_file.close()

    # Open and read local JSON heros file
    heroes_file = open(context["heroes_file"], 'r')
    heroes_json = json.load(heroes_file)
    heros_coll.insert_one(heroes_json)
    heroes_file.close()

def add_city_attribute_to_region():
    myclient = py.MongoClient("mongodb://mongo:27017/")
    constant_db = myclient["constant_db"]
    region_coll = constant_db["region"]

    region_cursor = region_coll.find()
    region_list = list(region_cursor)
    region_list[0]["region"] = "region_name"
    region_df = DataFrame(region_list).set_index("region")
    region_df = region_df.transpose()
    region_df = region_df.drop(labels="_id", axis=0)
    region_df = region_df.drop(labels="13", axis=0)
    city_list = [
        ["1", "SAN FRANSISCO"],
        ["2", "NEW YORK"],
        ["3", "MADRID"],
        ["5", "SINGAPORE"],
        ["6", "DUBAI"],
        ["7", "ALICE SPRINGS"],
        ["8", "STOCKHOLM"],
        ["9", "LIEZEN"],
        ["10", "BRASILIA"],
        ["11", "PRETORIA"],
        ["12", "SHANGHAI"],
        ["14", "SANTIAGO"],
        ["15", "PUCALLPA"],
        ["16", "NAGPUR"],
        ["17", "GUANGDONG"],
        ["18", "ZHEJIANG"],
        ["19", "TOKYO"],
        ["20", "WUHAN"],
        ["25", "TIANJIN"],
        ["37", "TAIPEI"],
        ["38", "NEUQUEN"],
    ]
    city_df = DataFrame(city_list, columns=["region", "city_name"])
    region_city_df = region_df.join(city_df.set_index("region"))    
    region_city_coll = constant_db["region_city"]
    region_city_dict = region_city_df.to_dict(orient="index")
    for index, region_city in region_city_dict.items():
        region_city['region_id']=int(index)
        region_city_coll.insert_one(region_city)

default_args_dict = {
    'start_date': datetime.datetime(2022,10,14),
    'concurrency': 1,
    'schedule_interval': None,
    'retries': 1,
    'retry_delay': datetime.timedelta(seconds=5),
}

constant_ingestion_offline = DAG(
    dag_id='constant_ingestion_dag_offline',
    default_args=default_args_dict,
    catchup=False,
)
download_constant_offline = BashOperator(
    task_id = 'download_constant_offline',
    dag = constant_ingestion_offline,
    bash_command = """curl http://mock-api:5010/region.json --output /opt/airflow/dags/data/region.json && curl http://mock-api:5010/heroes.json --output /opt/airflow/dags/data/heroes"""
)

add_constant_to_mongo_offline = PythonOperator(
    task_id = "add_constant_to_mongo_offline",
    dag = constant_ingestion_offline,
    python_callable = add_JSON_file_to_mongo,
    op_kwargs={
        "region_file":"/opt/airflow/dags/data/region.json",
        "heroes_file":"/opt/airflow/dags/data/heroes"
    }
)

add_city_attribute_to_region_task_offline = PythonOperator(
    task_id = "add_city_attribute_to_region_task_offline",
    dag = constant_ingestion_offline,
    python_callable = add_city_attribute_to_region,
)

download_constant_offline  >> add_constant_to_mongo_offline >> add_city_attribute_to_region_task_offline
