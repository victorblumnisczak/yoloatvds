import threading
import time


class RateLimiter:
    def __init__(self, min_interval_seconds: int):
        self._min = min_interval_seconds
        self._last: dict[str, float] = {}
        self._lock = threading.Lock()

    def can_request(self, key: str) -> bool:
        with self._lock:
            last = self._last.get(key, 0.0)
            return (time.time() - last) >= self._min

    def record_request(self, key: str) -> None:
        with self._lock:
            self._last[key] = time.time()

    def time_until_allowed(self, key: str) -> float:
        with self._lock:
            last = self._last.get(key, 0.0)
            elapsed = time.time() - last
            return max(0.0, self._min - elapsed)
