import airflow
import csv
from airflow import DAG
from datetime import timedelta, datetime
from airflow.operators.bash_operator import BashOperator
from airflow.providers.mongo.hooks.mongo import MongoHook
from airflow.operators.python_operator import PythonOperator
from airflow.providers.docker.operators.docker import DockerOperator

def upload_to_mongo():
    try:
        hook = MongoHook(mongo_conn_id='mongo_default')
        client = hook.get_conn()
        db = client.MyDB
        sunlight_collection=db.sunlight_collection
        print(f"Connected to MongoDB - {client.server_info()}")
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

sunlight_dag = DAG(
    dag_id='sunlight_dag',
    default_args=sunlight_args_dict,
    catchup=False,
)

# Downloading a file from an API/endpoint?

task_get_csv = BashOperator(
    task_id='get_csv',
    dag=sunlight_dag,
    bash_command="curl https://raw.githubusercontent.com/TanZng/data-dota/main/day-light-table-to-csv/table.csv --output /opt/airflow/dags/data/sunlight.csv",
)

task_index_to_mongo = PythonOperator(
    task_id='index_sunlight_to_mongo',
    dag=sunlight_dag,
    python_callable=upload_to_mongo,
)

task_get_sunlight_avg = DockerOperator(
    task_id='docker_get_sunlight_avg',
    dag=sunlight_dag,
    image='avg_sunlight_by_region',
    container_name='task_get_sunlight_avg',
    network_mode="data-dota",
    auto_remove=True,
    api_version='auto',
    docker_url="TCP://docker-socket-proxy:2375",
)


task_get_csv >> task_index_to_mongo >> task_get_sunlight_avg