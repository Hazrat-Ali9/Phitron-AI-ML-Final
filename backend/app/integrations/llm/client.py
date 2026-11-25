"""Thin wrapper around any OpenAI-compatible chat API (Groq, Gemini, OpenAI, Ollama, ...).

Switching provider is a .env change: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL.
"""

import json
import logging

import openai
from openai import AsyncOpenAI

from app.integrations.llm.types import (
    LLMReply,
    LLMUnavailableError,
    Message,
    ToolCallRequest,
    ToolDefinition,
)

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        timeout: float = 30.0,
        temperature: float = 0.2,
    ) -> None:
        self._client = AsyncOpenAI(
            base_url=base_url, api_key=api_key, timeout=timeout, max_retries=2
        )
        self.model = model
        self.temperature = temperature

    async def complete(
        self, messages: list[Message], tools: list[ToolDefinition] | None = None
    ) -> LLMReply:
        kwargs = {}
        if tools:
            kwargs = {"tools": tools, "tool_choice": "auto"}
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=self.temperature,
                max_tokens=1024,
                **kwargs,  # type: ignore[arg-type]
            )
        except openai.APIError as exc:
            # Timeouts, rate limits, bad key, provider outage... the user just sees a 503.
            logger.warning("LLM call failed: %s: %s", type(exc).__name__, exc)
            raise LLMUnavailableError() from exc

        if not response.choices:
            raise LLMUnavailableError()
        message = response.choices[0].message
        return LLMReply(
            content=(message.content or "").strip(),
            tool_calls=[_parse_tool_call(call) for call in message.tool_calls or []],
        )


def _parse_tool_call(call: object) -> ToolCallRequest:
    function = getattr(call, "function", None)
    raw = getattr(function, "arguments", None) or "{}"
    try:
        arguments = json.loads(raw)
        if not isinstance(arguments, dict):
            arguments = None
    except json.JSONDecodeError:
        arguments = None
    return ToolCallRequest(
        id=getattr(call, "id", "") or "",
        name=getattr(function, "name", "") or "",
        arguments=arguments,
        raw_arguments=raw,
    )
