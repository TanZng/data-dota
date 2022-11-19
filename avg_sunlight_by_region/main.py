from pymongo import MongoClient
import redis

REGIONS = {
  "US WEST": 0,
  "US EAST": 0,
  "EUROPE": 0,
  "SINGAPORE": 0,
  "DUBAI": 0,
  "AUSTRALIA": 0,
  "STOCKHOLM": 0,
  "AUSTRIA": 0,
  "BRAZIL": 0,
  "SOUTHAFRICA": 0,
  "PW TELECOM SHANGHAI": 0,
  "PW UNICOM": 0,
  "CHILE": 0,
  "PERU": 0,
  "INDIA": 0,
  "PW TELECOM GUANGDONG": 0,
  "PW TELECOM ZHEJIANG": 0,
  "JAPAN": 0,
  "PW TELECOM WUHAN": 0,
  "PW UNICOM TIANJIN": 0,
  "TAIWAN": 0,
  "ARGENTINA": 0,
}

def main():
  redisClient = redis.Redis(host='redis', port=6379, db=1)
  mongoClient = MongoClient("mongodb://mongo:27017/") #Mongo URI format
  
  # get regions from mongo?
  # REGIONS = ...

  # get the cities from mongo
  citiesData = mongoClient["sunlight_collection"]
  
  # group cities by region (closest)
  for city in citiesData:
    print(city+"\n")
    findRegion(city)
    getMonthlyAverage(city)
    # use a Redis sorted set to keep that info
  
def findRegion(city):
  # find the nearest region/country to the given city
  pass

def getMonthlyAverage(city):
  # get the avg of the region by month
  pass
  