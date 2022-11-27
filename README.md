# Report: Data dota

## Table of contents
- [Report: Data dota](#report-data-dota)
  - [Table of contents](#table-of-contents)
- [Summary](#summary)
- [Pipeline](#pipeline)
  - [Ingestion](#ingestion)
  - [Staging](#staging)
    - [Cleansing](#cleansing)
    - [Transformations](#transformations)
    - [Enrichments](#enrichments)
  - [Production](#production)
    - [Queries](#queries)
- [Conclusion](#conclusion)
- [How to run?](#how-to-run)
  - [Linux / MacOS](#linux--macos)
  - [Windows](#windows)

# Summary

Questions formulated:
- Does sunlight affect match stamp or comeback?
- Spike in win-rate by hero/season/month?
- Which lineup (other heroes) favors certain champions?


![Pipeline overview](assets/DataPipeline.png)

# Pipeline

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

### Transformations

### Enrichments

## Production

### Queries

# Conclusion

# How to run?

## Linux / MacOS

Run

```s
./start.sh
```

## Windows

Create a `.env` file

> Get the AIRFLOW_UID using `id -u`

```s
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
AIRFLOW_UID=1000
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
docker compose exec airflow-webserver airflow connections add 'postgres_default' --conn-uri 'postgres://user:password@postgres:5432'

docker compose exec airflow-webserver airflow connections add 'mongo_default' --conn-uri 'mongodb://mongo:27017'

docker compose exec airflow-webserver airflow connections add 'neo4j_default' --conn-uri 'bolt://neo:7687'
```

Build the image used by the Docker operator
```sh
docker build -f ./avg_sunlight_by_region/Dockerfile -t avg_sunlight_by_region ./avg_sunlight_by_region
```