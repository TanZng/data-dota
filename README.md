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
- Does sunlight affect match stamp or comeback?
- Spike in win-rate by hero/season/month?
- Which lineup (other heroes) favors certain champions?

# Pipeline

![Pipeline overview](assets/DataPipeline.png)

## Ingestion

For this projects we count with 4 datasources:
1. Oficial Dota API
2. Open Dota API
3. Sunlight by city per month CSV
4. Dota constants in JSON

The data from the APIs was obtain by doing calls using Python.

The CSV and JSON files were obtained throw a `curl`.

## Staging

### Cleansing

One example of the cleansing step is the way we process the Dota region and sunlight cities to make it correspond. The original data we downloaded has a big issue concerning the location : Dota data was ordered by region (meaning each place where there is a dota server) and sunlight data by cities. So we first have to clean the Dota region name into something more obvious and then binding each Dota region with one or more cities from sunlight data. So we added an attribute to the original Dota region DB : cities. This is done manually because the amount of data is not big enough to make the automatism process relevant. One that was done, it was just about joining the two tables.

### Transformations

> Explain another transformation

Also the sunlight by city per month data is indexed to MongoDB, since it will be easy to manipulate in further steps as a collection than a CSV.

### Enrichments

> Explain a Enrichment

Another important enrichments that happen is to the regions with their average sunlight per month. To make this happen we developed a python script and containerized it, it can be find in the ``avg_sunlight_by_region/`` folder. Then this script is run by the ``DockerOperator`` from Airflow. 

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

We use redis so the next task can get this values from Redis.

## Production

> Explain why star schema

In order to represent the impact of the lineup (5 heroes) in a match, we were looking about something which bind each heroes to its lineup, and the each lineup to the match. So naturally we chose a graph schema edited with Neo4j data system.
The way we proceed is quite simple. First we created each node. Match nodes have just one attribute (its id) and were created according to the match_details DB staged in MongoDB (post wrangling process). Hero nodes have two attributes (its id and its name) and were created with the heroes DB also in MongoDB. For Lineup nodes, it was a bit more tricky : as we didn't want to create all the lineup possible with all the heroes (which would represent approximately h*(h-1)(h-2)(h-3)(h-4) possibilities with h the number of heroes) because only few of them are used, we decided to create just the lineup used for matches we want to analyse. What's more, we retrieve the radiant_win attribute for each match to know which team won (and so the other lost). So each Lineup nodes have 7 attributes (ids of the five heroes which are belonging to this lineup, the match id this lineup is referring to and the name of the team (radiant or dire)).
Than we created the bindings between heroes and lineup (just a cypher statement according to the hero id) and between lineup and matches.

### Queries

For visualization we use:
- MotorAdmin for the star schema - http://localhost:3020/
- NeoDash for the graph schema - http://localhost:5005/

# Conclusion


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