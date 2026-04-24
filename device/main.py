from __future__ import annotations

import argparse
import logging
from collections import deque
from pathlib import Path

from device.encryptor.encryptor import DeviceEncryptor
from device.network.network import DeviceNetworkClient
from device.network.time import DeviceClock
from device.sensor.sensor import TemperatureSensor

LOGGER = logging.getLogger(__name__)
BUFFER_SIZE = 8


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SM4 IoT secure device")
    parser.add_argument("--host", default="127.0.0.1", help="server host")
    parser.add_argument("--port", default=9999, type=int, help="server UDP port")
    parser.add_argument(
        "--sync-interval",
        default=60,
        type=int,
        help="seconds between gradual NTP synchronizations",
    )
    parser.add_argument(
        "--device-dir",
        default=Path(__file__).resolve().parent / "encryptor",
        type=Path,
        help="directory containing id and master_key files",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="logging level",
    )
    return parser


def run_device(host: str, port: int, sync_interval: int, device_dir: Path) -> None:
    clock = DeviceClock(sync_interval=sync_interval)
    encryptor = DeviceEncryptor(device_dir=device_dir)
    sensor = TemperatureSensor(device_id=encryptor.device_id)
    network = DeviceNetworkClient(host=host, port=port)
    buffer: deque[int] = deque(maxlen=BUFFER_SIZE)

    LOGGER.info("initializing device clock with NTP")
    clock.initialize()
    LOGGER.info("device id=%s initialized", encryptor.device_id)

    try:
        while True:
            timestamp = clock.wait_next_timestamp()
            sample = sensor.read_encoded(timestamp)
            buffer.append(sample)
            LOGGER.debug("sampled timestamp=%s encoded=%s", timestamp, sample)

            if clock.should_sync():
                clock.try_sync()

            if timestamp % BUFFER_SIZE != 0:
                continue

            actual_count = len(buffer)
            payload = list(reversed(buffer))
            while len(payload) < BUFFER_SIZE:
                payload.append(sensor.padding_value)

            packet = encryptor.encrypt_batch(timestamp=timestamp, values=payload)
            network.send_packet(packet)
            LOGGER.info(
                "sent packet timestamp=%s samples=%s padded=%s",
                timestamp,
                actual_count,
                BUFFER_SIZE - actual_count,
            )
    finally:
        network.close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    run_device(
        host=args.host,
        port=args.port,
        sync_interval=args.sync_interval,
        device_dir=args.device_dir,
    )


if __name__ == "__main__":
    main()
