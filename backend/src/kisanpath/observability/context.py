"""Correlation identifiers propagated through async request/workflow boundaries."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
conversation_id_var: ContextVar[str | None] = ContextVar("conversation_id", default=None)
workflow_run_id_var: ContextVar[str | None] = ContextVar("workflow_run_id", default=None)
llm_run_id_var: ContextVar[str | None] = ContextVar("llm_run_id", default=None)
tool_run_id_var: ContextVar[str | None] = ContextVar("tool_run_id", default=None)
evaluation_run_id_var: ContextVar[str | None] = ContextVar("evaluation_run_id", default=None)

_VARS = {
    "request_id": request_id_var,
    "conversation_id": conversation_id_var,
    "workflow_run_id": workflow_run_id_var,
    "llm_run_id": llm_run_id_var,
    "tool_run_id": tool_run_id_var,
    "evaluation_run_id": evaluation_run_id_var,
}


@dataclass(frozen=True)
class ContextTokens:
    tokens: tuple[tuple[ContextVar[str | None], Token[str | None]], ...]

    def reset(self) -> None:
        for variable, token in reversed(self.tokens):
            variable.reset(token)


def bind_context(**identifiers: str | None) -> ContextTokens:
    tokens = tuple(
        (variable, variable.set(identifiers[name]))
        for name, variable in _VARS.items()
        if name in identifiers
    )
    return ContextTokens(tokens=tokens)


def correlation_context() -> dict[str, str]:
    return {
        name: value for name, variable in _VARS.items() if (value := variable.get()) is not None
    }
