"""Lightweight Prometheus Metrics Registry for Custodian AI Services.

Produces standard Prometheus exposition text format (/metrics) without external
dependencies, tracking request counters, error rates, and custom domain metrics.
"""

from __future__ import annotations

import threading
from typing import Dict, Tuple


class MetricsRegistry:
    """Thread-safe, lightweight metrics store."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self._lock = threading.Lock()
        # Key: (metric_name, label_key, label_val) -> float/int
        self._counters: Dict[Tuple[str, str, str], float] = {}

    def inc(
        self,
        metric_name: str,
        amount: float = 1.0,
        label_key: str = "status",
        label_val: str = "200",
    ) -> None:
        """Increment a counter metric."""
        key = (metric_name, label_key, label_val)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + amount

    def to_prometheus_text(self) -> str:
        """Render all recorded metrics into standard Prometheus text format."""
        with self._lock:
            snapshot = dict(self._counters)

        lines = [
            "# HELP custodian_service_info Build and service metadata",
            '# TYPE custodian_service_info gauge',
            f'custodian_service_info{{service="{self.service_name}"}} 1',
        ]

        # Group by metric name
        metrics_by_name: Dict[str, list] = {}
        for (m_name, l_key, l_val), val in snapshot.items():
            metrics_by_name.setdefault(m_name, []).append((l_key, l_val, val))

        for m_name, entries in metrics_by_name.items():
            lines.append(f"# TYPE {m_name} counter")
            for l_key, l_val, val in entries:
                lines.append(
                    f'{m_name}{{service="{self.service_name}",{l_key}="{l_val}"}} {val}'
                )

        return "\n".join(lines) + "\n"
