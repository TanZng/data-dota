import csv
import time
import airflow
from airflow import DAG
from datetime import timedelta, datetime
from airflow.operators.bash_operator import BashOperator
from airflow.providers.mongo.hooks.mongo import MongoHook
from airflow.operators.python_operator import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator

def upload_to_mongo_mock():
    try:
        hook = MongoHook(mongo_conn_id='mongo_default')
        client = hook.get_conn()
        db = client.SunLightDB
        sunlight_collection=db.sunlight_collection
        print(f"Connected to MongoDB - {client.server_info()}")
        name : US 
        with open('/opt/airflow/dags/data/sunlight.csv', mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            line_count = 0
            for row in csv_reader:
                if line_count > 0:
                    sunlight_collection.insert_one(row)
                line_count += 1
    except Exception as e:
        printf("Error connecting to MongoDB -- {e}")


sunlight_args_dict = {
    'start_date': datetime.now() - timedelta(days=1),
    'retries': 5,
    'retry_delay': timedelta(minutes=2),
}

sunlight_dag_offline = DAG(
    dag_id='sunlight_dag_offline',
    default_args=sunlight_args_dict,
    catchup=False,
)

# Downloading a file from an API/endpoint?

task_get_csv_mock = BashOperator(
    task_id='offline_get_csv_mock',
    dag=sunlight_dag_offline,
    bash_command="curl http://mock-api:5010/sunlight.csv --output /opt/airflow/dags/data/sunlight.csv",
)

task_index_to_mongo_mock = PythonOperator(
    task_id='index_sunlight_to_mongo_mock',
    dag=sunlight_dag_offline,
    python_callable=upload_to_mongo_mock,
)

id_now = int( time.time() )

task_get_sunlight_avg_mock = DockerOperator(
    task_id='docker_get_sunlight_avg_mock',
    dag=sunlight_dag_offline,
    mount_tmp_dir=False,
    image='avg_sunlight_by_region',
    network_mode="data-dota",
    auto_remove=True,
    # xcom_all=True,
    api_version='auto',
    docker_url="tcp://docker-socket-proxy:2375",
)


task_get_csv_mock >> task_index_to_mongo_mock >> task_get_sunlight_avg_mock