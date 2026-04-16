from __future__ import annotations

import struct
from dataclasses import dataclass

PACKET_SIZE = 48


@dataclass(slots=True)
class UDPPacket:
    timestamp: int
    device_id: int
    ciphertext: bytes
    tag: bytes
    iv: bytes

    @classmethod
    def from_bytes(cls, data: bytes) -> "UDPPacket":
        if len(data) != PACKET_SIZE:
            raise ValueError(f"packet must be {PACKET_SIZE} bytes")
        timestamp, device_id = struct.unpack(">II", data[:8])
        return cls(
            timestamp=timestamp,
            device_id=device_id,
            ciphertext=data[8:24],
            tag=data[24:36],
            iv=data[36:48],
        )
