from __future__ import annotations

from dataclasses import dataclass

from device.sensor.fake import generate_fake_temperature
from device.sensor.float_to_byte import PADDING_VALUE, encode_temperature


@dataclass(slots=True)
class TemperatureSensor:
    padding_value: int = PADDING_VALUE

    def read(self) -> float:
        return generate_fake_temperature()

    def read_encoded(self) -> int:
        return encode_temperature(self.read())
