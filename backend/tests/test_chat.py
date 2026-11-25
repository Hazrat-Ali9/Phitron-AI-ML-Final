"""Chat endpoint with a scripted fake LLM (no network): history, prompt, errors."""

import json
import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import AsyncClient

from app.integrations.llm.dependencies import get_llm_client
from app.integrations.llm.types import (
    LLMReply,
    LLMUnavailableError,
    Message,
    ToolCallRequest,
    ToolDefinition,
)
from tests.conftest import MakeUser


class FakeLLM:
    def __init__(self, replies: list[LLMReply | Exception]) -> None:
        self.replies = list(replies)
        self.calls: list[tuple[list[Message], list[ToolDefinition] | None]] = []

    async def complete(
        self, messages: list[Message], tools: list[ToolDefinition] | None = None
    ) -> LLMReply:
        self.calls.append(([dict(m) for m in messages], tools))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture
async def fake_llm() -> AsyncIterator[FakeLLM]:
    from app.main import app

    fake = FakeLLM([])
    app.dependency_overrides[get_llm_client] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_llm_client, None)


async def test_chat_sends_history_and_system_prompt(
    client: AsyncClient, make_user: MakeUser, fake_llm: FakeLLM
) -> None:
    user = await make_user("staff", "Md. Karim Uddin")
    fake_llm.replies = [LLMReply(content="Your name is Karim.")]
    res = await client.post(
        "/chat",
        json={
            "message": "What's my name?",
            "history": [
                {"role": "user", "content": "My name is Karim"},
                {"role": "assistant", "content": "Nice to meet you, Karim!"},
            ],
        },
        headers=user.headers,
    )
    assert res.status_code == 200, res.text
    assert res.json() == {"reply": "Your name is Karim.", "tool_calls": [], "sources": []}

    messages, _ = fake_llm.calls[0]
    assert messages[0]["role"] == "system"
    assert "BariBhara assistant" in messages[0]["content"]
    assert "Md. Karim Uddin" in messages[0]["content"]
    assert [m["role"] for m in messages[1:]] == ["user", "assistant", "user"]
    assert messages[-1]["content"] == "What's my name?"


async def test_chat_requires_login(client: AsyncClient) -> None:
    assert (await client.post("/chat", json={"message": "hi"})).status_code == 401


async def test_chat_validates_input(client: AsyncClient, make_user: MakeUser) -> None:
    user = await make_user("tenant")
    res = await client.post("/chat", json={"message": ""}, headers=user.headers)
    assert res.status_code == 422
    history = [{"role": "user", "content": "x"}] * 21
    res = await client.post(
        "/chat", json={"message": "hi", "history": history}, headers=user.headers
    )
    assert res.status_code == 422


async def test_llm_outage_is_503(
    client: AsyncClient, make_user: MakeUser, fake_llm: FakeLLM
) -> None:
    user = await make_user("tenant")
    fake_llm.replies = [LLMUnavailableError()]
    res = await client.post("/chat", json={"message": "hello"}, headers=user.headers)
    assert res.status_code == 503
    assert "temporarily unavailable" in res.json()["detail"]


# ---- tool calling ---------------------------------------------------------------------


def tool_call(name: str, arguments: dict | None = None, call_id: str = "call_1") -> LLMReply:
    raw = json.dumps(arguments or {})
    return LLMReply(
        content="",
        tool_calls=[
            ToolCallRequest(id=call_id, name=name, arguments=arguments or {}, raw_arguments=raw)
        ],
    )


def offered_tools(fake: FakeLLM, call: int = 0) -> set[str]:
    tools = fake.calls[call][1] or []
    return {t["function"]["name"] for t in tools}


@pytest.fixture
async def rented(client: AsyncClient, make_user: MakeUser) -> dict:
    """An admin, a tenant with an active lease on a flat and one unpaid month."""
    admin = await make_user("admin")
    tenant = await make_user("tenant", "Tanvir Hasan")
    suffix = uuid.uuid4().hex[:6]
    building = (
        await client.post(
            "/buildings",
            json={
                "name": f"Chat Villa {suffix}",
                "address": "House 12, Road 5, Mirpur",
                "area": "Mirpur",
                "total_floors": 6,
            },
            headers=admin.headers,
        )
    ).json()
    flat = (
        await client.post(
            "/flats",
            json={
                "building_id": building["id"],
                "flat_no": "2A",
                "floor": 2,
                "bedrooms": 3,
                "bathrooms": 2,
                "size_sqft": 1250,
                "monthly_rent": 22000,
                "service_charge": 2000,
            },
            headers=admin.headers,
        )
    ).json()
    lease = (
        await client.post(
            "/leases",
            json={
                "flat_id": flat["id"],
                "tenant_id": tenant.id,
                "start_date": "2026-01-01",
                "monthly_rent": 24000,
                "nid_number": "1992384756",
            },
            headers=admin.headers,
        )
    ).json()
    await client.post(
        "/payments", json={"lease_id": lease["id"], "month": "2026-11"}, headers=admin.headers
    )
    return {"admin": admin, "tenant": tenant, "flat": flat, "building": building}


async def test_tenant_rent_question_runs_tool(
    client: AsyncClient, rented: dict, fake_llm: FakeLLM
) -> None:
    tenant = rented["tenant"]
    fake_llm.replies = [
        tool_call("get_my_rent_status"),
        LLMReply(content="You owe **৳24,000** for November 2026."),
    ]
    res = await client.post(
        "/chat", json={"message": "How much rent do I owe?"}, headers=tenant.headers
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["tool_calls"] == [{"name": "get_my_rent_status", "arguments": {}}]
    assert "24,000" in body["reply"]

    # the tenant is never offered admin tools
    assert "get_collection_summary" not in offered_tools(fake_llm)
    assert {"get_my_rent_status", "create_maintenance_request"} <= offered_tools(fake_llm)

    # the second LLM call received the real DB numbers as a tool message
    second_messages, _ = fake_llm.calls[1]
    assert second_messages[-2]["tool_calls"][0]["function"]["name"] == "get_my_rent_status"
    tool_msg = second_messages[-1]
    assert tool_msg["role"] == "tool" and tool_msg["tool_call_id"] == "call_1"
    result = json.loads(tool_msg["content"])
    assert result["total_outstanding"] == 24000
    assert result["flat_no"] == "2A"
    # and the system prompt knows the tenant's flat
    assert "flat 2A" in second_messages[0]["content"]


async def test_tenant_cannot_call_admin_tool(
    client: AsyncClient, rented: dict, fake_llm: FakeLLM
) -> None:
    fake_llm.replies = [
        tool_call("get_collection_summary"),
        LLMReply(content="I can't share that."),
    ]
    res = await client.post(
        "/chat", json={"message": "who has not paid?"}, headers=rented["tenant"].headers
    )
    assert res.status_code == 200
    tool_msg = fake_llm.calls[1][0][-1]
    assert "not allowed" in json.loads(tool_msg["content"])["error"]


async def test_admin_collection_summary(
    client: AsyncClient, rented: dict, fake_llm: FakeLLM
) -> None:
    fake_llm.replies = [
        tool_call("get_collection_summary", {"month": "2026-11"}),
        LLMReply(content="ok"),
    ]
    res = await client.post(
        "/chat", json={"message": "collection this month?"}, headers=rented["admin"].headers
    )
    assert res.status_code == 200
    assert "get_my_rent_status" not in offered_tools(fake_llm)
    result = json.loads(fake_llm.calls[1][0][-1]["content"])
    assert result["month"] == "2026-11" and result["outstanding"] >= 24000
    assert any(p["tenant_name"] == "Tanvir Hasan" for p in result["pending_tenants"])


async def test_tenant_creates_maintenance_via_tool(
    client: AsyncClient, rented: dict, fake_llm: FakeLLM
) -> None:
    args = {
        "title": "Kitchen sink leaking",
        "description": "Water under the sink since last night",
        "category": "plumbing",
        "priority": "high",
    }
    fake_llm.replies = [
        tool_call("create_maintenance_request", args),
        LLMReply(content="Done, request created."),
    ]
    res = await client.post(
        "/chat", json={"message": "my kitchen sink is leaking"}, headers=rented["tenant"].headers
    )
    assert res.status_code == 200
    result = json.loads(fake_llm.calls[1][0][-1]["content"])
    assert result["status"] == "open" and result["flat"].startswith("2A")
    mine = (await client.get("/maintenance", headers=rented["tenant"].headers)).json()
    assert any(r["id"] == result["request_id"] for r in mine)


async def test_bad_arguments_go_back_to_the_model(
    client: AsyncClient, rented: dict, fake_llm: FakeLLM
) -> None:
    fake_llm.replies = [
        tool_call("create_maintenance_request", {"title": "x", "category": "roof"}),
        tool_call("does_not_exist", call_id="call_2"),
        LLMReply(content="Could you describe the problem?"),
    ]
    res = await client.post("/chat", json={"message": "fix it"}, headers=rented["tenant"].headers)
    assert res.status_code == 200
    first = json.loads(fake_llm.calls[1][0][-1]["content"])
    assert first["error"].startswith("Invalid arguments")
    second = json.loads(fake_llm.calls[2][0][-1]["content"])
    assert "Unknown tool" in second["error"]


async def test_vacant_flats_tool(client: AsyncClient, rented: dict, fake_llm: FakeLLM) -> None:
    fake_llm.replies = [tool_call("list_vacant_flats", {"area": "Mirpur"}), LLMReply(content="ok")]
    res = await client.post(
        "/chat", json={"message": "any flats in Mirpur?"}, headers=rented["admin"].headers
    )
    assert res.status_code == 200
    result = json.loads(fake_llm.calls[1][0][-1]["content"])
    assert all(f["area"] == "Mirpur" for f in result["flats"])
    assert result["count"] <= 10


async def test_loop_stops_after_max_iterations(
    client: AsyncClient, rented: dict, fake_llm: FakeLLM
) -> None:
    fake_llm.replies = [tool_call("list_vacant_flats", call_id=f"c{i}") for i in range(5)]
    res = await client.post("/chat", json={"message": "loop"}, headers=rented["admin"].headers)
    assert res.status_code == 200
    assert res.json()["reply"].startswith("Sorry")
    assert len(res.json()["tool_calls"]) == 5


async def test_tool_crash_does_not_break_the_chat(
    client: AsyncClient, rented: dict, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    from sqlalchemy import text

    from app.modules.chat import tools as tools_module

    async def broken(ctx, args):  # type: ignore[no-untyped-def]
        await ctx.services.session.execute(text("SELECT 1/0"))  # DB error -> session needs rollback
        return {}

    monkeypatch.setitem(
        tools_module.TOOLS,
        "list_vacant_flats",
        replace(tools_module.TOOLS["list_vacant_flats"], handler=broken),
    )
    fake_llm.replies = [
        tool_call("list_vacant_flats"),
        tool_call("get_my_rent_status", call_id="call_2"),  # needs the DB and the user again
        LLMReply(content="Sorry, flats search failed, but you owe ৳24,000."),
    ]
    res = await client.post(
        "/chat", json={"message": "flats? and my rent?"}, headers=rented["tenant"].headers
    )
    assert res.status_code == 200, res.text
    assert "failed unexpectedly" in json.loads(fake_llm.calls[1][0][-1]["content"])["error"]
    assert json.loads(fake_llm.calls[2][0][-1]["content"])["total_outstanding"] == 24000
