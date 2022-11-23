Create a .env file

> Get the AIRFLOW_UID using `id -u`

```s
_AIRFLOW_WWW_USER_USERNAME=airflow
_AIRFLOW_WWW_USER_PASSWORD=airflow
AIRFLOW_UID=1000
AIRFLOW_GID=0
_PIP_ADDITIONAL_REQUIREMENTS=xlsx2csv==0.7.8 faker==8.12.1 apache-airflow-providers-mongo==2.3.1 apache-airflow-providers-docker==2.1.0
```

Create an airflow-compose.yaml file
```yaml
x-airflow-common: &airflow-common
  # In order to add custom dependencies or upgrade provider packages you can use your extended image.
  # Comment the image line, place your Dockerfile in the directory where you placed the docker-compose.yaml
  # and uncomment the "build" line below, Then run `docker-compose build` to build the images.
  image: ${AIRFLOW_IMAGE_NAME:-apache/airflow:2.1.3}
  # build: .
  environment: &airflow-common-env
    AIRFLOW__CORE__EXECUTOR: CeleryExecutor
    AIRFLOW__CORE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres-airflow/airflow
    AIRFLOW__CELERY__RESULT_BACKEND: db+postgresql://airflow:airflow@postgres-airflow/airflow
    AIRFLOW__CELERY__BROKER_URL: redis://:@redis-airflow:6379/0
    AIRFLOW__CORE__FERNET_KEY: ""
    AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: "true"
    AIRFLOW__CORE__LOAD_EXAMPLES: "false"
    AIRFLOW_HOME: "/opt/airflow"
    AIRFLOW__CORE_dags_folder: "/opt/airflow/dags"
    AIRFLOW__CORE__ENABLE_XCOM_PICKLING: "true" # "_run_image of the DockerOperator returns now a python string, not a byte string" Ref: https://github.com/apache/airflow/issues/13487
    AIRFLOW__API__AUTH_BACKEND: "airflow.api.auth.backend.basic_auth"
    _PIP_ADDITIONAL_REQUIREMENTS: ${_PIP_ADDITIONAL_REQUIREMENTS:-}
  volumes:
    - ./airflow/dags:/opt/airflow/dags
    - ./airflow/logs:/opt/airflow/logs
    - ./airflow/plugins:/opt/airflow/plugins
    - ./airflow/config/airflow.cfg:/opt/airflow/airflow.cfg
  user: "${AIRFLOW_UID:-50000}:${AIRFLOW_GID:-0}"
  depends_on:
    redis-airflow:
      condition: service_healthy
    postgres-airflow:
      condition: service_healthy
services:
  postgres-airflow:
    image: postgres:13.8-bullseye
    hostname: postgres-airflow
    container_name: postgres-airflow
    restart: always
    environment:
      POSTGRES_DB: airflow
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      PGDATA: /var/lib/postgresql/data/pgdata
    ports:
      - "5433:5432"
    volumes:
      - type: bind
        source: ./tmp/postgres-data-airflow
        target: /var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "airflow"]
      interval: 5s
      retries: 5
  redis-airflow: 
    image: redis:6.0.16-bullseye
    image: redis:6.0.16-bullseye
    hostname: redis-airflow
    container_name: redis-airflow
    restart: always
    ports:
      - "6380:6379"
    volumes:
      - type: bind
        source: ./tmp/redis-data-airflow
        target: /data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 30s
      retries: 50
  airflow-webserver:
    <<: *airflow-common
    command: webserver
    ports:
      - 8080:8080
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:8080/health"]
      interval: 10s
      timeout: 10s
      retries: 5
    restart: always
  airflow-scheduler:
    <<: *airflow-common
    command: scheduler
    healthcheck:
      test:
        [
          "CMD-SHELL",
          'airflow jobs check --job-type SchedulerJob --hostname "$${HOSTNAME}"',
        ]
      interval: 10s
      timeout: 10s
      retries: 5
    restart: always
  airflow-worker:
    <<: *airflow-common
    command: celery worker
    healthcheck:
      test:
        - "CMD-SHELL"
        - 'celery --app airflow.executors.celery_executor.app inspect ping -d "celery@$${HOSTNAME}"'
      interval: 10s
      timeout: 10s
      retries: 5
    restart: always
  airflow-init:
    <<: *airflow-common
    profiles: ["init"]
    entrypoint: /bin/bash
    command:
      - -c
      - |
        function ver() {
          printf "%04d%04d%04d%04d" $${1//./ }
        }
        airflow_version=$$(gosu airflow airflow version)
        airflow_version_comparable=$$(ver $${airflow_version})
        min_airflow_version=2.1.0
        min_airlfow_version_comparable=$$(ver $${min_airflow_version})
        if (( airflow_version_comparable < min_airlfow_version_comparable )); then
          echo -e "\033[1;31mERROR!!!: Too old Airflow version $${airflow_version}!\e[0m"
          echo "The minimum Airflow version supported: $${min_airflow_version}. Only use this or higher!"
          exit 1
        fi
        if [[ -z "${AIRFLOW_UID}" ]]; then
          echo -e "\033[1;31mERROR!!!: AIRFLOW_UID not set!\e[0m"
          echo "Please follow these instructions to set AIRFLOW_UID and AIRFLOW_GID environment variables:
            https://airflow.apache.org/docs/apache-airflow/stable/start/docker.html#initializing-environment"
          exit 1
        fi
        one_meg=1048576
        mem_available=$$(($$(getconf _PHYS_PAGES) * $$(getconf PAGE_SIZE) / one_meg))
        cpus_available=$$(grep -cE 'cpu[0-9]+' /proc/stat)
        disk_available=$$(df / | tail -1 | awk '{print $$4}')
        warning_resources="false"
        if (( mem_available < 4000 )) ; then
          echo -e "\033[1;33mWARNING!!!: Not enough memory available for Docker.\e[0m"
          echo "At least 4GB of memory required. You have $$(numfmt --to iec $$((mem_available * one_meg)))"
          warning_resources="true"
        fi
        if (( cpus_available < 2 )); then
          echo -e "\033[1;33mWARNING!!!: Not enough CPUS available for Docker.\e[0m"
          echo "At least 2 CPUs recommended. You have $${cpus_available}"
          warning_resources="true"
        fi
        if (( disk_available < one_meg * 10 )); then
          echo -e "\033[1;33mWARNING!!!: Not enough Disk space available for Docker.\e[0m"
          echo "At least 10 GBs recommended. You have $$(numfmt --to iec $$((disk_available * 1024 )))"
          warning_resources="true"
        fi
        if [[ $${warning_resources} == "true" ]]; then
          echo
          echo -e "\033[1;33mWARNING!!!: You have not enough resources to run Airflow (see above)!\e[0m"
          echo "Please follow the instructions to increase amount of resources available:"
          echo "   https://airflow.apache.org/docs/apache-airflow/stable/start/docker.html#before-you-begin"
        fi
        mkdir -p /sources/logs /sources/dags /sources/plugins
        chown -R "${AIRFLOW_UID}:${AIRFLOW_GID}" /sources/{logs,dags,plugins}
        exec /entrypoint airflow version
    environment:
      <<: *airflow-common-env
      _AIRFLOW_DB_UPGRADE: "true"
      _AIRFLOW_WWW_USER_CREATE: "true"
      _AIRFLOW_WWW_USER_USERNAME: ${_AIRFLOW_WWW_USER_USERNAME:-airflow}
      _AIRFLOW_WWW_USER_PASSWORD: ${_AIRFLOW_WWW_USER_PASSWORD:-airflow}
    user: "0:${AIRFLOW_GID:-0}"
    volumes:
      - ./airflow:/sources
  flower:
    <<: *airflow-common
    command: celery flower
    ports:
      - 5555:5555
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:5555/"]
      interval: 10s
      timeout: 10s
      retries: 5
    restart: always
  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:0.1.1
    environment:
      CONTAINERS: 1
      IMAGES: 1
      AUTH: 1
      POST: 1
    privileged: true
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro # this may change depending the OS
    restart: always
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