import airflow
import datetime
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.postgres_operator import PostgresOperator

def get_match_ids():

    import requests, time, pymongo

    class ResponseResultsCountException(Exception):
        def __init__(self, message ="Number of results not equal to 100"):
            self.message = message
            super().__init__(self.message)

    class ResponseStatusCodeException(Exception):
        def __init__(self, code, message ="HTML status code return: "):
            self.code = code
            self.message = message
            super().__init__(self.message)
        def __str__(self):
            return self.message + str(self.code)

    class ResponseReturnIncorrectMatch(Exception):
        def __init__(self, match_seq_num, message ="Match sequence number returned wrong for number: "):
            self.message = message
            self.match_seq_num = match_seq_num
            super().__init__(self.message)
        def __str__(self):
            return self.message + str(self.match_seq_num)

    api_key = "5178694816A055E8ED1B5E0F822590F5"
    steam_url = "https://api.steampowered.com/IDOTA2Match_570/"
    get_match = "GetMatchHistoryBySequenceNum/v1/"

    match_seq_num = 4702324544

    mongo_client = pymongo.MongoClient("mongodb://mongo:27017/")

    id_db = mongo_client['match_ids']
    id_db.match_ids.drop()

    for i in range(1,10):
        request_url = steam_url+get_match+"?key="+api_key+"&start_at_match_seq_num="+\
            str(match_seq_num)+"&matches_requested=10"
        
        retry = True
        while (retry==True):
            try:
                response = requests.get(request_url)
                if (response.status_code!=200):
                    raise ResponseStatusCodeException(response.status_code)

                response=response.json()

                if (len(response['result']['matches'])!=10):
                    raise ResponseResultsCountException

                if (response['result']['matches'][0]['match_seq_num']!=match_seq_num):
                    raise ResponseReturnIncorrectMatch(match_seq_num)
                
                retry = False

                match_seq_num+=10000

            except requests.exceptions.RequestException as e:
                raise SystemExit(e)
            except (ResponseResultsCountException,ResponseStatusCodeException) as e:
                print (e)
                time.sleep(0.1)
            except (ResponseReturnIncorrectMatch) as e:
                print (e)
                match_seq_num+=1

        matches = response['result']['matches']

        id_db.match_ids.insert_many(matches)
    
def get_match_details():
    class ResponseStatusCodeException(Exception):
        def __init__(self, code, message ="HTML status code return: "):
            self.code = code
            self.message = message
            super().__init__(self.message)
        def __str__(self):
            return self.message + str(self.code)

    class MatchNotFoundException(Exception):
        def __init__(self, message ="Match was not found!"):
            self.message = message
            super().__init__(self.message)
        def __str__(self):
            return self.message
    
    import requests, json, pymongo, time

    openDota_url = "https://api.opendota.com/api/"
    get_match = "matches/"

    mongo_client = pymongo.MongoClient("mongodb://mongo:27017/")

    id_db = mongo_client['match_ids']
    id_db.match_details.drop()

    all_match_id = id_db.match_ids.find()

    for match in all_match_id:
        match_id = match['match_id']
        request_url = openDota_url+get_match+str(match_id)

        retry = True
        write = True
        while (retry):
            try:
                response = requests.get(request_url)
                if (response.status_code == 200):
                    response=response.json()
                    retry = False
                elif (response.status_code==404):
                    raise MatchNotFoundException
                else:
                    raise ResponseStatusCodeException(response.status_code)
            except requests.exceptions.RequestException as e:
                raise SystemExit(e)
            except MatchNotFoundException as e:
                print (e)
                retry = False
                write = False
            except (ResponseStatusCodeException) as e:
                print(e,", retrying...")
                time.sleep(5)

        if (write):
            id_db.match_details.insert_one(response)

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

task_get_match_ids = PythonOperator(
    task_id='get_match_ids',
    dag=first_dag,
    python_callable=get_match_ids,
)

task_get_match_details = PythonOperator(
    task_id='get_match_details',
    dag=first_dag,
    python_callable=get_match_details,
)

task_last = DummyOperator(
    task_id='end',
    dag=first_dag,
    trigger_rule='none_failed',
    depends_on_past=False,
)

task_get_match_ids >> task_get_match_details >> task_last




