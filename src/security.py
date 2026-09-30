from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class LoginRateLimiter:
    def __init__(self, attempt_limit: int, window_seconds: int):
        self.attempt_limit = attempt_limit
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _active_attempts(self, key: str, now: float) -> deque[float]:
        attempts = self._attempts[key]
        cutoff = now - self.window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        return attempts

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            return len(self._active_attempts(key, time.monotonic())) >= self.attempt_limit

    def record_failure(self, key: str) -> None:
        with self._lock:
            self._active_attempts(key, time.monotonic()).append(time.monotonic())

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)
