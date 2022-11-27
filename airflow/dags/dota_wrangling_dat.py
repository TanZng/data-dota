import airflow
import datetime
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators.postgres_operator import PostgresOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor

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
    import datetime, calendar

    mongo_client = pm.MongoClient("mongodb://mongo:27017/")
    wrangling_db = mongo_client['wrangling_match_details']
    wrangling_db.match_details_filtered.drop()

    match_details = pd.DataFrame(wrangling_db.match_details.find())

    match_details = match_details[match_details['stomp']!='null'].drop('_id',axis=1)

    match_details['duration'] = np.ceil(match_details['duration']/900).apply(lambda x: min(int(x),5))

    constant_db = mongo_client['constant_db']

    regions = pd.DataFrame(constant_db.region_city.find()).set_index('region_id').drop('_id',axis=1)

    #make all region 13 to region 12
    match_details.loc[match_details['region']==13,'region'] = 12

    match_details = match_details.join(regions,on='region')

    match_details['sunlight'] = match_details.apply(\
        lambda x: str(x['region_name']).replace(' ','_')+'_'+calendar.month_abbr[datetime.datetime.fromtimestamp(x['start_time']).month],axis=1)

    match_details = match_details.drop('city_name',axis=1).drop('region_name',axis=1)

    match_details_dict = match_details.to_dict(orient='index')

    for _, match_detail_item in match_details_dict.items():
        wrangling_db.match_details_filtered.insert_one(match_detail_item)

def upload_region_to_dim_table():

    import pymongo as pm, pandas as pd

    from sqlalchemy import create_engine

    conn_string = 'postgres://airflow:airflow@postgres:5432'
    
    db = create_engine(conn_string)
    conn = db.connect()

    mongo_client = pm.MongoClient("mongodb://mongo:27017/")
    constant_db = mongo_client['constant_db']

    regions = pd.DataFrame(constant_db.region_city.find()).drop('_id',axis=1).drop('city_name',axis=1)

    regions.to_sql('region',con=conn,if_exists='replace',index=False)

def create_sunlight_mapping_table():
    import pymongo as pm, pandas as pd, numpy as np
    import redis
    from sqlalchemy import create_engine

    conn_string = 'postgres://airflow:airflow@postgres:5432'
    
    db = create_engine(conn_string)
    conn = db.connect()

    redis_host = 'redis'
    redis_port = '6379'

    redis_client = redis.Redis(host=redis_host, port=redis_port, db=1)

    mongo_client = pm.MongoClient("mongodb://mongo:27017/")
    constant_db = mongo_client['constant_db']

    regions = pd.DataFrame(constant_db.region_city.find()).set_index('region_id').drop('_id',axis=1)
    regions['region_name'] = regions['region_name'].apply(lambda x: x.replace(' ','_'))

    month_names = ['Dec', 'Feb', 'Jan', 'Jul', 'Jun', 'Mar', 'May', 'Nov', 'Oct', 'Sep']
    monthly_sunlight = {i : 0 for i in month_names}

    regional_monthly_sunlight = pd.DataFrame(columns = ['sunlight_id','sunlight_level_id'])

    for _, region in regions.iterrows():
        for month_name in month_names:
            monthly_sunlight[month_name] = (float(redis_client.get(region['region_name']+'_'+month_name)))

        average = sum(monthly_sunlight.values())/len(monthly_sunlight)
        for month_name in month_names:
            # x<0.85 = 1
            # 0.85<x<0.95 = 2
            # 0.95<x<1.05 = 3
            # 1.05<x<1.15 = 4
            # x>1.15 = 5
            sunlight_level_id = np.ceil((min(max((monthly_sunlight[month_name]/average),0.85),1.3)-0.75)/0.1)
            regional_monthly_sunlight.loc[len(regional_monthly_sunlight)] = \
                [region['region_name']+'_'+month_name,sunlight_level_id]
        
    regional_monthly_sunlight.to_sql('sunlight_map',con=conn,if_exists='replace',index=False)

def upload_match_to_fact_table():
    import pymongo as pm, pandas as pd

    from sqlalchemy import create_engine

    conn_string = 'postgres://airflow:airflow@postgres:5432'
    
    db = create_engine(conn_string)
    conn = db.connect()

    mongo_client = pm.MongoClient("mongodb://mongo:27017/")
    wrangling_db = mongo_client['wrangling_match_details']

    match_details = pd.DataFrame(wrangling_db.match_details_filtered.find()).drop('players',axis=1).drop('_id',axis=1)

    match_details.to_sql('match',con=conn,if_exists='replace',index=False)

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
        '   sunlight VARCHAR,'\
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

task_create_sunlight_level_table = PostgresOperator(
    task_id='create_sunlight_level_table',
    dag=first_dag,
    postgres_conn_id='postgres_default',
    sql='DROP TABLE IF EXISTS sunlight_level; '\
        'CREATE TABLE sunlight_level ('\
        '   sunlight_level_id int,'\
        '   name VARCHAR);'\
        'INSERT INTO sunlight_level VALUES(1,\'VERY DARK\'),'\
        '   (2, \'DARK\'),'\
        '   (3, \'NORMAL\'),'\
        '   (4, \'BRIGHT\'),'\
        '   (5, \'VERY BRIGHT\');',
    trigger_rule='all_success',
    autocommit=True,
)

task_upload_region_to_dim_table = PythonOperator(
    task_id='upload_region_to_dim_table',
    dag=first_dag,
    python_callable=upload_region_to_dim_table,
)

task_create_sunlight_mapping_table = PythonOperator(
    task_id='create_sunlight_mapping_table',
    dag=first_dag,
    python_callable=create_sunlight_mapping_table,
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

task_upload_match_to_fact_table = PythonOperator(
    task_id='upload_match_to_fact_table',
    dag=first_dag,
    python_callable=upload_match_to_fact_table,
)

task_last = DummyOperator(
    task_id='end',
    dag=first_dag,
    trigger_rule='none_failed',
    depends_on_past=False,
)

task_create_region_table = ExternalTaskSensor(
    task_id='task_create_region_table',
    poke_interval=60,
    timeout=180,
    soft_fail=False,
    retries=2,
    external_task_id='add_constant_to_mongo',
    external_dag_id='constant_ingestion_dag',
    dag=first_dag
)

task_get_match_ids >> [task_get_match_details, task_create_region_table] >> task_select_attributes >> task_filter_data >> task_upload_match_to_fact_table >> task_last

task_create_match_table >> [task_create_duration_table, task_upload_region_to_dim_table, task_create_sunlight_level_table >> task_create_sunlight_mapping_table] >> task_filter_data