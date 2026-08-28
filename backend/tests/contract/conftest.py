from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import httpx
import pytest

from kisanpath.llm.base import LLMClient
from kisanpath.llm.models import ProviderCapabilities
from kisanpath.llm.providers.anthropic import AnthropicAdapter
from kisanpath.llm.providers.gemini import GeminiAdapter
from kisanpath.llm.providers.ollama import OllamaAdapter
from kisanpath.llm.providers.openai import OpenAIAdapter
from kisanpath.llm.providers.openai_compatible import OpenAICompatibleAdapter


class FakeProviderError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"provider error {status_code}")
        self.status_code = status_code


class AsyncItems:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def __aiter__(self) -> AsyncItems:
        self._iterator = iter(self._items)
        return self

    async def __anext__(self) -> Any:
        try:
            return next(self._iterator)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


@dataclass
class Script:
    mode: str = "plain"
    last_request: dict[str, Any] = field(default_factory=dict)

    def fail(self) -> None:
        if self.mode == "rate_limit":
            raise FakeProviderError(429)
        if self.mode == "authentication":
            raise FakeProviderError(401)
        if self.mode == "unavailable":
            raise FakeProviderError(503)
        if self.mode == "timeout":
            raise TimeoutError
        if self.mode == "cancelled":
            raise asyncio.CancelledError

    def text(self) -> str:
        if self.mode == "structured":
            return '{"name":"Kisan","count":2}'
        if self.mode == "invalid":
            return '{"name":4}'
        return "hello farmer"


@dataclass
class ContractCase:
    adapter: LLMClient
    script: Script
    http_client: httpx.AsyncClient | None = None

    async def close(self) -> None:
        if self.http_client:
            await self.http_client.aclose()


class FakeOpenAICompletions:
    def __init__(self, script: Script) -> None:
        self.script = script

    async def create(self, **kwargs: Any) -> Any:
        self.script.last_request = kwargs
        self.script.fail()
        if kwargs.get("stream"):
            return AsyncItems(
                [
                    {
                        "choices": [{"delta": {"content": "hello "}, "finish_reason": None}]
                    },
                    {
                        "choices": [{"delta": {"content": "farmer"}, "finish_reason": "stop"}]
                    },
                    {
                        "choices": [],
                        "usage": {
                            "prompt_tokens": 3,
                            "completion_tokens": 2,
                            "total_tokens": 5,
                        },
                    },
                ]
            )
        message: dict[str, Any] = {"content": self.script.text(), "tool_calls": []}
        finish = "stop"
        if self.script.mode == "tool":
            message = {
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-1",
                        "function": {"name": "lookup", "arguments": '{"scheme":"demo"}'},
                    }
                ],
            }
            finish = "tool_calls"
        return {
            "id": "openai-request",
            "model": kwargs["model"],
            "choices": [{"message": message, "finish_reason": finish}],
            "usage": {
                "prompt_tokens": -1 if self.script.mode == "malformed" else 3,
                "completion_tokens": 2,
                "total_tokens": 5,
            },
        }


class FakeModels:
    async def retrieve(self, model: str) -> dict[str, str]:
        return {"id": model}


def openai_case() -> ContractCase:
    script = Script()
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeOpenAICompletions(script)), models=FakeModels()
    )
    return ContractCase(OpenAIAdapter(alias="openai", model="test-model", client=client), script)


class FakeAnthropicMessages:
    def __init__(self, script: Script) -> None:
        self.script = script

    async def create(self, **kwargs: Any) -> Any:
        self.script.last_request = kwargs
        self.script.fail()
        if kwargs.get("stream"):
            return AsyncItems(
                [
                    {
                        "type": "content_block_delta",
                        "delta": {"type": "text_delta", "text": "hello "},
                    },
                    {
                        "type": "content_block_delta",
                        "delta": {"type": "text_delta", "text": "farmer"},
                    },
                    {
                        "type": "message_delta",
                        "delta": {"stop_reason": "end_turn"},
                        "usage": {"output_tokens": 2},
                    },
                ]
            )
        content: list[dict[str, Any]] = [{"type": "text", "text": self.script.text()}]
        stop = "end_turn"
        if self.script.mode == "tool":
            content = [
                {
                    "type": "tool_use",
                    "id": "call-1",
                    "name": "lookup",
                    "input": {"scheme": "demo"},
                }
            ]
            stop = "tool_use"
        return {
            "id": "anthropic-request",
            "model": kwargs["model"],
            "content": content,
            "stop_reason": stop,
            "usage": {
                "input_tokens": -1 if self.script.mode == "malformed" else 3,
                "output_tokens": 2,
            },
        }


def anthropic_case() -> ContractCase:
    script = Script()
    client = SimpleNamespace(messages=FakeAnthropicMessages(script), models=FakeModels())
    return ContractCase(
        AnthropicAdapter(alias="anthropic", model="test-model", client=client), script
    )


class FakeGeminiModels:
    def __init__(self, script: Script) -> None:
        self.script = script

    async def generate_content(self, **kwargs: Any) -> Any:
        self.script.last_request = kwargs
        self.script.fail()
        parts: list[dict[str, Any]] = [{"text": self.script.text()}]
        text: str | None = self.script.text()
        finish = "STOP"
        if self.script.mode == "tool":
            text = None
            finish = "FUNCTION_CALL"
            parts = [
                {
                    "function_call": {
                        "id": "call-1",
                        "name": "lookup",
                        "args": {"scheme": "demo"},
                    }
                }
            ]
        return {
            "text": text,
            "model_version": kwargs["model"],
            "candidates": [{"finish_reason": finish, "content": {"parts": parts}}],
            "usage_metadata": {
                "prompt_token_count": -1 if self.script.mode == "malformed" else 3,
                "candidates_token_count": 2,
                "total_token_count": 5,
            },
        }

    async def generate_content_stream(self, **kwargs: Any) -> AsyncItems:
        self.script.last_request = kwargs
        self.script.fail()
        return AsyncItems(
            [
                {"text": "hello ", "candidates": []},
                {
                    "text": "farmer",
                    "candidates": [{"finish_reason": "STOP"}],
                    "usage_metadata": {
                        "prompt_token_count": 3,
                        "candidates_token_count": 2,
                        "total_token_count": 5,
                    },
                },
            ]
        )

    async def get(self, *, model: str) -> dict[str, str]:
        return {"name": model}


def gemini_case() -> ContractCase:
    script = Script()
    client = SimpleNamespace(models=FakeGeminiModels(script))
    return ContractCase(GeminiAdapter(alias="gemini", model="test-model", client=client), script)


def http_case(kind: str) -> ContractCase:
    script = Script()

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"models": []})
        script.last_request = json.loads(request.content)
        if script.mode == "rate_limit":
            return httpx.Response(429, json={"error": "limited"})
        if script.mode == "authentication":
            return httpx.Response(401, json={"error": "unauthorized"})
        if script.mode == "unavailable":
            return httpx.Response(503, json={"error": "unavailable"})
        if script.mode == "timeout":
            raise httpx.ReadTimeout("timeout", request=request)
        if script.mode == "cancelled":
            raise asyncio.CancelledError

        is_stream = bool(script.last_request.get("stream"))
        if kind == "compatible":
            if is_stream:
                body = (
                    'data: {"choices":[{"delta":{"content":"hello "},"finish_reason":null}]}\n\n'
                    'data: {"choices":[{"delta":{"content":"farmer"},"finish_reason":"stop"}]}\n\n'
                    'data: {"choices":[],"usage":{"prompt_tokens":3,'
                    '"completion_tokens":2,"total_tokens":5}}\n\n'
                    "data: [DONE]\n\n"
                )
                return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})
            message: dict[str, Any] = {"content": script.text(), "tool_calls": []}
            finish = "stop"
            if script.mode == "tool":
                message = {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "function": {
                                "name": "lookup",
                                "arguments": '{"scheme":"demo"}',
                            },
                        }
                    ],
                }
                finish = "tool_calls"
            return httpx.Response(
                200,
                json={
                    "id": "compatible-request",
                    "model": script.last_request["model"],
                    "choices": [{"message": message, "finish_reason": finish}],
                    "usage": {
                        "prompt_tokens": -1 if script.mode == "malformed" else 3,
                        "completion_tokens": 2,
                        "total_tokens": 5,
                    },
                },
            )

        if is_stream:
            body = "\n".join(
                [
                    json.dumps({"message": {"content": "hello "}, "done": False}),
                    json.dumps(
                        {
                            "message": {"content": "farmer"},
                            "done": True,
                            "done_reason": "stop",
                            "prompt_eval_count": 3,
                            "eval_count": 2,
                        }
                    ),
                ]
            )
            return httpx.Response(200, text=body)
        message = {"content": script.text(), "tool_calls": []}
        finish = "stop"
        if script.mode == "tool":
            message = {
                "content": "",
                "tool_calls": [
                    {
                        "id": "call-1",
                        "function": {
                            "name": "lookup",
                            "arguments": {"scheme": "demo"},
                        },
                    }
                ],
            }
            finish = "tool_calls"
        return httpx.Response(
            200,
            json={
                "model": script.last_request["model"],
                "message": message,
                "done": True,
                "done_reason": finish,
                "prompt_eval_count": -1 if script.mode == "malformed" else 3,
                "eval_count": 2,
            },
        )

    client = httpx.AsyncClient(
        base_url="http://provider.test", transport=httpx.MockTransport(handler)
    )
    if kind == "compatible":
        adapter: LLMClient = OpenAICompatibleAdapter(
            alias="openai_compatible",
            model="test-model",
            client=client,
            capabilities=ProviderCapabilities(native_tools=True),
        )
    else:
        adapter = OllamaAdapter(alias="ollama", model="test-model", client=client)
    return ContractCase(adapter, script, client)


CASE_FACTORIES = [
    openai_case,
    anthropic_case,
    gemini_case,
    lambda: http_case("ollama"),
    lambda: http_case("compatible"),
]
CASE_IDS = ["openai", "anthropic", "gemini", "ollama", "openai-compatible"]


@pytest.fixture(params=CASE_FACTORIES, ids=CASE_IDS)
async def adapter_case(request: pytest.FixtureRequest) -> Any:
    case = request.param()
    yield case
    await case.close()
