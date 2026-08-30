"""Small metrics port and bounded in-process Prometheus exposition adapter."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping
from threading import Lock
from typing import Protocol

_METRIC_NAME = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
_ALLOWED_LABELS = {
    "method",
    "route",
    "status",
    "provider",
    "model",
    "agent",
    "outcome",
    "stage",
    "reason",
}


class MetricsSink(Protocol):
    def increment(
        self, name: str, *, labels: Mapping[str, str] | None = None, value: float = 1
    ) -> None: ...
    def observe(
        self, name: str, value: float, *, labels: Mapping[str, str] | None = None
    ) -> None: ...


class InMemoryMetrics:
    """Process-local adapter for development/tests; production may replace the port."""

    def __init__(self) -> None:
        self._values: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)
        self._lock = Lock()

    @staticmethod
    def _key(
        name: str, labels: Mapping[str, str] | None
    ) -> tuple[str, tuple[tuple[str, str], ...]]:
        if not _METRIC_NAME.fullmatch(name):
            raise ValueError(f"invalid metric name: {name}")
        safe_labels = tuple(
            sorted(
                (key, str(value)[:100])
                for key, value in (labels or {}).items()
                if key in _ALLOWED_LABELS
            )
        )
        return name, safe_labels

    def increment(
        self, name: str, *, labels: Mapping[str, str] | None = None, value: float = 1
    ) -> None:
        with self._lock:
            self._values[self._key(name, labels)] += value

    def observe(self, name: str, value: float, *, labels: Mapping[str, str] | None = None) -> None:
        self.increment(f"{name}_sum", labels=labels, value=value)
        self.increment(f"{name}_count", labels=labels)

    def render_prometheus(self) -> str:
        with self._lock:
            items = tuple(sorted(self._values.items()))
        lines = []
        for (name, labels), value in items:
            suffix = ""
            if labels:
                encoded = ",".join(f'{key}="{item.replace(chr(34), "_")}"' for key, item in labels)
                suffix = "{" + encoded + "}"
            lines.append(f"{name}{suffix} {value:g}")
        return "\n".join(lines) + ("\n" if lines else "")


class NoopMetrics:
    def increment(
        self, name: str, *, labels: Mapping[str, str] | None = None, value: float = 1
    ) -> None:
        del name, labels, value

    def observe(self, name: str, value: float, *, labels: Mapping[str, str] | None = None) -> None:
        del name, value, labels
