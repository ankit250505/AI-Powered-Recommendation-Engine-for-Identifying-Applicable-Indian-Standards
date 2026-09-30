from __future__ import annotations

import threading
import time


class ApplicationMetrics:
    def __init__(self):
        self.started_at = time.time()
        self.request_count = 0
        self.error_count = 0
        self.total_duration_ms = 0.0
        self._lock = threading.Lock()

    def observe(self, status_code: int, duration_ms: float) -> None:
        with self._lock:
            self.request_count += 1
            self.total_duration_ms += duration_ms
            if status_code >= 500:
                self.error_count += 1

    def prometheus_text(self) -> str:
        with self._lock:
            request_count = self.request_count
            error_count = self.error_count
            total_duration = self.total_duration_ms / 1000
        uptime = max(0.0, time.time() - self.started_at)
        return "\n".join(
            [
                "# HELP standards_app_up Whether the process is running.",
                "# TYPE standards_app_up gauge",
                "standards_app_up 1",
                "# HELP standards_app_uptime_seconds Process uptime in seconds.",
                "# TYPE standards_app_uptime_seconds gauge",
                f"standards_app_uptime_seconds {uptime:.3f}",
                "# HELP standards_app_requests_total Total HTTP requests.",
                "# TYPE standards_app_requests_total counter",
                f"standards_app_requests_total {request_count}",
                "# HELP standards_app_errors_total Total HTTP 5xx responses.",
                "# TYPE standards_app_errors_total counter",
                f"standards_app_errors_total {error_count}",
                "# HELP standards_app_request_duration_seconds_total Cumulative request duration.",
                "# TYPE standards_app_request_duration_seconds_total counter",
                f"standards_app_request_duration_seconds_total {total_duration:.6f}",
                "",
            ]
        )


metrics = ApplicationMetrics()
