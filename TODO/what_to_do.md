# STEP 1 = DATA INGESTION :

start with 4 DBs :
- Matchs ids => allows us to retrieve match ids with Dota API
- Constant => JSON file downloaded manually allowing us to identify regions and heroes of Opendota database
- Sunlight => CSV file containing sunlights data for regions in countries
- Opendota => JSON file retrieved with API request using match id

Data ingestion => MongoDB for data wrangling => PostgreSQL for data production
DBs Match_ids, sunlight et Constant => one time data ingestion
DB Opendota => as many as there are match ids in Match_ids DB

# STEP 2 = DATA WRANGLING :

in MongoDB
Opendota => we have an id for each region, using Constant DB, we find the region name according to the id,
Then, using Sunlight DB, we calculate the average sunlight per month for each region (one Opendota region = multiple city (i.e rows) in Sunlight DB)

filter Opendota DB to get just some attributes (cf below) for each match + ignore empty rows (or other tests as "are there 10 players in the match ?")
attributes to retrieve from Opendota DB :
"match_id": the id of the match
"duration": the duration of the match in seconds => to transform from seconds to adjectives (very short = less than 20min, short = 20-30min,
medium = 30-50min, long = 50min-1h30, very long = more than 1h30)
"game_mode": if need more complexity (one more dimension),
"human_players": numbers of human players during this match (exactly 10, else delete the match),
"start_time": start time of the match (UNIX format = number of seconds since january 1st 1970 at midnight),
"version":if need more complexity (one more dimension),
"players": identifiers of the players,
"heroes": identifiers the heroes playing in the match,
"region": id of the region,
"comeback": numbers representing the highest gold advantage of the loosing team => the higher the value the bigger the comeback
"stomp": numbers representing the highest gold advantage of the winning team => the higher the value the easier it was to win
"radiant_win": boolean => true means Radiant team win = players id 0 to 4 // false means Dire team win so players id from 5 to 9
create a "sunlight" attribute : id of the level of the sunlight during the match => foreign key od the dimension table "level_of_sunlight"
create a "lineup_radiant" attribute : list of five heroes belonging to Radiant team
create a "lineup_dire" attribute : list of five heroes belonging to Dire team
result = JSON files with data to form :
- one fact_table "match_detail" with each row representing one match and as many columns as attributes filtered
- 3 dimension_tables :
    - match_duration table which makes corresponding duration id = key (1, 2, 3, 4, 5) with adjective duration (very short, short...)
    - level_of_sunlight which makes corresponding sunlight level id = key (1, 2, 3... to be defined) with sunlight level qualifiers (very dark, dark... to be defined)
    - region : directly from data ingestion step from Constant DB (id and name of each Opendota region)
- one temp_table which makes corresponding id of Opendota region with id of sunlight level. To create this table :
    - 1) group all the sunlight region (cities) corresponding to the Opendota region (ex : region Opendota = EU West => cities from sunlight DB = Paris, Lyon, Marseille, London...)
    - 2) calculate the average sunlight per month for the whole Opendota region (ex : EU West for january = 130)
    - 3) classify each sunlight value by one sunlight level qualifier (ex : 130 => dark ? to be defined) 
- one table "hero" directly from data ingestion step from Constant DB (id and name of each Opendota hero) => this is not a dimension table because it will be used to produce graph schema and not star schema

# STEP 3 DATA PRODUCTION :

## STEP 3.1 : Production of star schema

add JSON files from data wrangling step to PostgreSQL DB

## STEP 3.2 : Production of graph schema

using data form JSON file match "match_detail", create the corresponding nodes for heroes, match and lineup

### first proposal 
Each hero is a node and each match is a node. One link respresents a participation, it is labelled with "win" or "lose".
### second proposal 
Each hero is a node, each lineup (=group of five heroes) is a node, each match is a node. One link with "makes up" label represents the fact that the hero belongs to the lineup; one link with "win" or "lose" labels represents the fact that two lineups participate to the match and who won.

