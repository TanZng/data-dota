import os
import redis
import  math
import  random
from pprint import pprint
from pymongo import MongoClient
from geopy.geocoders import Nominatim
from geopy import distance as geodist

MONTHS = ['Dec', 'Feb', 'Jan', 'Jul', 'Jun', 'Mar', 'May', 'Nov', 'Oct', 'Sep']

REGION_MONTH_KEYS = {}

def main():
  redis_host = os.getenv('REDIS_HOST', 'localhost')
  redis_port = os.getenv('REDIS_PORT', '6379')
  mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')

  redisClient = redis.Redis(host=redis_host, port=redis_port, db=1)
  mongoClient = MongoClient(mongo_uri) #Mongo URI format

  sunlightDB = mongoClient["SunLightDB"]
  constant_db = mongoClient["constant_db"]
  
  citiesData=sunlightDB.sunlight_collection.find({})
  regionsData=constant_db.region_city.find({})

  for city in citiesData:
    findRegion(city, regionsData, redisClient)
  getMonthlyAverage(city, redisClient)
  # idea: use a Redis sorted set to keep that info

  # tag the values
  return 0
  
# findRegion checks which regions is the nearest to a certain city and saves
# it in redis as a 
# region_name_month : city: value
# eg. US_WEST_January: { L.A : 200, San Francisco : 100, ... }
def findRegion(sunlight, regionsData, redisClient):
  # find the nearest region/country to the given city  
  near_region = ""
  distance_diff = float('inf')

  target_city_coords = getCoordinates(sunlight["City"])

  for region in regionsData:
    region_city_coords = getCoordinates(region["city_name"])
    
    print(target_city_coords)
    print(region_city_coords)
    distance_tmp = geodist.distance(target_city_coords, region_city_coords).km
    if distance_tmp <= distance_diff:
      near_region = region["region_name"].replace(" ", "_")
      distance_diff = distance_tmp
  
  for month in MONTHS:
    key_name = near_region+"_"+month
    pprint(key_name)
    REGION_MONTH_KEYS[key_name] = 0 
    redisClient.zadd(key_name, {sunlight["City"]: float(sunlight[month])} )


def getMonthlyAverage(city, redisClient):
  print(REGION_MONTH_KEYS)
  for k in REGION_MONTH_KEYS:
    print("\n")
    print(k)
    print(redisClient.zrange(k, 0, -1, withscores=True))
    print("\n")
 

def getCoordinates(city_name):
  geolocator = Nominatim(user_agent="avg_distance_cities")
  try:
    location = geolocator.geocode(city_name)
    return (location.latitude, location.longitude)
  except:
    return randlatlon1()

def randlatlon1():
    pi = math.pi
    cf = 180.0 / pi  # radians to degrees Correction Factor

    # get a random Gaussian 3D vector:
    gx = random.gauss(0.0, 1.0)
    gy = random.gauss(0.0, 1.0)
    gz = random.gauss(0.0, 1.0)

    # normalize to an equidistributed (x,y,z) point on the unit sphere:
    norm2 = gx*gx + gy*gy + gz*gz
    norm1 = 1.0 / math.sqrt(norm2)
    x = gx * norm1
    y = gy * norm1
    z = gz * norm1

    radLat = math.asin(z)      # latitude  in radians
    radLon = math.atan2(y,x)   # longitude in radians

    return (round(cf*radLat, 5), round(cf*radLon, 5))

main()
