from __future__ import annotations

import struct

MAX_ENCODED = 0x07CF
PADDING_VALUE = 0xFFFF
MIN_TEMP = -99.9
MAX_TEMP = 99.9


def encode_temperature(value: float) -> int:
    if value < MIN_TEMP or value > MAX_TEMP:
        raise ValueError("temperature out of supported range")
    encoded = int(round((value + 99.9) * 10))
    if not 0 <= encoded <= MAX_ENCODED:
        raise ValueError("encoded temperature out of range")
    return encoded


def encode_temperature_bytes(value: float) -> bytes:
    return struct.pack(">H", encode_temperature(value))


def padding_bytes() -> bytes:
    return struct.pack(">H", PADDING_VALUE)
