from pymongo import MongoClient
import redis
from pprint import pprint

REGIONS = {
  "US WEST": {"sunlight":0, "count":0},
  "US EAST": {"sunlight":0, "count":0},
  "EUROPE": {"sunlight":0, "count":0},
  "SINGAPORE": {"sunlight":0, "count":0},
  "DUBAI": {"sunlight":0, "count":0},
  "AUSTRALIA": {"sunlight":0, "count":0},
  "STOCKHOLM": {"sunlight":0, "count":0},
  "AUSTRIA": {"sunlight":0, "count":0},
  "BRAZIL": {"sunlight":0, "count":0},
  "SOUTHAFRICA": {"sunlight":0, "count":0},
  "PW TELECOM SHANGHAI": {"sunlight":0, "count":0},
  "PW UNICOM": {"sunlight":0, "count":0},
  "CHILE": {"sunlight":0, "count":0},
  "PERU": {"sunlight":0, "count":0},
  "INDIA": {"sunlight":0, "count":0},
  "PW TELECOM GUANGDONG": {"sunlight":0, "count":0},
  "PW TELECOM ZHEJIANG": {"sunlight":0, "count":0},
  "JAPAN": {"sunlight":0, "count":0},
  "PW TELECOM WUHAN": {"sunlight":0, "count":0},
  "PW UNICOM TIANJIN": {"sunlight":0, "count":0},
  "TAIWAN": {"sunlight":0, "count":0},
  "ARGENTINA": {"sunlight":0, "count":0},
}

def main():
  redisClient = redis.Redis(host='localhost', port=6379, db=1)
  mongoClient = MongoClient("mongodb://localhost:27017/") #Mongo URI format
  
  # get regions from mongo?
  # REGIONS = ...

  # get the cities from mongo
  myDB = mongoClient["MyDB"]
  citiesData=myDB.sunlight_collection.find({})
  # group cities by region (closest)
  for city in citiesData:
    pprint(city)
    print("\n")
    findRegion(city)
  getMonthlyAverage(city)
  # idea: use a Redis sorted set to keep that info

  # tag the values
  
# in redis
# region_name_month : city: value

def findRegion(city):
  # find the nearest region/country to the given city
  pass

def getMonthlyAverage(city):
  # get the avg of the region by month
  pass
  
main()