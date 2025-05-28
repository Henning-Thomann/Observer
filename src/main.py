 import os
from datetime import datetime

# discord-notification imports
import http.client
import json
import Discord
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
from tinkerforge.bricklet_segment_display_4x7_v2 import BrickletSegmentDisplay4x7V2
from tinkerforge.bricklet_nfc import BrickletNFC

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



ALARM = None
COUNT_DOWN = None
WAIT_FOR_MOTION = True

class Alarm:
    def __init__(self, conn):
        self.speaker = BrickletPiezoSpeakerV2("R7M", conn)
        self.led_button = BrickletRGBLEDButton("23Qx", conn)
        self._is_triggered = False

    def setup(self):
        self.led_button.set_color(0, 0, 0)
        self.led_button.register_callback(self.led_button.CALLBACK_BUTTON_STATE_CHANGED, self.button_callback)

    def update(self):
        if self._is_triggered:
            self.speaker.set_alarm(800, 2000, 10, 1, 1, 1000)

    def trigger_alarm(self):
        if not self._is_triggered:
            self._is_triggered = True
            self.led_button.set_color(200, 30, 30)

    def button_callback(self, state):
        if (state == self.led_button.BUTTON_STATE_PRESSED):
            print("Button pressed - resetting alarm and enabling motion detection")
            self.led_button.set_color(0, 0, 0)
            self._is_triggered = False
            # Button-Press soll das System wieder in den normalen Zustand versetzen
            COUNT_DOWN.enable_motion_detection()

    def reset_alarm(self):
        self._is_triggered = False
        self.led_button.set_color(0,0,0)
        self.speaker.set_alarm(800,2000,10,1,10,0)

class CountDown:
    def __init__(self, conn):
        self.segment_display = BrickletSegmentDisplay4x7V2("Tre", conn)
        self.segment_display.register_callback(self.segment_display.CALLBACK_COUNTER_FINISHED, self._count_down_ended)
        self.allow_cool_down = True
        self._callback = None

    def start_count_down(self, count_down, callback):
        if self.allow_cool_down:
            self.allow_cool_down = True
            self.segment_display.start_counter(count_down, 0, -1, 1000)
            self._callback = callback

    def _count_down_ended(self):
        if self._callback:
            self._callback()
            self._callback = None

    def stop_count_down(self):
        print("Stopping countdown")
        self.segment_display.set_numeric_value([0,0,0,0])
        self._callback = None

    def disable_motion_detection(self):
        """Deaktiviert Motion Detection (nach NFC-Scan)"""
        self.motion_detection_enabled = False
        print("Motion detection disabled")

    def enable_motion_detection(self):
        """Aktiviert Motion Detection wieder (nach Button-Press)"""
        self.motion_detection_enabled = True
        print("Motion detection enabled")

IP = "172.20.10.242"
PORT = 4223

# delay between notification when a critical measurement is taken
NOTIFICATION_DELAY_SECONDS = 60 * 5

SENSOR_DATA = SensorData()
VALID_NFC_ID_SUFFIX = 0x90

def temperature_callback(temperature):
    SENSOR_DATA.temperature.set_current(temperature / 100)

def ambient_light_callback(illuminance):
    SENSOR_DATA.illuminance.set_current(illuminance / 100)

def moisture_callback(moisture):
    SENSOR_DATA.moisture.set_current(moisture / 100)

def start_motion_detection():
    COUNT_DOWN.start_count_down(4, ALARM.trigger_alarm)

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

def cb_reader_state_changed(state, idle, nfc):
    global COUNT_DOWN, ALARM
    if state == nfc.READER_STATE_REQUEST_TAG_ID_READY:
        ret = nfc.reader_get_tag_id()
        tag_id = list(ret.tag_id)

        print("Found tag of type " +
              str(ret.tag_type) +
              " with ID [" +
              " ".join(map(str, map('0x{:02X}'.format, ret.tag_id))) +
              "]")

        if tag_id[-1] == VALID_NFC_ID_SUFFIX:
            print("Valid NFC card scanned - Stopping countdown and disabling motion detection")
            COUNT_DOWN.stop_count_down()
            ALARM.reset_alarm()
            COUNT_DOWN.disable_motion_detection()  # Verwende die neue Methode!
        else:
            print("Scanned card doesn't match Whitelist. Try another card")

    if idle:
        nfc.reader_request_tag_id()

if __name__ == "__main__":
    conn = IPConnection()

    # actors
    speaker = BrickletPiezoSpeakerV2("R7M", conn)
    paper_display = BrickletEPaper296x128("XGL", conn)
    lcd_display = LCD_Display(conn)

    # sensors
    ALARM = Alarm(conn)
    COUNT_DOWN = CountDown(conn)

    ambient_light = BrickletAmbientLightV3("Pdw", conn)
    temperature = BrickletPTCV2("Wcg", conn)
    moisture_sensor = BrickletHumidityV2("ViW", conn)
    nfc = BrickletNFC("22ND", conn)
  
    motion_detection = BrickletMotionDetectorV2("ML4", conn)

    conn.connect(IP, PORT)

    # register callbacks
    temperature.register_callback(temperature.CALLBACK_TEMPERATURE, temperature_callback)
    temperature.set_temperature_callback_configuration(1000, False, "x", 0, 0)

    ambient_light.register_callback(ambient_light.CALLBACK_ILLUMINANCE, ambient_light_callback)
    ambient_light.set_illuminance_callback_configuration(1000, False, "x", 0, 0)

    moisture_sensor.register_callback(moisture_sensor.CALLBACK_HUMIDITY, moisture_callback)
    moisture_sensor.set_humidity_callback_configuration(1000, False, "x", 0, 0)

    nfc.register_callback(nfc.CALLBACK_READER_STATE_CHANGED,
                          lambda x, y: cb_reader_state_changed(x, y, nfc))
    nfc.set_mode(nfc.MODE_READER)
    
    
    motion_detection.register_callback(motion_detection.CALLBACK_MOTION_DETECTED, start_motion_detection)
    motion_detection.register_callback(motion_detection.CALLBACK_DETECTION_CYCLE_ENDED, end_motion_detection)

    lcd_display.setup()
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
            print(lcd_display.current_tab)

            print(SENSOR_DATA)

            lcd_display.tick(SENSOR_DATA)
            #lcd_display.render()

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

            ALARM.update()

            time.sleep(100)

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
