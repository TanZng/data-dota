Run this **once**:
```sh
docker compose up airflow-init
```
If the exit code is 0 then it's all good.

```sh
docker compose up
```

After it is up, add a new connection:

* Database - airflow
* Username - airflow
* Password - airflow