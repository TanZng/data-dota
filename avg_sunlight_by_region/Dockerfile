FROM python:3.8.14

COPY . .

RUN pip install -r requirements.txt

ENV REDIS_HOST="redis"
ENV REDIS_PORT=6379
ENV MONGO_URI="mongodb://mongo:27017/"
ENV MONGO_URI="mongodb://mongo:27017/"

CMD [ "python", "./main.py"]
