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

    def to_bytes(self) -> bytes:
        if len(self.ciphertext) != 16:
            raise ValueError("ciphertext must be 16 bytes")
        if len(self.tag) != 12:
            raise ValueError("tag must be 12 bytes")
        if len(self.iv) != 12:
            raise ValueError("iv must be 12 bytes")
        return (
            struct.pack(">II", self.timestamp, self.device_id)
            + self.ciphertext
            + self.tag
            + self.iv
        )
