import sys
import http.client
import json

with open("wh.dat") as f:
    WEBHOOK = f.readline()

@staticmethod
def send(message):
    
    host = "discord.com"
    connection = http.client.HTTPSConnection(host)
        
    global WEBHOOK
    # your webhook URL

    payload = json.dumps({"content": message})

    headers = {
        "Content-Type": "application/json"
    }

    connection.request("POST", WEBHOOK, body=payload, headers=headers)

    # get the response
    response = connection.getresponse()
    result = response.read()

    # return back to the calling function with the result
    return f"{response.status} {response.reason}\n{result.decode()}"
