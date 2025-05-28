import os
from datetime import datetime

# discord-notification imports
import http.client
import json
import time

#import Discord
from count_down import CountDown
from alarm import Alarm

from tinkerforge.ip_connection import IPConnection

from tinkerforge.bricklet_ptc_v2 import BrickletPTCV2
from tinkerforge.bricklet_ambient_light_v3 import BrickletAmbientLightV3
from tinkerforge.bricklet_humidity_v2 import BrickletHumidityV2
from tinkerforge.bricklet_motion_detector_v2 import BrickletMotionDetectorV2

from tinkerforge.bricklet_e_paper_296x128 import BrickletEPaper296x128
from tinkerforge.bricklet_nfc import BrickletNFC

class Statistics:
    def __init__(self, title, unit, min, max, critical_min=None, critical_max=None):
        self._current = None
        self.is_critical = False

        self.title = title
        self.unit = unit
        self.measured_minimum = max
        self.measured_maximum = min

        self.critical_min = critical_min
        self.critical_max = critical_max

        # time stamp when the last notification was send
        self.last_notified = datetime(2000, 1, 1)

    def set_current(self, value):
        self._current = value
        self.measured_minimum = min(self.measured_minimum, value)
        self.measured_maximum = max(self.measured_maximum, value)

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
        minimum: {self.measured_minimum}{self.unit}
        maximum: {self.measured_maximum}{self.unit}
        """.strip()

# used as global state
class SensorData:
    def __init__(self):
        self.temperature = Statistics("TEMPERATURE", "C", 0, 80)
        self.illuminance = Statistics("ILLUMINANCE", "lx", 0, 1600, critical_min=50)
        self.moisture = Statistics("MOISTURE", "%RH", 0, 100)

    def __iter__(self):
        yield self.temperature
        yield self.illuminance
        yield self.moisture

        return StopIteration

    def __str__(self):
        return "\n".join([str(data) for data in self])

ALARM = None
COUNT_DOWN = None
SENSOR_DATA = SensorData()

IP = "172.20.10.242"
PORT = 4223

# delay between notification when a critical measurement is taken
NOTIFICATION_DELAY_SECONDS = 60 * 5

def temperature_callback(temperature):
    SENSOR_DATA.temperature.set_current(temperature / 100)

def ambient_light_callback(illuminance):
    SENSOR_DATA.illuminance.set_current(illuminance / 100)

def moisture_callback(moisture):
    SENSOR_DATA.moisture.set_current(moisture / 100)

def start_motion_detection():
    if ALARM.can_trigger():
        COUNT_DOWN.start_count_down(10, ALARM.trigger_alarm)

def end_motion_detection():
    print("stop motion detected")

def cb_reader_state_changed(state, idle, nfc):
    if state == nfc.READER_STATE_REQUEST_TAG_ID_READY:
        ret = nfc.reader_get_tag_id()

        print("Found tag of type " +
              str(ret.tag_type) +
              " with ID [" +
              " ".join(map(str, map('0x{:02X}'.format, ret.tag_id))) +
              "]")

    if idle:
        nfc.reader_request_tag_id()

if __name__ == "__main__":
    conn = IPConnection()

    # actors
    paper_display = BrickletEPaper296x128("XGL", conn)

    # sensors
    COUNT_DOWN = CountDown(conn)
    ALARM = Alarm(conn, COUNT_DOWN, 60)

    motion_detection = BrickletMotionDetectorV2("ML4", conn)
    ambient_light = BrickletAmbientLightV3("Pdw", conn)
    temp = BrickletPTCV2("Wcg", conn)
    moisture_sensore = BrickletHumidityV2("ViW", conn)
    nfc = BrickletNFC("22ND", conn)

    conn.connect(IP, PORT)

    # register callbacks
    temp.register_callback(temp.CALLBACK_TEMPERATURE, temperature_callback)
    temp.set_temperature_callback_configuration(1000, False, "x", 0, 0)

    ambient_light.register_callback(ambient_light.CALLBACK_ILLUMINANCE, ambient_light_callback)
    ambient_light.set_illuminance_callback_configuration(1000, False, "x", 0, 0)

    moisture_sensore.register_callback(moisture_sensore.CALLBACK_HUMIDITY, moisture_callback)
    moisture_sensore.set_humidity_callback_configuration(1000, False, "x", 0, 0)

    nfc.register_callback(nfc.CALLBACK_READER_STATE_CHANGED,
                          lambda x, y: cb_reader_state_changed(x, y, nfc))
    nfc.set_mode(nfc.MODE_READER)
    
    motion_detection.register_callback(motion_detection.CALLBACK_MOTION_DETECTED, start_motion_detection)
    motion_detection.register_callback(motion_detection.CALLBACK_DETECTION_CYCLE_ENDED, end_motion_detection)

    ALARM.setup()

    count = 0

    try:
        while True:
            # clear screen
            if os.name == "nt":
                os.system("cls")
            else:
                os.system("clear")

            now = datetime.now()

            print(SENSOR_DATA)

            paper_display.fill_display(paper_display.COLOR_BLACK)
            if count % 20 == 0:
                for (i, data) in enumerate(SENSOR_DATA):
                    paper_display.draw_text(
                        8, 16 * (i + 1),
                        paper_display.FONT_12X16,
                        paper_display.COLOR_RED if data.is_critical else paper_display.COLOR_WHITE,
                        paper_display.ORIENTATION_HORIZONTAL,
                        f"{data.title}:{data.get_current()} {data.unit}")
                paper_display.draw()

            for data in SENSOR_DATA:

                notified_seconds_ago = (now - data.last_notified).total_seconds()
                if(data.is_critical and notified_seconds_ago > NOTIFICATION_DELAY_SECONDS):
                    #Discord.send(f"illuminance is critical: {SENSOR_DATA.illuminance.get_current()}{SENSOR_DATA.illuminance.unit}")
                    data.last_notified = now

            ALARM.update()

            time.sleep(0.1)

    except KeyboardInterrupt:
        # the user ended the program so we absorb the exception
        pass
    finally:
        # gracefully close the connection
        conn.disconnect()
        print("\rconnection closed")

        #Discord.send(f"""
        #    Data before disconnect:
        #        {str(SENSOR_DATA)}
        #    """)
