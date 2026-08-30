"""Prompt boundary for approved-but-untrusted retrieved text."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_INJECTION_MARKERS = (
    "ignore previous",
    "ignore all instructions",
    "system prompt",
    "developer message",
    "execute command",
    "call this tool",
)


class UntrustedEvidence(BaseModel):
    """Bounded evidence payload; warning flags are audit metadata, not a verdict."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_ref_id: str = Field(min_length=1, max_length=200)
    locator: str = Field(min_length=1, max_length=500)
    text: str = Field(min_length=1, max_length=4000)
    suspicious_markers: tuple[str, ...] = ()


def prepare_untrusted_evidence(
    text: str,
    *,
    source_ref_id: str,
    locator: str,
    max_characters: int = 1000,
) -> UntrustedEvidence:
    """Normalize controls, bound size, and flag instruction-like source content."""

    cleaned = _CONTROL_CHARACTERS.sub(" ", text).strip()[:max_characters]
    lowered = cleaned.casefold()
    markers = tuple(marker for marker in _INJECTION_MARKERS if marker in lowered)
    return UntrustedEvidence(
        source_ref_id=source_ref_id,
        locator=locator,
        text=cleaned,
        suspicious_markers=markers,
    )


def render_evidence_for_prompt(evidence: UntrustedEvidence) -> str:
    """Create a data-only envelope with explicit non-executable delimiters."""

    return (
        "<UNTRUSTED_EVIDENCE_DATA>\n"
        f"source_ref_id={evidence.source_ref_id}\n"
        f"locator={evidence.locator}\n"
        f"content={evidence.text}\n"
        "</UNTRUSTED_EVIDENCE_DATA>"
    )
