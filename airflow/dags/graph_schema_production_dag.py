from py2neo  import Graph
import datetime
import json
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor
import pymongo as py
import pandas as pd

def download_data(**context):
    myclient = py.MongoClient("mongodb://mongo:27017/")
    match_details_db = myclient["wrangling_match_details"]
    match_details_coll = match_details_db["match_details_filtered"]
    constant_db = myclient["constant_db"]
    heros_coll = constant_db["heroes"]
    pd.DataFrame(match_details_coll.find({})).to_json(context["match_details_file"], orient='index')
    pd.DataFrame(heros_coll.find({})).to_json(context["heroes_file"], orient='index')



def match_nodes(**context):
    heroes_lineup_graph = Graph(context["neo4j_DB"])
    tx = heroes_lineup_graph.begin()
    with open(context["matchDetails_file"]) as matchDetails_json:
        matchDetails_dict = json.load(matchDetails_json)
    for match in matchDetails_dict:
        tx.run("CREATE (m:Match{id:$id_match}) RETURN m", id_match=match.get("match_id"))
    tx.commit()

def hero_nodes(**context):
    heroes_lineup_graph = Graph(context["neo4j_DB"])
    tx = heroes_lineup_graph.begin()
    with open(context["heroes_file"]) as heroes_json:
        heroes_dict = json.load(heroes_json)
    for key in heroes_dict:
        id = heroes_dict.get(key).get("id")
        name = heroes_dict.get(key).get("name")
        tx.run("CREATE (h:Heroe{id:$id_heroe, name:$name_heroe}) RETURN h", id_heroe= id, name_heroe = name)
    tx.commit()

def lineup_nodes(**context):
    heroes_lineup_graph = Graph(context["neo4j_DB"])
    tx = heroes_lineup_graph.begin()
    with open(context["matchDetails_file"]) as matchDetails_json:
        matchDetails_dict = json.load(matchDetails_json)   
    radiant_lineup = []
    dire_lineup = []
    for match in matchDetails_dict:
        for player in match.get("players"):
            if player.get("isRadiant") == True:
                radiant_lineup.append(player.get("hero_id"))
            else:
                dire_lineup.append(player.get("hero_id"))
        if (len(radiant_lineup) == 5 and len(dire_lineup) == 5):
            match_id = match.get("match_id")
            tx.run("CREATE (l:Lineup{id_match:$match_id, team:'radiant', hero_id_1:$id_heroe_1, hero_id_2:$id_heroe_2, hero_id_3:$id_heroe_3, hero_id_4:$id_heroe_4, hero_id_5:$id_heroe_5}) RETURN l", match_id = match_id, id_heroe_1 = radiant_lineup[0], id_heroe_2 = radiant_lineup[1], id_heroe_3 = radiant_lineup[2], id_heroe_4 = radiant_lineup[3], id_heroe_5 = radiant_lineup[4])
            tx.run("CREATE (l:Lineup{id_match:$match_id, team: 'dire', hero_id_1:$id_heroe_1, hero_id_2:$id_heroe_2, hero_id_3:$id_heroe_3, hero_id_4:$id_heroe_4, hero_id_5:$id_heroe_5}) RETURN l", match_id = match_id, id_heroe_1 = dire_lineup[0], id_heroe_2 = dire_lineup[1], id_heroe_3 = dire_lineup[2], id_heroe_4 = dire_lineup[3], id_heroe_5 = dire_lineup[4])        
        radiant_lineup=[]
        dire_lineup=[]
    tx.commit()

def lineup_to_match_binding (**context):
    heroes_lineup_graph = Graph(context["neo4j_DB"])
    tx = heroes_lineup_graph.begin()
    with open(context["matchDetails_file"]) as matchDetails_json:
        matchDetails_dict = json.load(matchDetails_json)   
    for match in matchDetails_dict:
        id_match = match.get("match_id")
        if match.get("radiant_win") == True:
            tx.run("MATCH (l:Lineup), (m:Match) WHERE l.team = 'radiant' AND m.id = $match_id AND l.id_match = $match_id MERGE (l)-[:WON]->(m) RETURN *", match_id = id_match)
            tx.run("MATCH (l:Lineup), (m:Match) WHERE l.team = 'dire' AND m.id = $match_id AND l.id_match = $match_id MERGE (l)-[:LOST]->(m) RETURN *", match_id = id_match)
        else:
            tx.run("MATCH (l:Lineup), (m:Match) WHERE l.team = 'radiant' AND m.id = $match_id AND l.id_match = $match_id MERGE (l)-[:LOST]->(m) RETURN *", match_id = id_match)
            tx.run("MATCH (l:Lineup), (m:Match) WHERE l.team = 'dire' AND m.id = $match_id AND l.id_match = $match_id MERGE (l)-[:WON]->(m) RETURN *", match_id = id_match)
    tx.commit()

def heroe_to_lineup_bindings (**context):
    heroes_lineup_graph = Graph(context["neo4j_DB"])
    tx = heroes_lineup_graph.begin()
    tx.run("MATCH (l:Lineup), (h:Heroe) WHERE h.id = l.hero_id_1 OR h.id = l.hero_id_2 OR h.id = l.hero_id_3 OR h.id = l.hero_id_4 OR h.id = l.hero_id_5 MERGE (h)-[:BELONG_TO]->(l)")
    tx.commit()

default_args_dict = {   
    'start_date': datetime.datetime(2022,10,14),
    'concurrency': 1,
    'schedule_interval': None,
    'retries': 1,
    'retry_delay': datetime.timedelta(seconds=5),
}

neo4j_production = DAG(
    dag_id='neo4j_production_dag',
    default_args=default_args_dict,
    catchup=False,
)

download_data_from_mongo = PythonOperator (
    task_id = "download_data",
    dag = neo4j_production,
    python_callable = download_data,
    op_kwargs={
        "match_details_file":"/opt/airflow/dags/data/match_details",
        "heroes_file":"/opt/airflow/dags/data/heroes"
    }
)

create_match_nodes_task = PythonOperator (
    task_id = "match_nodes",
    dag = neo4j_production,
    python_callable = match_nodes,
    op_kwargs={
        "neo4j_DB":"bolt://neo:7687",
        "matchDetails_file":"/opt/airflow/dags/data/match_details"
    }
)

create_hero_nodes_task = PythonOperator (
    task_id = "hero_nodes",
    dag = neo4j_production,
    python_callable = hero_nodes,
    op_kwargs={
        "neo4j_DB":"bolt://neo:7687",
        "heroes_file":"/opt/airflow/dags/data/heroes"
    }
)

create_lineup_nodes_task = PythonOperator (
    task_id = "lineup_nodes",
    dag = neo4j_production,
    python_callable = lineup_nodes,
    op_kwargs={
        "neo4j_DB":"bolt://neo:7687",
        "matchDetails_file":"/opt/airflow/dags/data/match_details"
    }
)

create_lineup_to_match_bindings_task = PythonOperator (
    task_id = "lineup_to_match_bindings",
    dag = neo4j_production,
    python_callable = lineup_to_match_binding,
    op_kwargs={
        "neo4j_DB":"bolt://neo:7687",
        "matchDetails_file":"/opt/airflow/dags/data/match_details"
    }
)

create_hero_to_lineup_bindings_task = PythonOperator (
    task_id = "heroes_to_lineup_bindings",
    dag = neo4j_production,
    python_callable = heroe_to_lineup_bindings,
    op_kwargs={
        "neo4j_DB":"bolt://neo:7687"
    }
)

task_create_region_table = ExternalTaskSensor(
    task_id='task_create_region_table',
    poke_interval=60,
    timeout=180,
    soft_fail=False,
    retries=2,
    external_task_id='add_constant_to_mongo',
    external_dag_id='constant_ingestion_dag',
    dag=neo4j_production
)

task_filter_data = ExternalTaskSensor(
    task_id='task_filter_data',
    poke_interval=60,
    timeout=180,
    soft_fail=False,
    retries=2,
    external_task_id='filter_data',
    external_dag_id='dota_wrangling_dag',
    dag=neo4j_production
)

[task_create_region_table, task_filter_data] >> create_match_nodes_task >> create_hero_nodes_task >> create_lineup_nodes_task >> create_hero_to_lineup_bindings_task >> create_lineup_to_match_bindings_task
