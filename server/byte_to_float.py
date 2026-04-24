from __future__ import annotations

MAX_ENCODED = 0x07CE
PADDING_VALUE = 0xFFFF


def decode_temperature(encoded: int) -> float | None:
    if encoded == PADDING_VALUE:
        return None
    if not 0 <= encoded <= MAX_ENCODED:
        raise ValueError(f"invalid temperature encoding: 0x{encoded:04X}")
    return round((encoded / 10) - 99.9, 1)
