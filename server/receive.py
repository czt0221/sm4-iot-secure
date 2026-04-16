from __future__ import annotations

import logging
import socket
import struct
import time
from pathlib import Path

from cryptography.exceptions import InvalidTag

from server.byte_to_float import decode_temperature
from server.cache import ReplayCache
from server.database import ServerDatabase, StoredMeasurement
from server.hmac_sm3 import derive_hour_key
from server.sm4_gcm import decrypt
from server.udp import UDPPacket

LOGGER = logging.getLogger(__name__)


class UDPServer:
    def __init__(
        self,
        host: str,
        port: int,
        server_dir: Path,
        max_time_skew: int = 30,
        replay_ttl: int | None = None,
    ) -> None:
        self.database = ServerDatabase(server_dir)
        self.max_time_skew = max_time_skew
        self.replay_ttl = replay_ttl if replay_ttl is not None else max(10, max_time_skew * 2)
        self.cache = ReplayCache(ttl_seconds=self.replay_ttl)
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((host, port))
        LOGGER.info("listening on %s:%s", host, port)

    def serve_forever(self) -> None:
        while True:
            data, address = self._socket.recvfrom(4096)
            try:
                self.handle_datagram(data)
            except Exception as exc:  # pragma: no cover - defensive boundary
                LOGGER.warning("failed to handle packet from %s: %s", address, exc)

    def handle_datagram(self, data: bytes) -> None:
        packet = UDPPacket.from_bytes(data)
        self._validate_timestamp(packet.timestamp)

        master_key = self.database.get_master_key(packet.device_id)
        if master_key is None:
            raise ValueError(f"unknown device id {packet.device_id}")

        if self.cache.contains(packet.device_id, packet.timestamp):
            raise ValueError("replay packet detected")

        aad = struct.pack(">II", packet.device_id, packet.timestamp)
        hour_key = derive_hour_key(master_key, packet.timestamp // 3600)
        try:
            plaintext = decrypt(hour_key, packet.iv, aad, packet.ciphertext, packet.tag)
        except InvalidTag as exc:
            raise ValueError("invalid GCM tag") from exc

        measurements = self._parse_measurements(packet.device_id, packet.timestamp, plaintext)
        self.database.append_measurements(measurements)
        self.cache.add(packet.device_id, packet.timestamp)

        if measurements:
            LOGGER.info(
                "stored %s measurements from device=%s timestamp=%s",
                len(measurements),
                packet.device_id,
                packet.timestamp,
            )
        else:
            LOGGER.warning("received packet with only padding from device=%s", packet.device_id)

    def _validate_timestamp(self, timestamp: int) -> None:
        current_time = int(time.time())
        if abs(current_time - timestamp) > self.max_time_skew:
            raise ValueError(f"timestamp outside {self.max_time_skew}-second tolerance")
        if timestamp % 8 != 0:
            raise ValueError("timestamp must satisfy timestamp % 8 == 0")

    def _parse_measurements(self, device_id: int, timestamp: int, plaintext: bytes) -> list[StoredMeasurement]:
        if len(plaintext) != 16:
            raise ValueError("plaintext must be 16 bytes")

        measurements: list[StoredMeasurement] = []
        encoded_values = struct.unpack(">8H", plaintext)
        for offset, encoded in enumerate(encoded_values):
            value = decode_temperature(encoded)
            if value is None:
                continue
            measurements.append(
                StoredMeasurement(
                    device_id=device_id,
                    timestamp=timestamp - offset,
                    value=value,
                )
            )
        measurements.sort(key=lambda item: item.timestamp)
        return measurements
