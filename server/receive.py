from __future__ import annotations

import logging
import socket
import struct
import time
from collections.abc import Callable

from cryptography.exceptions import InvalidTag

from server.byte_to_float import decode_temperature
from server.cache import ReplayCache
from server.database import ServerDatabase, StoredMeasurement
from server.hmac_sm3 import derive_hour_key
from server.sm4_gcm import decrypt
from server.udp import UDPPacket

LOGGER = logging.getLogger(__name__)
MAX_TEMPERATURE_DELTA = 0.2


class UDPServer:
    def __init__(
        self,
        host: str,
        port: int,
        database: ServerDatabase,
        max_time_skew: int = 30,
        replay_ttl: int | None = None,
        event_callback: Callable[[str, str], None] | None = None,
    ) -> None:
        self.database = database
        self.max_time_skew = max_time_skew
        self.replay_ttl = replay_ttl if replay_ttl is not None else max(10, max_time_skew * 2)
        self.cache = ReplayCache(ttl_seconds=self.replay_ttl)
        self._event_callback = event_callback
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.bind((host, port))
        self._running = True
        self._emit("info", "listening on %s:%s", host, port)

    def _emit(self, level: str, message: str, *args: object) -> None:
        log_method = getattr(LOGGER, level, LOGGER.info)
        log_method(message, *args)
        if self._event_callback is not None:
            formatted = message % args if args else message
            self._event_callback(level, formatted)

    def serve_forever(self) -> None:
        while self._running:
            try:
                data, address = self._socket.recvfrom(4096)
            except OSError:
                break

            try:
                self.handle_datagram(data)
            except Exception as exc:  # pragma: no cover - defensive boundary
                self._emit("warning", "failed to handle packet from %s: %s", address, exc)

    def close(self) -> None:
        self._running = False
        try:
            self._socket.close()
        except OSError:
            pass

    def handle_datagram(self, data: bytes) -> None:
        packet = UDPPacket.from_bytes(data)
        self._validate_timestamp(packet.timestamp)

        if self.cache.contains(packet.device_id, packet.timestamp):
            raise ValueError("replay packet detected")

        master_key = self.database.get_master_key(packet.device_id)
        if master_key is None:
            raise ValueError(f"unknown device id {packet.device_id}")

        aad = struct.pack(">II", packet.device_id, packet.timestamp)
        hour_key = derive_hour_key(master_key, packet.timestamp // 3600)
        try:
            plaintext = decrypt(hour_key, packet.iv, aad, packet.ciphertext, packet.tag)
        except InvalidTag as exc:
            raise ValueError("invalid GCM tag") from exc

        measurements = self._parse_measurements(packet.device_id, packet.timestamp, plaintext)
        self._warn_large_temperature_delta(packet.device_id, measurements)
        stored_count = self.database.append_measurements(measurements)
        self.cache.add(packet.device_id, packet.timestamp)

        if stored_count > 0:
            self._emit(
                "info",
                "stored %s measurements from device=%s timestamp=%s",
                stored_count,
                packet.device_id,
                packet.timestamp,
            )
        else:
            self._emit("warning", "received packet with no storable data from device=%s", packet.device_id)

    def _validate_timestamp(self, timestamp: int) -> None:
        current_time = int(time.time())
        if abs(current_time - timestamp) > self.max_time_skew:
            raise ValueError(f"timestamp outside {self.max_time_skew}-second tolerance")
        if timestamp % 8 != 0:
            raise ValueError("timestamp must satisfy timestamp % 8 == 0")

    def _parse_measurements(self, device_id: int, timestamp: int, plaintext: bytes) -> list[StoredMeasurement]:
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

    def _warn_large_temperature_delta(self, device_id: int, measurements: list[StoredMeasurement]) -> None:
        if not measurements:
            return

        first_timestamp = measurements[0].timestamp
        known_values: dict[int, float] = {}

        previous_value = self.database.get_measurement_value(device_id, first_timestamp - 1)
        if previous_value is not None:
            known_values[first_timestamp - 1] = previous_value

        for measurement in measurements:
            previous_timestamp = measurement.timestamp - 1
            previous_measurement_value = known_values.get(previous_timestamp)
            if previous_measurement_value is not None:
                delta = abs(measurement.value - previous_measurement_value)
                if delta > MAX_TEMPERATURE_DELTA:
                    self._emit(
                        "warning",
                        "temperature jump detected for device=%s between timestamp=%s and timestamp=%s: %.1f -> %.1f",
                        device_id,
                        previous_timestamp,
                        measurement.timestamp,
                        previous_measurement_value,
                        measurement.value,
                    )

            known_values[measurement.timestamp] = measurement.value
