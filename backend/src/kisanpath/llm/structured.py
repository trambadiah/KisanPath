"""Provider-independent local structured-output validation."""

from __future__ import annotations

import json
import re
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from kisanpath.llm.exceptions import LLMSchemaValidationError

T = TypeVar("T", bound=BaseModel)
_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


def validate_structured_text(
    text: str,
    schema: type[T],
    *,
    provider: str,
    model: str,
) -> T:
    """Parse JSON and validate it locally, even when a provider enforces a schema."""

    candidate = text.strip()
    fenced = _FENCE.match(candidate)
    if fenced:
        candidate = fenced.group(1)
    try:
        payload = json.loads(candidate)
        return schema.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        raise LLMSchemaValidationError(
            f"{provider} returned content that does not match {schema.__name__}",
            provider=provider,
            model=model,
        ) from exc
