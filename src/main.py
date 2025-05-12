import os

from tinkerforge.ip_connection import IPConnection

from tinkerforge.bricklet_ptc_v2 import BrickletPTCV2
from tinkerforge.bricklet_piezo_speaker_v2 import BrickletPiezoSpeakerV2
from tinkerforge.bricklet_ambient_light_v3 import BrickletAmbientLightV3

from MoistureSensore import MoistureSensor

import time

class Statistics:
    def __init__(self, title, unit, min, max):
        self._current = None

        self.title = title
        self.unit = unit
        self.minimum = max
        self.maximum = min

    def set_current(self, value):
        self._current = value
        self.minimum = min(self.minimum, value)
        self.maximum = max(self.maximum, value)

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

    moisture_sensor = MoistureSensor(conn, "ViW", 1000)

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
        print("\rconnection closed")

