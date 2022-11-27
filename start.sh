#!/bin/bash

docker build -f ./avg_sunlight_by_region/Dockerfile -t avg_sunlight_by_region ./avg_sunlight_by_region

docker compose up --build --force-recreate