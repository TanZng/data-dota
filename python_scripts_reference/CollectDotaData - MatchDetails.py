class ResponseStatusCodeException(Exception):
    def __init__(self, code, message ="HTML status code return: "):
        self.code = code
        self.message = message
        super().__init__(self.message)
    def __str__(self):
        return self.message + str(self.code)

class MatchNotFoundException(Exception):
    def __init__(self, message ="Match was not found!"):
        self.message = message
        super().__init__(self.message)
    def __str__(self):
        return self.message

import requests, json, pandas as pd
import time
from pynput import keyboard
from threading import Thread
import os

class Requester(Thread):
    def __init__(self):
        print("Initialising...")
        super(Requester,self).__init__()
        # http_proxy  = "http://10.4.4.50:58101"
        # https_proxy = "http://10.4.4.50:58101"

        # self.proxies = { 
        #             "http"  : http_proxy, 
        #             "https" : https_proxy
        #             }
        self.openDotaUrl = "https://api.opendota.com/api/"
        self.getMatch = "matches/"
        if os.path.isfile("./data/matchCounter") > 0:
            counterFile = open("./data/matchCounter",'r')

            self.counter = int(counterFile.read())
        else:
            counterFile = open("./data/matchCounter",'w+')
            self.counter = 0
            counterFile.write(str(self.counter))
        counterFile.close()

        self.matchId = pd.read_csv("./data/matches",skiprows=range(1,self.counter))

        self.dataFile = open("./data/matchDetails","a+")
        self.listNotFound = open("./data/matchesNotFound","a+")
        self.running = False
        self.program_running = True
        print("Initialisation done, press '`' to start/stop sending requests")

    def start_requesting(self):
        print("Starts sending requests")
        self.running = True

    def stop_requesting(self):
        print("Stops sending requests")
        self.running = False

    def exit(self):
        self.stop_requesting()
        print("Exitting")
        self.program_running = False
        self.dataFile.close()
        self.listNotFound.close()

    def run(self):
        while self.program_running:
            i = 0
            while self.running and i < len(self.matchId):
                requestUrl = self.openDotaUrl+self.getMatch+str(self.matchId["match_id"].values[i])
                
                print (requestUrl)

                retry = True
                write = True
                while (retry and self.running):
                    try:
                        response = requests.get(requestUrl)
                        if (response.status_code == 200):
                            response=response.json()
                            retry = False
                        elif (response.status_code==404):
                            raise MatchNotFoundException
                        else:
                            raise ResponseStatusCodeException(response.status_code)
                            
                    except requests.exceptions.RequestException as e:
                        raise SystemExit(e)
                    except MatchNotFoundException as e:
                        print (e)
                        self.listNotFound.write(str(self.matchId["match_id"].values[i])+"\n")
                        retry = False
                        write = False
                    except (ResponseStatusCodeException) as e:
                        print(e,", retrying...")
                        time.sleep(5)

                # accountIds = []
                # heroIds = []
                # for account in response["players"]:
                #     accountIds.append(account["account_id"])
                #     heroIds.append(account["hero_id"])
                # accountIds = json.dumps(accountIds)

                # if ("comeback" in response):
                #     comeback = response["comeback"]
                # else:
                #     comeback = "null"

                # if ("stomp" in response):
                #     stomp = response["stomp"]
                # else:
                #     stomp = "null"

                # matchDetails = {
                #     "match_id":response["match_id"],
                #     "chat":response["chat"],
                #     "duration":response["duration"],
                #     "game_mode":response["game_mode"],
                #     "human_players":response["human_players"],
                #     "negative_votes":response["negative_votes"],
                #     "positive_votes":response["positive_votes"],
                #     "start_time":response["start_time"],
                #     # "teamfights":response["teamfights"],
                #     "version":response["version"],
                #     "players":accountIds,
                #     "heroes":heroIds,
                #     "region":response["region"],
                #     "comeback":comeback,
                #     "stomp":stomp
                # }
                
                if (self.running and write):
                    self.dataFile.write(",")

                    json.dump(response,self.dataFile)

                    counterFile = open("./data/matchCounter",'w')
                    counterFile.write(str(i+self.counter+1))
                    counterFile.close()

                i+=1
                
            time.sleep(0.1)

start_stop_key = keyboard.KeyCode(char='`')
exit_key = keyboard.Key.esc

autoRequester = Requester()
autoRequester.start()

def ListenInput(key):
    if key == start_stop_key:
        if autoRequester.running:
            autoRequester.stop_requesting()
        else:
            autoRequester.start_requesting()
    elif key == exit_key:
        autoRequester.exit()
        listenInput.stop()

listenInput = keyboard.Listener( on_press = ListenInput)
listenInput.start()
listenInput.join()