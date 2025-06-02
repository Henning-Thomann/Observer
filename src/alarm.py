from datetime import datetime, timedelta
from tinkerforge.bricklet_rgb_led_button import BrickletRGBLEDButton
from tinkerforge.bricklet_piezo_speaker_v2 import BrickletPiezoSpeakerV2

class Alarm:
    def __init__(self, conn, count_down, trigger_timout_duration):
        self.speaker = BrickletPiezoSpeakerV2("R7M", conn)
        self.led_button = BrickletRGBLEDButton("23Qx", conn)
        self._is_triggered = False
        self._count_down = count_down

        self._trigger_timout_duration = trigger_timout_duration
        self._trigger_timeout_start = datetime.now() - timedelta(seconds=trigger_timout_duration)

    def setup(self):
        self.led_button.set_color(0, 0, 0)
        self.led_button.register_callback(self.led_button.CALLBACK_BUTTON_STATE_CHANGED, self.button_callback)

    def update(self):
        if self._is_triggered:
            self.speaker.set_alarm(800, 2000, 10, 1, 1, 200)

    def trigger_alarm(self):
        if not self._is_triggered:
            self._is_triggered = True
            self.led_button.set_color(255, 30, 30)

    def can_trigger(self):
        print("Timeout time (sec): " + str((datetime.now() - self._trigger_timeout_start).total_seconds()))
        return (datetime.now() - self._trigger_timeout_start).total_seconds() >= self._trigger_timout_duration
            
    def button_callback(self, state):
        if (state == self.led_button.BUTTON_STATE_PRESSED):
            print("Button pressed - resetting alarm and enabling motion detection")

            self._trigger_timeout_start = datetime.now();
            self.led_button.set_color(0, 0, 0)
            self._is_triggered = False

            # Button-Press soll das System wieder in den normalen Zustand versetzen
            self._count_down.enable_motion_detection()
    
    def reset_alarm(self):
        self._is_triggered = False
        self.led_button.set_color(0,0,0)
        self.speaker.set_alarm(800,2000,10,1,10,0)
