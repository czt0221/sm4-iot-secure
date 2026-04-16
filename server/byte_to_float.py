from __future__ import annotations

PADDING_VALUE = 0xFFFF


def decode_temperature(encoded: int) -> float | None:
    if encoded == PADDING_VALUE:
        return None
    return round((encoded / 10) - 99.9, 1)
