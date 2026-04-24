from __future__ import annotations

from dataclasses import dataclass

from device.sensor.fake import generate_fake_temperature
from device.sensor.float_to_byte import PADDING_VALUE, encode_temperature


@dataclass(slots=True)
class TemperatureSensor:
    device_id: int
    padding_value: int = PADDING_VALUE

    def read(self, timestamp: int) -> float:
        return generate_fake_temperature(self.device_id, timestamp)

    def read_encoded(self, timestamp: int) -> int:
        return encode_temperature(self.read(timestamp))
