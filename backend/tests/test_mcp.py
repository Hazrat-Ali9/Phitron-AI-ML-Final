"""MCP server, connected in-process: tools, resource and prompt return real DB data."""

import json
import uuid

import pytest
from httpx import AsyncClient
from mcp import Client

from app.mcp.server import mcp
from tests.conftest import MakeUser


@pytest.fixture
async def building(client: AsyncClient, make_user: MakeUser) -> dict:
    admin = await make_user("admin", "Abdur Rahman")
    tenant = await make_user("tenant", "Rafiqul Alam")
    b = (
        await client.post(
            "/buildings",
            json={
                "name": f"MCP Manzil {uuid.uuid4().hex[:6]}",
                "address": "House 34/A, Road 9/A",
                "area": "Dhanmondi",
                "total_floors": 7,
            },
            headers=admin.headers,
        )
    ).json()
    flats = []
    for flat_no, floor, rent in [("3A", 3, 45000), ("4A", 4, 46000)]:
        flats.append(
            (
                await client.post(
                    "/flats",
                    json={
                        "building_id": b["id"],
                        "flat_no": flat_no,
                        "floor": floor,
                        "bedrooms": 3,
                        "bathrooms": 3,
                        "size_sqft": 1800,
                        "monthly_rent": rent,
                        "service_charge": 5000,
                    },
                    headers=admin.headers,
                )
            ).json()
        )
    lease = (
        await client.post(
            "/leases",
            json={
                "flat_id": flats[1]["id"],
                "tenant_id": tenant.id,
                "start_date": "2026-01-01",
                "monthly_rent": 51000,
                "nid_number": "1979283746",
            },
            headers=admin.headers,
        )
    ).json()
    await client.post(
        "/payments",
        json={"lease_id": lease["id"], "month": "2026-11", "amount_paid": 20000},
        headers=admin.headers,
    )
    return {"building": b, "vacant": flats[0], "occupied": flats[1]}


def structured(result) -> object:  # type: ignore[no-untyped-def]
    assert not result.is_error, result.content
    if result.structured_content is not None:
        content = result.structured_content
        return content.get("result", content) if isinstance(content, dict) else content
    return json.loads(result.content[0].text)


async def test_lists_tools_resource_and_prompt() -> None:
    async with Client(mcp) as client:
        tools = {t.name for t in (await client.list_tools()).tools}
        assert {
            "list_vacant_flats",
            "get_rent_due_summary",
            "create_maintenance_request",
            "search_building_documents",
        } <= tools
        templates = (await client.list_resource_templates()).resource_templates
        assert [t.uri_template for t in templates] == [
            "baribhara://buildings/{building_id}/summary"
        ]
        prompts = {p.name for p in (await client.list_prompts()).prompts}
        assert "rent_reminder" in prompts


async def test_tools_return_db_data(building: dict) -> None:
    name = building["building"]["name"]
    async with Client(mcp) as client:
        flats = structured(await client.call_tool("list_vacant_flats", {"area": "dhanmondi"}))
        mine = [f for f in flats if f["building_name"] == name]
        assert [f["flat_no"] for f in mine] == ["3A"]

        summary = structured(await client.call_tool("get_rent_due_summary", {"month": "2026-11"}))
        row = next(b for b in summary["by_building"] if b["building"] == name)
        assert row == {
            "building": name,
            "expected": 51000,
            "collected": 20000,
            "outstanding": 31000,
        }

        created = structured(
            await client.call_tool(
                "create_maintenance_request",
                {
                    "flat_id": building["occupied"]["id"],
                    "title": "Lift stops between floors",
                    "description": "Lift stopped twice this week.",
                    "category": "lift",
                    "priority": "urgent",
                },
            )
        )
        assert created["status"] == "open" and created["building_name"] == name
        assert created["reported_by_name"]  # acts as the owner

        bad = await client.call_tool("get_rent_due_summary", {"month": "2026-13"})
        assert bad.is_error


async def test_missing_flat_is_a_readable_error(building: dict) -> None:
    async with Client(mcp) as client:
        result = await client.call_tool(
            "create_maintenance_request",
            {
                "flat_id": 999_999,
                "title": "Leak",
                "description": "Leaking pipe",
                "category": "plumbing",
            },
        )
        assert result.is_error
        assert "Flat not found" in result.content[0].text


async def test_building_summary_resource(building: dict) -> None:
    bid = building["building"]["id"]
    async with Client(mcp) as client:
        result = await client.read_resource(f"baribhara://buildings/{bid}/summary")
        data = json.loads(result.contents[0].text)
    assert data["flats"] == 2 and data["occupied"] == 1 and data["occupancy_percent"] == 50.0
    assert [f["flat_no"] for f in data["vacant_flats"]] == ["3A"]
    assert data["collection_this_month"]["month"]


async def test_rent_reminder_prompt() -> None:
    async with Client(mcp) as client:
        result = await client.get_prompt(
            "rent_reminder",
            {
                "tenant_name": "Tanvir Hasan",
                "amount_due": "24,000",
                "month": "November 2026",
                "language": "bn",
            },
        )
    text = result.messages[0].content.text
    assert "Tanvir Hasan" in text and "৳24,000" in text and "7th" in text and "Bangla" in text
