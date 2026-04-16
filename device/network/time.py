from __future__ import annotations

import logging
import time
from collections.abc import Callable

from pyntp import NTPTime

LOGGER = logging.getLogger(__name__)


class DeviceClock:
    def __init__(
        self,
        sync_interval: int = 60,
        ntp_server_url: str = "pool.ntp.org",
        adjust_interval: int = 60,
        merge_time: int = 10,
        ntp_client: NTPTime | None = None,
        monotonic_func: Callable[[], float] | None = None,
        sleep_func: Callable[[float], None] | None = None,
    ) -> None:
        self.sync_interval = sync_interval
        self.ntp = ntp_client or NTPTime(
            ntp_server_url=ntp_server_url,
            adjust_interval=adjust_interval,
            merge_time=merge_time,
        )
        self._monotonic = monotonic_func or time.monotonic
        self._sleep = sleep_func or time.sleep
        self.local_time = 0.0
        self.clock_rate = 1.0
        self.offset_estimate = 0.0
        self.initialized = False
        self._consecutive_sync_failures = 0
        self._last_monotonic = 0.0
        self._next_sync_due = 0.0
        self._last_emitted_timestamp = 0

    def initialize(self) -> None:
        while not self.initialized:
            try:
                ref_time = self.ntp.now()
            except Exception as exc:  # pragma: no cover - network dependent
                LOGGER.warning("initial NTP sync failed: %s", exc)
                self._sleep(1)
                continue

            self.local_time = ref_time
            self.clock_rate = 1.0
            self.offset_estimate = 0.0
            self.initialized = True
            self._last_monotonic = self._monotonic()
            self._next_sync_due = self._last_monotonic + self.sync_interval
            self._last_emitted_timestamp = int(self.local_time)

    def _advance_local_time(self) -> None:
        now = self._monotonic()
        elapsed = max(0.0, now - self._last_monotonic)
        self.local_time += elapsed * self.clock_rate
        self._last_monotonic = now

    def wait_next_timestamp(self) -> int:
        if not self.initialized:
            raise RuntimeError("device clock is not initialized")

        while True:
            self._advance_local_time()
            current_timestamp = int(self.local_time)
            if current_timestamp > self._last_emitted_timestamp:
                if current_timestamp > self._last_emitted_timestamp + 1:
                    LOGGER.warning(
                        "device time advanced faster than sampling loop, smoothing emitted timestamp from %s to %s",
                        self._last_emitted_timestamp,
                        current_timestamp,
                    )
                self._last_emitted_timestamp += 1
                return self._last_emitted_timestamp

            next_boundary = self._last_emitted_timestamp + 1
            wait_seconds = (next_boundary - self.local_time) / max(self.clock_rate, 1e-6)
            self._sleep(max(0.001, min(0.2, wait_seconds)))

    def should_sync(self) -> bool:
        if not self.initialized:
            return False
        self._advance_local_time()
        return self._last_monotonic >= self._next_sync_due

    def try_sync(self) -> None:
        if not self.initialized:
            return
        self._advance_local_time()
        try:
            ref_time = self.ntp.now()
        except Exception as exc:  # pragma: no cover - network dependent
            self._consecutive_sync_failures += 1
            if self._consecutive_sync_failures >= 3:
                LOGGER.warning("NTP sync failed %s times: %s", self._consecutive_sync_failures, exc)
            self._next_sync_due = self._last_monotonic + self.sync_interval
            return

        self._consecutive_sync_failures = 0
        offset = ref_time - self.local_time
        self.offset_estimate = 0.2 * offset + 0.8 * self.offset_estimate
        adjusted_rate = 1.0 + (self.offset_estimate / self.sync_interval)
        self.clock_rate = max(0.9, min(1.1, adjusted_rate))
        self._next_sync_due = self._last_monotonic + self.sync_interval
