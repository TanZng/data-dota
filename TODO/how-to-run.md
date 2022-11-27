Create a .env file

> Get the AIRFLOW_UID using `id -u`

```s
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
AIRFLOW_UID=1000
AIRFLOW_GID=0
_PIP_ADDITIONAL_REQUIREMENTS=xlsx2csv==0.7.8 faker==8.12.1 apache-airflow-providers-mongo==2.3.1 apache-airflow-providers-docker==2.1.0
```

Create an `docker-socket-proxy.yaml` file depending on your os:
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
    ports:
      - 2375:2375
    volumes:
      - type: bind
        source: /var/run/docker.sock
        target: /var/run/docker.sock:ro
    # Linux
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