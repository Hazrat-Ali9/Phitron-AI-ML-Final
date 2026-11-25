"""The chat agent: system prompt + history + tool-calling loop."""

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.integrations.embeddings.client import EmbeddingClient
from app.integrations.llm.client import LLMClient
from app.integrations.llm.types import Message, ToolCallRequest
from app.modules.chat.prompts import AskerContext, build_system_prompt
from app.modules.chat.schemas import (
    MAX_HISTORY,
    ChatRequest,
    ChatResponse,
    SourceOut,
    ToolCallOut,
)
from app.modules.chat.tools import TOOLS, ToolContext, tools_for_role
from app.modules.users.models import RoleName, User
from app.services import Services

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 5
SNIPPET_CHARS = 150
FALLBACK_REPLY = (
    "Sorry, I couldn't finish that request. Please try asking in a simpler way, "
    "or contact the caretaker."
)


@dataclass
class _Run:
    """Everything collected while answering one message."""

    tool_calls: list[ToolCallOut] = field(default_factory=list)
    sources: dict[tuple[str, str], SourceOut] = field(default_factory=dict)


class ChatService:
    def __init__(self, llm: LLMClient, session: AsyncSession, embeddings: EmbeddingClient) -> None:
        self.llm = llm
        self.session = session
        self.services = Services(session, embeddings)

    async def chat(self, user: User, request: ChatRequest) -> ChatResponse:
        tools = tools_for_role(user.role_name)
        tool_definitions = [tool.definition() for tool in tools]
        allowed = {tool.name for tool in tools}

        # 1. system prompt -> trimmed history -> new message
        system_prompt = build_system_prompt(await self._asker(user), allowed, date.today())
        messages: list[Message] = [{"role": "system", "content": system_prompt}]
        messages += [turn.model_dump() for turn in request.history[-MAX_HISTORY:]]
        messages.append({"role": "user", "content": request.message})

        run = _Run()
        for _ in range(MAX_ITERATIONS):
            # 2. ask the model, offering only this role's tools
            reply = await self.llm.complete(messages, tool_definitions or None)

            # 3. no tool calls -> this is the final answer
            if not reply.tool_calls:
                return self._response(reply.content or FALLBACK_REPLY, run)

            # 4. run every requested tool and feed the results back
            messages.append(reply.as_message())
            for call in reply.tool_calls:
                result = await self._run_tool(user, call, allowed, run)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": call.name,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )
            # 5. loop: the model now sees the tool results

        logger.warning("Chat hit the %d-iteration limit for user %s", MAX_ITERATIONS, user.id)
        return self._response(FALLBACK_REPLY, run)

    async def _run_tool(
        self, user: User, call: ToolCallRequest, allowed: set[str], run: _Run
    ) -> dict[str, Any]:
        run.tool_calls.append(ToolCallOut(name=call.name, arguments=call.arguments or {}))

        tool = TOOLS.get(call.name)
        if tool is None:
            return {"error": f"Unknown tool '{call.name}'."}
        # Defense in depth: the model was never offered this tool, but check again.
        if call.name not in allowed or user.role_name not in tool.roles:
            return {"error": "You are not allowed to use this tool for this user."}
        if call.arguments is None:
            return {"error": "Arguments were not valid JSON. Send a JSON object."}

        try:
            args = tool.args_model.model_validate(call.arguments)
        except ValidationError as exc:
            problems = "; ".join(
                f"{'.'.join(map(str, e['loc'])) or 'arguments'}: {e['msg']}" for e in exc.errors()
            )
            return {"error": f"Invalid arguments: {problems}"}

        try:
            result = await tool.handler(ToolContext(user=user, services=self.services), args)
        except AppError as exc:
            # Business-rule errors (no active lease, not found, ...) are for the model to explain.
            return {"error": exc.message}
        except Exception:
            logger.exception("Tool %s failed", call.name)
            await self._recover_session(user)
            return {"error": "The tool failed unexpectedly. Apologise and suggest trying later."}

        for source in result.get("results", []) if call.name == "search_knowledge" else []:
            key = (source["title"], source["content"][:SNIPPET_CHARS])
            run.sources.setdefault(
                key,
                SourceOut(
                    title=source["title"],
                    snippet=_snippet(source["content"]),
                    score=round(float(source["score"]), 3),
                ),
            )
        return result

    async def _recover_session(self, user: User) -> None:
        """After a DB error the session must be rolled back; reload the user it expired."""
        await self.session.rollback()
        await self.session.refresh(user)

    @staticmethod
    def _response(reply: str, run: _Run) -> ChatResponse:
        sources = sorted(run.sources.values(), key=lambda s: s.score, reverse=True)
        return ChatResponse(reply=reply, tool_calls=run.tool_calls, sources=sources)

    async def _asker(self, user: User) -> AskerContext:
        if user.role_name == RoleName.TENANT:
            lease = await self.services.leases.current_for_tenant(user)
            if lease is not None:
                return AskerContext(
                    name=user.full_name,
                    role=user.role_name,
                    building=lease.flat.building.name,
                    flat_no=lease.flat.flat_no,
                    area=lease.flat.building.area,
                )
        return AskerContext(name=user.full_name, role=user.role_name)


def _snippet(text: str) -> str:
    text = " ".join(text.split())
    if len(text) <= SNIPPET_CHARS:
        return text
    return text[:SNIPPET_CHARS].rsplit(" ", 1)[0] + "…"
