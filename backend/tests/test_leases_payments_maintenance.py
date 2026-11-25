"""Step 6 checks: active-lease 409, flat status sync, computed payment status, tenant isolation."""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import AuthedUser, MakeUser


@pytest.fixture(scope="module")
async def admin(make_user: MakeUser) -> AuthedUser:
    return await make_user("admin", "Abdur Rahman")


@pytest.fixture(scope="module")
async def staff(make_user: MakeUser) -> AuthedUser:
    return await make_user("staff", "Md. Karim Uddin")


async def new_flat(client: AsyncClient, admin: AuthedUser) -> dict:
    res = await client.post(
        "/buildings",
        json={
            "name": f"Lease Villa {uuid.uuid4().hex[:6]}",
            "address": "House 7, Road 14, Sector 11, Uttara",
            "area": "Uttara",
            "total_floors": 5,
        },
        headers=admin.headers,
    )
    building = res.json()
    res = await client.post(
        "/flats",
        json={
            "building_id": building["id"],
            "flat_no": "2A",
            "floor": 2,
            "bedrooms": 3,
            "bathrooms": 2,
            "size_sqft": 1350,
            "monthly_rent": 26000,
            "service_charge": 3000,
        },
        headers=admin.headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


def lease_body(flat_id: int, tenant_id: int, **overrides: object) -> dict:
    return {
        "flat_id": flat_id,
        "tenant_id": tenant_id,
        "start_date": "2026-08-01",
        "monthly_rent": 29000,
        "advance_amount": 52000,
        "nid_number": "1992384756",
        "family_members": 4,
        **overrides,
    }


async def flat_status(client: AsyncClient, admin: AuthedUser, flat_id: int) -> str:
    return (await client.get(f"/flats/{flat_id}", headers=admin.headers)).json()["status"]


async def test_lease_lifecycle_syncs_flat_status(
    client: AsyncClient, admin: AuthedUser, make_user: MakeUser
) -> None:
    flat = await new_flat(client, admin)
    tenant = await make_user("tenant", "Tanvir Hasan")

    res = await client.post(
        "/leases", json=lease_body(flat["id"], tenant.id), headers=admin.headers
    )
    assert res.status_code == 201, res.text
    lease = res.json()
    assert lease["tenant_name"] == "Tanvir Hasan"
    assert lease["flat_no"] == "2A"
    assert await flat_status(client, admin, flat["id"]) == "occupied"

    # second active lease on the same flat -> 409
    other = await make_user("tenant")
    res = await client.post("/leases", json=lease_body(flat["id"], other.id), headers=admin.headers)
    assert res.status_code == 409

    # flat with an active lease cannot be deleted or set to vacant
    assert (await client.delete(f"/flats/{flat['id']}", headers=admin.headers)).status_code == 409
    res = await client.patch(
        f"/flats/{flat['id']}", json={"status": "vacant"}, headers=admin.headers
    )
    assert res.status_code == 409

    # "End lease" exactly like the frontend sends it
    res = await client.patch(
        f"/leases/{lease['id']}",
        json={"is_active": False, "end_date": "2026-11-30"},
        headers=admin.headers,
    )
    assert res.status_code == 200 and res.json()["is_active"] is False
    assert await flat_status(client, admin, flat["id"]) == "vacant"

    # now a new lease is allowed
    res = await client.post("/leases", json=lease_body(flat["id"], other.id), headers=admin.headers)
    assert res.status_code == 201
    new_lease = res.json()

    # deleting the active lease frees the flat again
    res = await client.delete(f"/leases/{new_lease['id']}", headers=admin.headers)
    assert res.status_code == 204
    assert await flat_status(client, admin, flat["id"]) == "vacant"


async def test_ending_lease_keeps_maintenance_status(
    client: AsyncClient, admin: AuthedUser, make_user: MakeUser
) -> None:
    flat = await new_flat(client, admin)
    tenant = await make_user("tenant")
    lease = (
        await client.post("/leases", json=lease_body(flat["id"], tenant.id), headers=admin.headers)
    ).json()
    res = await client.patch(
        f"/flats/{flat['id']}", json={"status": "maintenance"}, headers=admin.headers
    )
    assert res.status_code == 200
    await client.patch(f"/leases/{lease['id']}", json={"is_active": False}, headers=admin.headers)
    assert await flat_status(client, admin, flat["id"]) == "maintenance"


async def test_lease_validation(client: AsyncClient, admin: AuthedUser, staff: AuthedUser) -> None:
    flat = await new_flat(client, admin)
    # staff is not a tenant -> 422 on tenant_id
    res = await client.post("/leases", json=lease_body(flat["id"], staff.id), headers=admin.headers)
    assert res.status_code == 422
    assert res.json()["detail"][0]["loc"] == ["body", "tenant_id"]

    res = await client.post(
        "/leases",
        json=lease_body(flat["id"], staff.id, nid_number="12345", end_date="2026-01-01"),
        headers=admin.headers,
    )
    assert res.status_code == 422

    # staff cannot read leases at all
    assert (await client.get("/leases", headers=staff.headers)).status_code == 403


async def test_payments_status_and_duplicates(
    client: AsyncClient, admin: AuthedUser, make_user: MakeUser
) -> None:
    flat = await new_flat(client, admin)
    tenant = await make_user("tenant")
    lease = (
        await client.post("/leases", json=lease_body(flat["id"], tenant.id), headers=admin.headers)
    ).json()

    res = await client.post(
        "/payments",
        json={"lease_id": lease["id"], "month": "2026-11", "amount_paid": 0},
        headers=admin.headers,
    )
    assert res.status_code == 201, res.text
    payment = res.json()
    assert payment["amount_due"] == 29000  # defaults to the lease rent
    assert payment["status"] == "due"
    assert payment["paid_at"] is None

    dup = await client.post(
        "/payments", json={"lease_id": lease["id"], "month": "2026-11"}, headers=admin.headers
    )
    assert dup.status_code == 409

    bad = await client.post(
        "/payments", json={"lease_id": lease["id"], "month": "2026-13"}, headers=admin.headers
    )
    assert bad.status_code == 422

    res = await client.patch(
        f"/payments/{payment['id']}",
        json={"amount_paid": 15000, "method": "bkash", "trx_id": "BK7X9Q2M4P"},
        headers=admin.headers,
    )
    assert res.json()["status"] == "partial" and res.json()["paid_at"] is not None

    res = await client.patch(
        f"/payments/{payment['id']}", json={"amount_paid": 29000}, headers=admin.headers
    )
    assert res.json()["status"] == "paid"

    res = await client.patch(
        f"/payments/{payment['id']}", json={"amount_paid": -1}, headers=admin.headers
    )
    assert res.status_code == 422

    res = await client.get(
        "/payments", params={"month": "2026-11", "status": "paid"}, headers=admin.headers
    )
    assert payment["id"] in [p["id"] for p in res.json()]


async def test_tenant_sees_only_own_data(
    client: AsyncClient, admin: AuthedUser, make_user: MakeUser
) -> None:
    flat_a = await new_flat(client, admin)
    flat_b = await new_flat(client, admin)
    alice = await make_user("tenant", "Nusrat Jahan")
    bob = await make_user("tenant", "Farhana Akter")
    lease_a = (
        await client.post("/leases", json=lease_body(flat_a["id"], alice.id), headers=admin.headers)
    ).json()
    lease_b = (
        await client.post("/leases", json=lease_body(flat_b["id"], bob.id), headers=admin.headers)
    ).json()
    pay_b = (
        await client.post(
            "/payments", json={"lease_id": lease_b["id"], "month": "2026-10"}, headers=admin.headers
        )
    ).json()

    leases = (await client.get("/leases", headers=alice.headers)).json()
    assert [lease["id"] for lease in leases] == [lease_a["id"]]
    # someone else's lease or payment -> 404, not 403 (do not leak that it exists)
    assert (await client.get(f"/leases/{lease_b['id']}", headers=alice.headers)).status_code == 404
    assert (await client.get(f"/payments/{pay_b['id']}", headers=alice.headers)).status_code == 404
    assert all(
        p["lease_id"] == lease_a["id"]
        for p in (await client.get("/payments", headers=alice.headers)).json()
    )
    # tenants cannot write rent records
    res = await client.post(
        "/payments", json={"lease_id": lease_a["id"], "month": "2026-09"}, headers=alice.headers
    )
    assert res.status_code == 403


async def test_maintenance_flow(
    client: AsyncClient, admin: AuthedUser, staff: AuthedUser, make_user: MakeUser
) -> None:
    flat = await new_flat(client, admin)
    tenant = await make_user("tenant", "Ayesha Siddiqua")
    no_lease = await make_user("tenant")
    await client.post("/leases", json=lease_body(flat["id"], tenant.id), headers=admin.headers)

    body = {
        "title": "Low gas pressure in the morning",
        "description": "Gas burner flame is very low between 7am and 10am.",
        "category": "gas",
        "flat_id": 999_999,  # ignored for tenants
    }
    res = await client.post("/maintenance", json=body, headers=tenant.headers)
    assert res.status_code == 201, res.text
    req = res.json()
    assert req["flat_id"] == flat["id"]
    assert req["priority"] == "medium" and req["status"] == "open"
    assert req["reported_by_name"] == "Ayesha Siddiqua"

    # tenant without an active lease -> 403
    assert (
        await client.post("/maintenance", json=body, headers=no_lease.headers)
    ).status_code == 403

    # staff/admin must give flat_id
    res = await client.post("/maintenance", json={**body, "flat_id": None}, headers=staff.headers)
    assert res.status_code == 422

    # tenant cannot update; staff can, and only assign to staff/admin
    patch_url = f"/maintenance/{req['id']}"
    assert (
        await client.patch(patch_url, json={"status": "resolved"}, headers=tenant.headers)
    ).status_code == 403
    res = await client.patch(patch_url, json={"assigned_to_id": tenant.id}, headers=staff.headers)
    assert res.status_code == 422
    res = await client.patch(
        patch_url, json={"assigned_to_id": staff.id, "status": "in_progress"}, headers=staff.headers
    )
    assert res.json()["assigned_to_name"] == "Md. Karim Uddin"
    assert res.json()["resolved_at"] is None

    res = await client.patch(patch_url, json={"status": "resolved"}, headers=staff.headers)
    assert res.json()["resolved_at"] is not None
    res = await client.patch(patch_url, json={"status": "open"}, headers=staff.headers)
    assert res.json()["resolved_at"] is None

    # tenants only see their own requests; others' -> 404
    other = await make_user("tenant")
    assert (await client.get(patch_url, headers=other.headers)).status_code == 404
    mine = (await client.get("/maintenance", headers=tenant.headers)).json()
    assert {r["reported_by_id"] for r in mine} == {tenant.id}

    # staff cannot delete, admin can
    assert (await client.delete(patch_url, headers=staff.headers)).status_code == 403
    assert (await client.delete(patch_url, headers=admin.headers)).status_code == 204
