"""Provider-independent generation and structured-output example."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from kisanpath.llm import (
    LLMMessage,
    LLMRequest,
    LLMRouter,
    MessageRole,
    StructuredLLMRequest,
    create_builtin_registry,
    load_llm_settings,
)


class LanguageResult(BaseModel):
    language: str
    confidence: float


async def main() -> None:
    settings = load_llm_settings("examples/llm.example.toml")
    router = LLMRouter(settings, create_builtin_registry())
    request = LLMRequest(
        messages=(
            LLMMessage(
                role=MessageRole.USER,
                content="Identify the language: મને સિંચાઈ માટે સહાય જોઈએ છે.",
            ),
        ),
        max_output_tokens=64,
    )

    plain = await router.generate(request, agent="profile")
    print(plain.text)

    structured = await router.generate_structured(
        StructuredLLMRequest(request=request, output_schema=LanguageResult),
        agent="profile",
    )
    print(structured.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
