#!/bin/bash

FILE=./.env
if [ ! -f "$FILE" ]; then
sh -c "
cat <<EOF >>./.env
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
AIRFLOW_UID=$(id -u)
AIRFLOW_GID=0
_PIP_ADDITIONAL_REQUIREMENTS=xlsx2csv==0.7.8 faker==8.12.1 apache-airflow-providers-mongo==2.3.1 apache-airflow-providers-docker==2.1.0
EOF
"
fi

FILE=./docker-socket-proxy.yaml
if [ ! -f "$FILE" ]; then
sh -c "
cat <<EOF >>./docker-socket-proxy.yaml
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
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
EOF
"
fi

docker build -f ./avg_sunlight_by_region/Dockerfile -t avg_sunlight_by_region ./avg_sunlight_by_region

docker compose up airflow-init

docker compose up --build --force-recreate -d

docker compose exec airflow-webserver airflow connections add 'postgres_default' --conn-uri 'postgres://user:password@postgres:5432'

docker compose exec airflow-webserver airflow connections add 'mongo_default' --conn-uri 'mongodb://mongo:27017'

docker compose exec airflow-webserver airflow connections add 'neo4j_default' --conn-uri 'bolt://neo:7687'