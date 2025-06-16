from tinkerforge.bricklet_segment_display_4x7_v2 import BrickletSegmentDisplay4x7V2

class CountDown:
    def __init__(self, conn):
        self.segment_display = BrickletSegmentDisplay4x7V2("Tre", conn)
        self.segment_display.register_callback(self.segment_display.CALLBACK_COUNTER_FINISHED, self._count_down_ended)
        self.allow_cool_down = True

    def start_count_down(self, count_down, callback):
        if self.allow_cool_down:
            self.allow_cool_down = False
            self.segment_display.start_counter(count_down, 0, -1, 1000)
            self._callback = callback

    def _count_down_ended(self):
        if self._callback:
            self._callback()
            self._callback = None

    def reset_count_down(self):
        self.allow_cool_down = True
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
