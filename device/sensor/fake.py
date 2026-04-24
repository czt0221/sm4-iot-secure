from __future__ import annotations

import math

MIN_TEMP = -20.0
MAX_TEMP = 42.0
SECONDS_PER_DAY = 24 * 60 * 60
SECONDS_PER_YEAR = 365 * SECONDS_PER_DAY

ANNUAL_BASELINE = 13.0
ANNUAL_AMPLITUDE = 16.0
DAILY_AMPLITUDE = 5.5
SPECIAL_AMPLITUDE = 1.2
MICRO_AMPLITUDE = 0.24


def _device_phase(device_id: int, factor: int, cycle: int) -> float:
    return ((device_id * factor) % cycle) / cycle * 2.0 * math.pi


def _clamp(value: float, lower: float, upper: float) -> float:
    return min(max(value, lower), upper)


def _triangle_wave(position: float) -> float:
    wrapped = position % 1.0
    return 1.0 - 4.0 * abs(wrapped - 0.5)


def generate_fake_temperature(device_id: int, timestamp: int) -> float:
    annual_phase = (timestamp % SECONDS_PER_YEAR) / SECONDS_PER_YEAR * 2.0 * math.pi
    daily_phase = (timestamp % SECONDS_PER_DAY) / SECONDS_PER_DAY * 2.0 * math.pi

    # January is the coldest period in North China, so shift the yearly peak into midsummer.
    annual = ANNUAL_BASELINE + ANNUAL_AMPLITUDE * math.sin(annual_phase - math.pi / 2.0)

    # Peak temperature occurs around 14:00.
    daily = DAILY_AMPLITUDE * math.sin(daily_phase - math.pi / 3.0)

    # Each device keeps a stable offset and phase, so different devices are similar but not identical.
    device_offset = ((device_id * 17) % 31) / 10.0 - 1.5

    special = (
        0.7 * math.sin(timestamp / (3 * SECONDS_PER_DAY) * 2.0 * math.pi + _device_phase(device_id, 37, 360))
        + 0.5 * math.sin(timestamp / (7 * SECONDS_PER_DAY) * 2.0 * math.pi + _device_phase(device_id, 91, 360))
    )

    # Add a short-period triangular component so rounded values still vary in a 10-second window.
    triangle = MICRO_AMPLITUDE * _triangle_wave(timestamp / 20.0 + device_id * 0.137)
    ripple = 0.06 * math.sin(timestamp / 16.0 * 2.0 * math.pi + _device_phase(device_id, 71, 360))
    micro = triangle + ripple

    value = annual + daily + device_offset + SPECIAL_AMPLITUDE * special + micro
    value = _clamp(value, MIN_TEMP, MAX_TEMP)
    return round(value, 1)
