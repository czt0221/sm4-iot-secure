from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class StoredMeasurement:
    device_id: int
    timestamp: int
    value: float


class ServerDatabase:
    def __init__(self, server_dir: Path) -> None:
        self.server_dir = server_dir
        self.master_key_file = server_dir / "id_masterkey"
        self.data_file = server_dir / "data"
        self._master_keys = self._load_master_keys()

    def _load_master_keys(self) -> dict[int, bytes]:
        mapping: dict[int, bytes] = {}
        if not self.master_key_file.exists():
            return mapping
        for raw_line in self.master_key_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            device_id_text, master_key_hex = [item.strip() for item in line.split(",", maxsplit=1)]
            mapping[int(device_id_text, 0)] = bytes.fromhex(master_key_hex)
        return mapping

    def get_master_key(self, device_id: int) -> bytes | None:
        return self._master_keys.get(device_id)

    def append_measurements(self, measurements: list[StoredMeasurement]) -> None:
        if not measurements:
            return
        with self.data_file.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            for measurement in measurements:
                writer.writerow((measurement.device_id, measurement.timestamp, measurement.value))
