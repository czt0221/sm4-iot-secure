from __future__ import annotations

import time


class ReplayCache:
    def __init__(self, ttl_seconds: int = 10) -> None:
        self.ttl_seconds = ttl_seconds
        self._entries: dict[tuple[int, int], float] = {}

    def _purge(self) -> None:
        now = time.monotonic()
        expired = [key for key, deadline in self._entries.items() if deadline <= now]
        for key in expired:
            self._entries.pop(key, None)

    def contains(self, device_id: int, timestamp: int) -> bool:
        self._purge()
        return (device_id, timestamp) in self._entries

    def add(self, device_id: int, timestamp: int) -> None:
        self._purge()
        self._entries[(device_id, timestamp)] = time.monotonic() + self.ttl_seconds

    def clear(self) -> None:
        self._entries.clear()
