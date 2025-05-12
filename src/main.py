import os

# discord-notification imports
import sys
import http.client
import json

from tinkerforge.ip_connection import IPConnection

from tinkerforge.bricklet_ptc_v2 import BrickletPTCV2
from tinkerforge.bricklet_piezo_speaker_v2 import BrickletPiezoSpeakerV2
from tinkerforge.bricklet_ambient_light_v3 import BrickletAmbientLightV3

import time

class Statistics:
    def __init__(self, title, unit, min, max, critical_min=None, critical_max=None):
        self._current = None
        self.is_critical = False

        self.title = title
        self.unit = unit
        self.minimum = max
        self.maximum = min

        self.critical_min = critical_min
        self.critical_max = critical_max

    def set_current(self, value):
        self._current = value
        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)

        self.is_critical = (
                self.critical_min is not None and self.critical_min > self._current
        ) or (
                self.critical_max is not None and self.critical_max < self._current
        )

    def get_current(self):
        return self._current

    def __str__(self):
        return f"""
        {self.title}
        current: {self._current}{self.unit}
        minimum: {self.minimum}{self.unit}
        maximum: {self.maximum}{self.unit}
        """

# used as global state
class SensorData:
    def __init__(self):
        self.temperature = Statistics("TEMPERATURE", "°C", 0, 80)
        self.illuminance = Statistics("ILLUMINANCE", "lx", 0, 1600)

with open("wh.dat") as f:
    WEBHOOK = f.readline()

class Discord:
    @staticmethod
    def send(message):
        global WEBHOOK
        # your webhook URL
        host = "discord.com"

        payload = json.dumps({"content": message})

        headers = {
            "Content-Type": "application/json"
        }

        # get the connection and make the request
        connection = http.client.HTTPSConnection(host)
        connection.request("POST", WEBHOOK, body=payload, headers=headers)

        # get the response
        response = connection.getresponse()
        result = response.read()

        # return back to the calling function with the result
        return f"{response.status} {response.reason}\n{result.decode()}"

        # send the messsage and print the response
        print( send( sys.argv[1] ) )

IP = "172.20.10.242"
PORT = 4223

SENSOR_DATA = SensorData()

def temperature_callback(temperature):
    SENSOR_DATA.temperature.set_current(temperature / 100)

def ambient_light_callback(illuminance):
    SENSOR_DATA.illuminance.set_current(illuminance / 100)

if __name__ == "__main__":
    conn = IPConnection()

    speaker = BrickletPiezoSpeakerV2("R7M", conn)

    ambient_light = BrickletAmbientLightV3("Pdw", conn)
    temp = BrickletPTCV2("Wcg", conn)

    conn.connect(IP, PORT)

    # register callbacks
    temp.register_callback(temp.CALLBACK_TEMPERATURE, temperature_callback)
    temp.set_temperature_callback_configuration(1000, False, "x", 0, 0)

    ambient_light.register_callback(ambient_light.CALLBACK_ILLUMINANCE, ambient_light_callback)
    ambient_light.set_illuminance_callback_configuration(1000, False, "x", 0, 0)

    try:
        while True:
            # clear screen
            if os.name == "nt":
                os.system("cls")
            else:
                os.system("clear")

            print("\tLIVE DATA")
            print("\t=========")
            print(SENSOR_DATA.temperature)
            print(SENSOR_DATA.illuminance)

            time.sleep(1) # sleep for 1 second

    except KeyboardInterrupt:
        # the user ended the program so we absorb the exception
        pass
    finally:
        # gracefully close the connection
        conn.disconnect()
        Discord.send("\tData before DC:")
        Discord.send("\t=========")
        Discord.send(str(SENSOR_DATA.temperature))
        Discord.send(str(SENSOR_DATA.illuminance))
        Discord.send("\t=========")
        print("\rconnection closed")

