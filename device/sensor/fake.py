from __future__ import annotations

import os

MIN_TEMP = -20.0
MAX_TEMP = 50.0


def _random_fraction() -> float:
    raw = int.from_bytes(os.urandom(2), "big")
    return raw / 65535


def generate_fake_temperature() -> float:
    value = MIN_TEMP + (MAX_TEMP - MIN_TEMP) * _random_fraction()
    return round(value, 1)
