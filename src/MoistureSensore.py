from tinkerforge.ip_connection import IPConnection
from tinkerforge.bricklet_humidity_v2 import BrickletHumidityV2

class MoistureSensor():
    def __init__(self, conn: IPConnection, sensore_id: str, threshold: int):
        self.moisture_sensore = BrickletHumidityV2(sensore_id, conn)
        self.moisture_value = 0
        self._threshold = threshold

        self.moisture_sensore.register_callback(self.moisture_sensore.CALLBACK_HUMIDITY, self.moisture_callback)
        self.moisture_sensore.set_humidity_callback_configuration(1000, False, "x", 0, 0)

    def moisture_callback(self, moisture_value):
        self.moisture_value = moisture_value

    def should_trigger_alarm(self):
        return self.moisture_value >= self._threshold
    