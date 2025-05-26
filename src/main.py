import os
from datetime import datetime

# discord-notification imports
import http.client
import json
import time

from tinkerforge.ip_connection import IPConnection

from tinkerforge.bricklet_ptc_v2 import BrickletPTCV2
from tinkerforge.bricklet_piezo_speaker_v2 import BrickletPiezoSpeakerV2
from tinkerforge.bricklet_ambient_light_v3 import BrickletAmbientLightV3
from tinkerforge.bricklet_humidity_v2 import BrickletHumidityV2
from tinkerforge.bricklet_motion_detector_v2 import BrickletMotionDetectorV2
from tinkerforge.bricklet_rgb_led_button import BrickletRGBLEDButton
from tinkerforge.bricklet_e_paper_296x128 import BrickletEPaper296x128
from tinkerforge.bricklet_lcd_128x64 import BrickletLCD128x64

import time

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

    def __getitem__(self, idx):
        return list(self)[idx]

    def __str__(self):
        return "\n".join([str(data) for data in self])

with open("wh.dat") as f:
    WEBHOOK = f.readline()

class Discord:
    # get the connection and make the request
    host = "discord.com"
    connection = http.client.HTTPSConnection(host)

    @staticmethod
    def send(message):
        global WEBHOOK
        # your webhook URL

        payload = json.dumps({"content": message})

        headers = {
            "Content-Type": "application/json"
        }

        Discord.connection.request("POST", WEBHOOK, body=payload, headers=headers)

        # get the response
        response = Discord.connection.getresponse()
        result = response.read()

        # return back to the calling function with the result
        return f"{response.status} {response.reason}\n{result.decode()}"

class Alarm:
    def __init__(self, conn):
        self.speaker = BrickletPiezoSpeakerV2("R7M", conn)
        self.led_button = BrickletRGBLEDButton("23Qx", conn)
        self._is_triggered = False

    def setup(self):
        self.led_button.set_color(0, 0, 0)
        self.led_button.register_callback(self.led_button.CALLBACK_BUTTON_STATE_CHANGED, self.button_callback)

    def trigger_alarm(self):
        self._is_triggered = True
        self.led_button.set_color(200, 30, 30)

        while self._is_triggered:
            self.speaker.set_alarm(800, 2000, 10, 1, 1, 1000)
            time.sleep(1)

    def button_callback(self, state):
        if (state == self.led_button.BUTTON_STATE_PRESSED):
            self.led_button.set_color(0, 0, 0)
            self._is_triggered = False

IP = "172.20.10.242"
PORT = 4223

# delay between notification when a critical measurement is taken
NOTIFICATION_DELAY_SECONDS = 60 * 5

SENSOR_DATA = SensorData()

def temperature_callback(temperature):
    SENSOR_DATA.temperature.set_current(temperature / 100)

def ambient_light_callback(illuminance):
    SENSOR_DATA.illuminance.set_current(illuminance / 100)

def moisture_callback(moisture):
    SENSOR_DATA.moisture.set_current(moisture / 100)

def start_motion_detection():
    print("start motion detected")

def end_motion_detection():
    print("stop motion detected")

class LCD_Display:
    UID = "24Rh"

    def __init__(self, conn):
        self.lcd = BrickletLCD128x64(LCD_Display.UID, conn)
        self.current_tab = 1

        # data for the current tab
        self.graph_data = []
        self.graph_unit = []

    def setup(self):
        self.lcd.register_callback(self.lcd.CALLBACK_GUI_TAB_SELECTED, self.select_tab)
        self.lcd.set_gui_tab_selected_callback_configuration(100, False)

    def select_tab(self, index):
        if self.current_tab != index:
            self.current_tab = index
            self.graph_data = []

    def tick(self, sensor_data):
        datum = sensor_data[self.current_tab]
        self.graph_data.append(datum.get_current())
        self.graph_unit = datum.unit

    def render(self):
        self.lcd.clear_display()
        self.lcd.remove_all_gui()

        self.lcd.set_gui_tab_configuration(self.lcd.CHANGE_TAB_ON_CLICK_AND_SWIPE, False)

        self.lcd.set_gui_tab_text(0, "Temp.")
        self.lcd.set_gui_tab_text(1, "Lumi.")
        self.lcd.set_gui_tab_text(2, "Moist")

        self.lcd.set_gui_tab_selected(self.current_tab)

        if self.graph_data:
            # draw graph
            data_begin = 0 if len(self.graph_data) < 60 else len(self.graph_data) - 60

            data = self.graph_data[data_begin:]

            data_min = min(data)
            data_max = max(data)
            def normalize(data):
                return [int(((x - data_min) / ((data_max - data_min) or 1)) * 240) for x in data]

            self.lcd.set_gui_graph_configuration(0, self.lcd.GRAPH_TYPE_LINE, 50, 0, 60, 52, "t", self.graph_unit)
            self.lcd.set_gui_graph_data(0, normalize(data))

            self.lcd.draw_text(
                6, 0,
                self.lcd.FONT_6X8,
                self.lcd.COLOR_BLACK,
                f"{round(data_max, 2)}")
            self.lcd.draw_text(
                6, 40,
                self.lcd.FONT_6X8,
                self.lcd.COLOR_BLACK,
                f"{round(data_min, 2)}")

if __name__ == "__main__":
    conn = IPConnection()

    # actors
    speaker = BrickletPiezoSpeakerV2("R7M", conn)
    paper_display = BrickletEPaper296x128("XGL", conn)
    lcd_display = LCD_Display(conn)

    # sensors
    ambient_light = BrickletAmbientLightV3("Pdw", conn)
    temperature = BrickletPTCV2("Wcg", conn)
    moisture_sensor = BrickletHumidityV2("ViW", conn)
    motion_detection = BrickletMotionDetectorV2("ML4", conn)
    alarm = Alarm(conn);

    conn.connect(IP, PORT)

    # register callbacks
    temperature.register_callback(temperature.CALLBACK_TEMPERATURE, temperature_callback)
    temperature.set_temperature_callback_configuration(1000, False, "x", 0, 0)

    ambient_light.register_callback(ambient_light.CALLBACK_ILLUMINANCE, ambient_light_callback)
    ambient_light.set_illuminance_callback_configuration(1000, False, "x", 0, 0)

    moisture_sensor.register_callback(moisture_sensor.CALLBACK_HUMIDITY, moisture_callback)
    moisture_sensor.set_humidity_callback_configuration(1000, False, "x", 0, 0)

    motion_detection.register_callback(motion_detection.CALLBACK_MOTION_DETECTED, start_motion_detection)
    motion_detection.register_callback(motion_detection.CALLBACK_DETECTION_CYCLE_ENDED, end_motion_detection)

    lcd_display.setup()
    # alarm.trigger_alarm()

    count = 0

    try:
        while True:
            pass
            # clear screen
            if os.name == "nt":
                os.system("cls")
            else:
                os.system("clear")

            now = datetime.now()
            print(lcd_display.current_tab)

            print(SENSOR_DATA)

            lcd_display.tick(SENSOR_DATA)
            lcd_display.render()

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
                    Discord.send(f"illuminance is critical: {SENSOR_DATA.illuminance.get_current()}{SENSOR_DATA.illuminance.unit}")
                    data.last_notified = now

            time.sleep(1)

    except KeyboardInterrupt:
        # the user ended the program so we absorb the exception
        pass
    finally:
        # gracefully close the connection
        conn.disconnect()
        print("\rconnection closed")

        Discord.send(f"""
            Data before disconnect:
                {str(SENSOR_DATA)}
            """)
