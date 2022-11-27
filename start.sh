#!/bin/bash

docker build -f ./avg_sunlight_by_region/Dockerfile -t avg_sunlight_by_region ./avg_sunlight_by_region

docker compose up airflow-init

docker compose up --build --force-recreate -d

docker compose exec airflow-webserver airflow connections add 'postgres_default' --conn-uri 'postgres://user:password@postgres:5432'

docker compose exec airflow-webserver airflow connections add 'mongo_default' --conn-uri 'mongodb://mongo:27017'

docker compose exec airflow-webserver airflow connections add 'neo4j_default' --conn-uri 'bolt://neo:7687'