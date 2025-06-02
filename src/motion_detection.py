from tinkerforge.bricklet_motion_detector_v2 import BrickletMotionDetectorV2

class MotionDetection:
    def __init__(self, conn, count_down, alarm):
        self._motion_detection = BrickletMotionDetectorV2("ML4", conn)
        self._count_down = count_down
        self._alarm = alarm

    def setup(self):
        self._motion_detection.register_callback(self._motion_detection.CALLBACK_MOTION_DETECTED, self.start_motion_detection)

    def start_motion_detection(self):
        self._count_down.start_count_down(4, self._alarm.trigger_alarm)

        if self._alarm.can_trigger():
            self._count_down.start_count_down(10, self._alarm.trigger_alarm)
