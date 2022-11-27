# Report: Data dota

## Table of contents
- [Report: Data dota](#report-data-dota)
  - [Table of contents](#table-of-contents)
- [Introduction](#introduction)
- [Pipeline](#pipeline)
  - [Ingestion](#ingestion)
  - [Staging](#staging)
    - [Cleansing](#cleansing)
    - [Transformations](#transformations)
    - [Enrichments](#enrichments)
  - [Production](#production)
    - [Queries](#queries)
- [Conclusion](#conclusion)
- [Project Submission Checklist](#project-submission-checklist)
- [How to run?](#how-to-run)
  - [Automatic](#automatic)
  - [Manual](#manual)

# Introduction

Questions formulated:
- Does sunlight affect how likely a match will feature a stomp or a comeback?
- Spike in win-rate by hero/season/month?
- Which lineup (other heroes) favors certain heroes?

# Pipeline

![Pipeline overview](assets/DataPipeline.png)

## Ingestion

For this projects we utilize 4 datasources:
1. Oficial Dota API
2. Open Dota API
3. Sunlight by city per month CSV
4. Dota constants in JSON

The data from the APIs are obtain by doing calls using Python.

The CSV and JSON files are obtained with a `curl` bash command.

The raw data injested are then stored in mongodb for ease of access.

## Staging

### Cleansing

One example of the cleansing step is the way we process the Dota region and sunlight cities in order to link the two. The original data we downloaded have a big issue concerning the location : Dota data were ordered by region (in other words, a dota server), while sunlight data are grouped by cities. So we first have to clean the Dota region name into something more obvious and then bind each Dota region with one or more cities from sunlight data. In order to do so, we added an attribute to the original Dota region DB: a city that is the approximate center of the aforementioned region. This is done manually because the amount of data is not big enough to make the automatic process worthwhile. Once that was done, all that was left was to join the two tables.

For the match details data, the raw JSON returned by the OpenDota API is enourmous: aside from the data we utilize in our project, there are various other useful data that are not analysed (like the game mode, whether or not a match is a tournament, the ending status of the two teams' buildings, etc), as well as a lot of unimportant data (in particular the cosmetics equipped by a player, and the duplication of match details in each player details in the match, expanding the raw data by 10 times). The first step is then to select only the attributes that we need.

### Transformations

For the match details data, now reduced to a select few attributes, we must first filter out any matches that have none of the analytical data that we need, such as the `stomp` as `comeback` attributes.

Afterwards, to better categorize the dimension attributes, we transform certain dimensions from raw numerical values to categories. This applies to the Duration dimension and the Sunlight dimension:
- We categorize the Duration dimension into 5 categories:
  - Very short: matches that end in under 15 minutes
  - Short: matches lasting between 15 and 30 minutes
  - Medium: matches lasting between 30 and 45 minutes
  - Long: matches lasting between 45 minutes and 1 hour
  - Very long: matches that go on for more than 1 hour
  
As all duration is at least a positive number, and the categories are all spaced out by 15 minutes, the transformation can be done directly with a calculation:

```bash
np.ceil(match_details['duration']/900).apply(lambda x: min(int(x),5))
```

- Likewise, the Sunlight dimension is also divided into 5 categories:
  - Very dark: months that have less than 85% of the yearly average sunlight
  - Dark: months having between 85% and 95% of the yearly average sunlight
  - Normal: months having between 95% and 105% of the yearly average sunlight
  - Bright: months having between 105% and 115% of the yearly average sunlight
  - Very bright: months that have more than 115% of the yearly average sunlight

The calculation here is slight more tricky, but nothing can't be solved with a little bit of maths:

```bash
np.ceil((min(max((monthly_sunlight[month_name]/average),0.85),1.3)-0.75)/0.1)
```

In short, the operation rescales the percentage of between monthly sunlight and yearly average from [0,+infinite] to [0.1,0.5] with the min/max operations, then multiplies the value by 10 and getting the integer ceiling, and we end up with integers between `1` and `5`

Also for the sunlight by city per month data, the documents are indexed to MongoDB, since it will be easy to manipulate in further steps as a collection than a CSV.

### Enrichments

An important enrichment that we performed is to the regions with their average sunlight per month. To make this happen we developed a python script and containerized it, it can be find in the ``avg_sunlight_by_region/`` folder. Then this script is ran by the ``DockerOperator`` from Airflow. 

The DockerOperator allows AirFlow to run Docker containers. We decide to get this task done using Docker to avoid run a huge script using the ``PythonOperator``. 

To obtain the average per month by region first we get from MongoDB the regions and a city of each one. Then from MongoDB we get the sunlight average by month of all the cities that were available. Then we relate all the cities from the sunlight data to the nearest region in a Redis sorted set, with the next structure:

```bash
zset:REGION_Month: { City1: XXX, City2: XXX, ... }
# e.g
# zset:US_EAST_January: { Miami: 281, NYC: 149, ... }
```

To define to which region a city belongs, we get the coordinates of the cities and calculating the distance between them using the ``geopy`` library.

> Its important to mention that ``geopy`` has a limit to query the coordinates, so when this is reach ot theres no internet connection a random coordinate is assignee to a city, so the pipeline continues working fine.

Once this is done, for each ``zset`` we calculate the average and keep the results in Redis with this structure:
```bash
REGION_Month: XXX
# e.g
# US_EAST_January: 210
```

We use redis so the next task can get these values from Redis.

## Production

For the first question that we have (concerning the gameplay overall gameplay performance in each match), the data naturally fit into a star schema:
- We have a central Fact table that contains all the matches, having measures being a stomp value and a comeback value
- The Duration, Sunlight level, Region, Timestamp axes along which we want to analyse, can all be made into dimension tables

As such, we decided to create a star schema for this part of the analytical question. The Duration and Sunlight tables can be generated easily with just an ID and a name for each categories. The fact table can be uploaded directly after the wrangling process: we already transformed the raw data for `duration` into IDs that point to the Duration table. The main issue is linking each match to a level of sunlight (Sunlight_level table). In order to do this, we created an ID in the fact table that is the `REGION_Month` of where and when the match was played. We then created a mapping table `Sunlight_map`, which points each `REGION_Month` to a corresponding `Sunlight_level`. In doing so, the star schema becomes a snowflake schema (albeit in just this dimension)

In order to represent the impact of the lineup (5 heroes) in a match, we were looking for a way to bind heroes to a lineup, and then each lineup to the match. So for this, naturally we chose a graph schema (using Neo4j).
The way we proceed is quite simple. First we created each node. Match nodes have just one attribute (its id) and were created according to the match_details DB staged in MongoDB (after the wrangling process). Hero nodes have two attributes (its id and its name) and were created with the heroes DB also in MongoDB. For Lineup nodes, it was a bit more tricky : as we didn't want to create all the lineup possible with all the heroes (which would represent approximately h*(h-1)(h-2)(h-3)(h-4) possibilities with h the number of heroes) because only few of them are used, we decided to create just the lineups used for matches we want to analyse. What's more, we retrieve the radiant_win attribute for each match to know which team won (the two teams in Dota are named `Radiant` and `Dire`, and there is always only 1 winning team, so this attribute can tell us exactly which team wins). So each Lineup nodes have 7 attributes (ids of the five heroes which are belonging to this lineup, the match id this lineup is referring to and the name of the team - Radiant or Dire).
Then we created the bindings between heroes and lineup (just a cypher statement according to the hero id) and between lineup and matches.

### Queries

For visualization we use:
- A Power BI dashboard for the star schema - /dashboard/OT_Star_schema.pbix
- NeoDash for the graph schema - http://localhost:5005/

# Conclusion & (potential) furture developments

Overall, the project has concluded fairly successfully. The ETL pipeline was completed, and all the goals we set at the beginning were achieved. There are some aspects that could be improved upon, but we are satisfied with the end result.

Some aspects that we noted for future developments:

- The automisation for updating the data can be improved. The match details query is currently written statically: we will always query the same matches (but this can be automatised fairly easily). Finding a city for each dota region (game server) is probably the hardest to automatise, and also the least worthwhile: we can just spend a few minutes each time a new server is built (which is by itself a rare occurance).

- The match details wrangling process can maybe be sped up by using redis as an intermediate to store the match_details while selecting attributes/filtering/transforming data. Currently the data are stored in mongoDB and processed directly in memory, but this method might not work if the data amount becomes too big. We can also process a small portion of data at a time.

- The star schema can be optimized by making the wrangling process directly link each match to a sunlight level, instead of creating a `REGION_Month` ID and an intermediate mapping table. This will make the wrangling process a bit heavier on the processing side, but it will greatly reduce the processing needed when we extract the data and run queries.

- Many other dimensions can be added in order to enrich our analytics: creating a Gamemode dimension, a Patch dimension, or utilizing other analytical data such as the gold income of each player/hero in the graph schema.

# Project Submission Checklist

- [x] Repository with the code, well documented
- [x] Docker-compose file to run the environment
- [x] Detailed description of the various steps
- [x] Report with the project design steps divided per area
- [x] Example dataset: the project testing should work offline, i.e., you need to have some sample data points.
- [x] Slides for the project presentation. You can do them too in markdown too.
- [x] Use airflow + pandas + mongodb + postgres + neo4j
- [x] Using REDIS for speeding up steps
- [x] STAR schema design includes maintenance upon updates
- [x] Creativity: data viz, serious analysis, performance analysis, extensive cleansing.
- [x] Launching docker containers via airflow to schedule job

# How to run?

## Automatic

> Works with Linux and MacOS

Run

```s
./start.sh
```

## Manual

Create a `.env` file with these values:

> ⚠️ IMPORTANT: Get the AIRFLOW_UID using `id -u`

```s
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
AIRFLOW_UID=
AIRFLOW_GID=0
_PIP_ADDITIONAL_REQUIREMENTS=xlsx2csv==0.7.8 faker==8.12.1 py2neo==2021.2.3 apache-airflow-providers-mongo==2.3.1 apache-airflow-providers-docker==2.1.0
```

Create an `docker-socket-proxy.yaml` file depending on your OS:
```yaml
services:
  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:0.1.1
    environment:
      CONTAINERS: 1
      IMAGES: 1
      AUTH: 1
      POST: 1
    restart: always
    privileged: true
    # Windows
    volumes:
      - type: bind
        source: /var/run/docker.sock
        target: /var/run/docker.sock:ro
    # Linux / MacOS
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
```

Run this **once**:
```sh
docker compose up airflow-init
```
If the exit code is 0 then it's all good.

```sh
docker compose up
```

After it is up, add a these connections (postgres-conn and mongo-conn):

```sh
docker compose exec airflow-webserver airflow connections add 'postgres_default' --conn-uri 'postgres://airflow:airflow@postgres:5432/airflow'

docker compose exec airflow-webserver airflow connections add 'mongo_default' --conn-uri 'mongodb://mongo:27017'

docker compose exec airflow-webserver airflow connections add 'neo4j_default' --conn-uri 'bolt://neo:7687'
```

Build the image used by the Docker operator
```sh
docker build -f ./avg_sunlight_by_region/Dockerfile -t avg_sunlight_by_region ./avg_sunlight_by_region
```

Visit:

| Service    | URL                    |
| ---------- | ---------------------- |
| Airflow    | http://localhost:8080/ |
| MotorAdmin | http://localhost:3020/ |
| NeoDash    | http://localhost:5005/ |