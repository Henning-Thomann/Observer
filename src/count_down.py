from tinkerforge.bricklet_segment_display_4x7_v2 import BrickletSegmentDisplay4x7V2

class CountDown:
    def __init__(self, conn):
        self.segment_display = BrickletSegmentDisplay4x7V2("Tre", conn)
        self.segment_display.register_callback(self.segment_display.CALLBACK_COUNTER_FINISHED, self._count_down_ended)
        self.allow_cool_down = True

    def start_count_down(self, count_down, callback):
        if self.allow_cool_down:
            self.allow_cool_down = True
            self.segment_display.start_counter(count_down, 0, -1, 1000)
            self._callback = callback

    def _count_down_ended(self):
        self._callback()
