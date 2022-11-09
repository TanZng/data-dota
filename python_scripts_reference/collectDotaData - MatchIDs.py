class ResponseResultsCountException(Exception):
    def __init__(self, message ="Number of results not equal to 100"):
        self.message = message
        super().__init__(self.message)

class ResponseStatusCodeException(Exception):
    def __init__(self, code, message ="HTML status code return: "):
        self.code = code
        self.message = message
        super().__init__(self.message)
    def __str__(self):
        return self.message + str(self.code)

from pickle import FALSE, TRUE
import requests, pandas as pd
import time

apiKey = "5178694816A055E8ED1B5E0F822590F5"
steamUrl = "https://api.steampowered.com/IDOTA2Match_570/"
getMatch = "GetMatchHistoryBySequenceNum/v1/"
datafile = pd.read_csv("./data/matches")
lastRow = datafile.tail(1)

# requestUrl = steamUrl+getMatch+"?key="+apiKey+"&matches_requested=100"

requestUrl = steamUrl+getMatch+"?key="+apiKey+"&start_at_match_seq_num="+\
    str(lastRow['match_seq_num'].values[0])+"&matches_requested=100"

count = 1

while (count<1001):

    retry = TRUE
    while (retry==TRUE):
        try:
            response = requests.get(requestUrl)
            if (response.status_code!=200):
                raise ResponseStatusCodeException(response.status_code)
            else:
                response=response.json()
            if (len(response['result']['matches'])!=100):
                raise ResponseResultsCountException
            else:
                retry = FALSE
        except requests.exceptions.RequestException as e:
            raise SystemExit(e)
        except (ResponseResultsCountException,ResponseStatusCodeException) as e:
            time.sleep(0.1)

    matches = response['result']['matches']

    datafile = open("./data/matches","a+")

    for match in matches[1:]:
        datafile.write(str(match['match_id'])+","+str(match['match_seq_num'])+"\n")
        lastRow = match['match_seq_num']

    datafile.close()

    requestUrl = steamUrl+getMatch+"?key="+apiKey+"&start_at_match_seq_num="+\
        str(lastRow)+"&matches_requested=100"

    print(lastRow)

    count+=1