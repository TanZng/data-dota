import os
import redis
from pprint import pprint
from pymongo import MongoClient
from geopy.geocoders import Nominatim
from geopy import distance

MONTHS = ['Dec', 'Feb', 'Jan', 'Jul', 'Jun', 'Mar', 'May', 'Nov', 'Oct', 'Sep']

REGION_MONTH_KEYS = {}

def main():
  redis_host = os.getenv('REDIS_HOST', 'localhost')
  redis_port = os.getenv('REDIS_PORT', '6379')
  mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')

  redisClient = redis.Redis(host=redis_host, port=redis_port, db=1)
  mongoClient = MongoClient(mongo_uri) #Mongo URI format

  # get the cities from mongo
  sunlightDB = mongoClient["SunLightDB"]
  regionDB = mongoClient["RegionsDB"]
  
  citiesData=sunlightDB.sunlight_collection.find({})
  # get regions from mongo
  regionsData=sunlightDB.regions_collection.find({})
  # group cities by region (closest)
  for city in citiesData:
    # pprint(city)
    # print("\n")
    findRegion(city, regionsData, redisClient)
  getMonthlyAverage(city)
  # idea: use a Redis sorted set to keep that info

  # tag the values
  return 0
  
# findRegion checks which regions is the neareat to a certain city and saves
# it in redis as a 
# region_name_month : city: value
# eg. US_WEST_January: { L.A : 200, San Francisco : 100, ... }
def findRegion(sunlight, regionsData, redisClient):
  # find the nearest region/country to the given city  
  near_region = ""
  distance = float('inf')

  for region in regionsData:
    geolocator = Nominatim(user_agent="avg_distance_cities")
    target_city_coords = geolocator.geocode(sunlight["City"])
    print((target_city_coords.latitude, target_city_coords.longitude))

    region_city_coords = geolocator.geocode(region["city"])
    print((region_city_coords.latitude, region_city_coords.longitude))

    distance_tmp = distance.distance(target_city_coords, region_city_coords).km

    if distance_tmp < distance:
      near_region = region["region_name"]
      distance = distance_tmp
  
  for month in MONTHS:
    key_name = near_region+"_"+month
    REGION_MONTH_KEYS[key_name] = 0 
    redisClient.zadd(key_name, sunlight[month], sunlight["City"])


def getMonthlyAverage(city):
  for k,v in REGION_MONTH_KEYS:
    pprint(redisClient.zrange(k, 0, -1, withscores=True))
 

main()