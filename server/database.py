from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class StoredMeasurement:
    device_id: int
    timestamp: int
    value: float


@dataclass(slots=True)
class DeviceRecord:
    device_id: int
    master_key_hex: str
    note: str
    created_at: str


@dataclass(slots=True)
class MeasurementRecord:
    device_id: int
    note: str
    timestamp: int
    value: float

    @property
    def datetime_text(self) -> str:
        return datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S")


class ServerDatabase:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    id INTEGER PRIMARY KEY,
                    master_key_hex TEXT NOT NULL,
                    note TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    timestamp INTEGER NOT NULL,
                    value REAL NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE,
                    UNIQUE(device_id, timestamp)
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_measurements_device_time ON measurements(device_id, timestamp)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_measurements_value ON measurements(value)"
            )

    def get_master_key(self, device_id: int) -> bytes | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT master_key_hex FROM devices WHERE id = ?",
                (device_id,),
            ).fetchone()
        if row is None:
            return None
        return bytes.fromhex(row["master_key_hex"])

    def list_devices(self) -> list[DeviceRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, master_key_hex, note, created_at FROM devices ORDER BY id ASC"
            ).fetchall()
        return [
            DeviceRecord(
                device_id=row["id"],
                master_key_hex=row["master_key_hex"],
                note=row["note"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def create_device(self, note: str = "") -> DeviceRecord:
        master_key_hex = os.urandom(16).hex().upper()
        with self._connect() as connection:
            row = connection.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM devices").fetchone()
            device_id = int(row["next_id"])
            connection.execute(
                "INSERT INTO devices (id, master_key_hex, note) VALUES (?, ?, ?)",
                (device_id, master_key_hex, note),
            )
            created = connection.execute(
                "SELECT created_at FROM devices WHERE id = ?",
                (device_id,),
            ).fetchone()
        return DeviceRecord(
            device_id=device_id,
            master_key_hex=master_key_hex,
            note=note,
            created_at=created["created_at"],
        )

    def update_device_note(self, device_id: int, note: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE devices SET note = ? WHERE id = ?",
                (note, device_id),
            )

    def delete_device(self, device_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM devices WHERE id = ?",
                (device_id,),
            )

    def append_measurements(self, measurements: list[StoredMeasurement]) -> int:
        if not measurements:
            return 0

        with self._connect() as connection:
            cursor = connection.executemany(
                """
                INSERT OR IGNORE INTO measurements (device_id, timestamp, value)
                VALUES (?, ?, ?)
                """,
                [(item.device_id, item.timestamp, item.value) for item in measurements],
            )
            return cursor.rowcount if cursor.rowcount != -1 else 0

    def query_measurements(
        self,
        device_id: int | None = None,
        start_timestamp: int | None = None,
        end_timestamp: int | None = None,
        sort_field: str = "timestamp",
        sort_desc: bool = False,
    ) -> list[MeasurementRecord]:
        allowed_fields = {"timestamp", "value"}
        order_field = sort_field if sort_field in allowed_fields else "timestamp"
        order_direction = "DESC" if sort_desc else "ASC"

        conditions: list[str] = []
        params: list[object] = []
        if device_id is not None:
            conditions.append("m.device_id = ?")
            params.append(device_id)
        if start_timestamp is not None:
            conditions.append("m.timestamp >= ?")
            params.append(start_timestamp)
        if end_timestamp is not None:
            conditions.append("m.timestamp <= ?")
            params.append(end_timestamp)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT m.device_id, d.note, m.timestamp, m.value
            FROM measurements AS m
            LEFT JOIN devices AS d ON d.id = m.device_id
            {where_clause}
            ORDER BY m.{order_field} {order_direction}, m.device_id ASC, m.timestamp ASC
        """

        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [
            MeasurementRecord(
                device_id=row["device_id"],
                note=row["note"] or "",
                timestamp=row["timestamp"],
                value=row["value"],
            )
            for row in rows
        ]

    def clear_measurements(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM measurements")

    def execute_sql(self, sql: str) -> tuple[list[str], list[tuple[object, ...]], int]:
        with self._connect() as connection:
            cursor = connection.execute(sql)
            if cursor.description is not None:
                columns = [item[0] for item in cursor.description]
                rows = [tuple(row) for row in cursor.fetchall()]
                return columns, rows, len(rows)
            affected = cursor.rowcount if cursor.rowcount != -1 else 0
            return [], [], affected
