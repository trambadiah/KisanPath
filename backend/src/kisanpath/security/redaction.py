"""Conservative secret and sensitive-identifier redaction for operational data."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

_SECRET_KEYS = re.compile(
    r"(?:authorization|api[-_]?key|token|secret|password|cookie|credential|bank|aadhaar)",
    re.IGNORECASE,
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_KEY_VALUE = re.compile(r"(?i)\b(api[-_]?key|token|secret|password)\s*[:=]\s*[^\s,;]+")
_AADHAAR = re.compile(r"(?<!\d)(?:\d[ -]?){11}\d(?!\d)")


def redact(value: Any) -> Any:
    """Return a log-safe copy without mutating the source object."""

    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _SECRET_KEYS.search(str(key)) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, str):
        cleaned = _BEARER.sub("Bearer [REDACTED]", value)
        cleaned = _KEY_VALUE.sub(lambda match: f"{match.group(1)}=[REDACTED]", cleaned)
        return _AADHAAR.sub("[REDACTED_ID]", cleaned)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        return [redact(item) for item in value]
    if isinstance(value, bytes):
        return f"[BINARY:{len(value)} bytes]"
    return value
