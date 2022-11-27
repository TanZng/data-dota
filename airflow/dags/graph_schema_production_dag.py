from py2neo  import Graph
import datetime
import json
from airflow import DAG
from airflow.operators.python_operator import PythonOperator


# def test_neo4j(**context):
#     heroes_lineup_graph = Graph(context["neo4j_DB"])

#     tx = heroes_lineup_graph.begin()
#     for name in ["Alice", "Bob", "Carol"]:
#         tx.run("CREATE ((person:Person{name:$name})-[:JOB]->(job:Job{label:'developper'})) RETURN person, job", name=name)
#     tx.commit()

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

# create_match_nodes_task = PythonOperator (
#     task_id = "match_nodes",
#     dag = neo4j_production,
#     python_callable = match_nodes,
#     op_kwargs={
#         "neo4j_DB":"bolt://neo:7687",
#         "matchDetails_file":"/opt/airflow/dags/data/match_details_test",
#         "heroes_file":"/opt/airflow/dags/data/heroes.json"
#     }
# )

# create_hero_nodes_task = PythonOperator (
#     task_id = "hero_nodes",
#     dag = neo4j_production,
#     python_callable = hero_nodes,
#     op_kwargs={
#         "neo4j_DB":"bolt://neo:7687",
#         "matchDetails_file":"/opt/airflow/dags/data/match_details_test",
#         "heroes_file":"/opt/airflow/dags/data/heroes.json"
#     }
# )

# create_lineup_nodes_task = PythonOperator (
#     task_id = "lineup_nodes",
#     dag = neo4j_production,
#     python_callable = lineup_nodes,
#     op_kwargs={
#         "neo4j_DB":"bolt://neo:7687",
#         "matchDetails_file":"/opt/airflow/dags/data/match_details_test",
#         "heroes_file":"/opt/airflow/dags/data/heroes.json"
#     }
# )

# create_lineup_to_match_bindings_task = PythonOperator (
#     task_id = "lineup_to_match_bindings",
#     dag = neo4j_production,
#     python_callable = lineup_to_match_binding,
#     op_kwargs={
#         "neo4j_DB":"bolt://neo:7687",
#         "matchDetails_file":"/opt/airflow/dags/data/match_details_test",
#         "heroes_file":"/opt/airflow/dags/data/heroes.json"
#     }
# )

create_hero_to_lineup_bindings_task = PythonOperator (
    task_id = "heroes_to_lineup_bindings",
    dag = neo4j_production,
    python_callable = heroe_to_lineup_bindings,
    op_kwargs={
        "neo4j_DB":"bolt://neo:7687",
        "matchDetails_file":"/opt/airflow/dags/data/match_details_test",
        "heroes_file":"/opt/airflow/dags/data/heroes.json"
    }
)

create_hero_to_lineup_bindings_task

# 1) créer noeuds matchs : récupérer dans matchDetails (JSON), l'attribut match_id => "CREATE (m:Match{id:$id_match}) RETURN m", id_match=
# 2) créer noeuds hero : récupérer dans heroes (JSON), les attributs id et name => "CREATE (h:Heroe{id:$id_heroe, name:$name_heroe}) RETURN h", id_heroe= , name_heroe
# 3) créer lien héro to lineup : récupérer attributs dans matchDetails (JSON) players (tableau) => isRadiant (boolean) / hero_id => for each player du tableau players, 
# si isRadiant est True, ajoute heroe_id au lineup_radiant_tmp, sinon ajoute au lineup_dire_tmp; puis crée noeuds lineup + liens avec les héros
# 4) créer lien lineup to match (WIN/LOST) : 

# 5612 MATCHS DANS match_details_test
# le fichier match_details_test est une liste contenant 5612 python dict représentant chacun un match

# Le fichier heroes.json est un python dict