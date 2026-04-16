from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from device.encryptor.hmac_sm3 import derive_hour_key
from device.encryptor.random import generate_iv
from device.encryptor.sm4_gcm import encrypt
from device.network.udp import UDPPacket


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def _load_device_id(path: Path) -> int:
    content = _read_text_file(path)
    return int(content, 0)


def _load_master_key(path: Path) -> bytes:
    content = _read_text_file(path).replace(" ", "")
    key = bytes.fromhex(content)
    if len(key) != 16:
        raise ValueError("master_key must be exactly 16 bytes in hex form")
    return key


@dataclass(slots=True)
class DeviceEncryptor:
    device_dir: Path
    device_id: int = 0
    master_key: bytes = b""
    _cached_hour_index: int | None = None
    _cached_hour_key: bytes | None = None

    def __post_init__(self) -> None:
        self.device_id = _load_device_id(self.device_dir / "id")
        self.master_key = _load_master_key(self.device_dir / "master_key")
        self._cached_hour_index = None
        self._cached_hour_key = None

    def _hour_key_for(self, timestamp: int) -> bytes:
        hour_index = timestamp // 3600
        if self._cached_hour_index != hour_index:
            self._cached_hour_key = derive_hour_key(self.master_key, hour_index)
            self._cached_hour_index = hour_index
        return self._cached_hour_key  # type: ignore[return-value]

    def encrypt_batch(self, timestamp: int, values: list[int]) -> UDPPacket:
        if len(values) != 8:
            raise ValueError("exactly 8 encoded values are required")
        plaintext = b"".join(struct.pack(">H", value) for value in values)
        aad = struct.pack(">II", self.device_id, timestamp)
        iv = generate_iv()
        ciphertext, tag = encrypt(self._hour_key_for(timestamp), iv, aad, plaintext)
        return UDPPacket(
            timestamp=timestamp,
            device_id=self.device_id,
            ciphertext=ciphertext,
            tag=tag,
            iv=iv,
        )
