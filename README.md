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
```

Build the image used by the Docker operator
```sh
docker build -f ./avg_sunlight_by_region/Dockerfile -t avg_sunlight_by_region ./avg_sunlight_by_region
```