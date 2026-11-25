"""Step 5 checks: CRUD, duplicate flat -> 409, tenant write -> 403, filters, 404s."""

import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import AuthedUser, MakeUser


@pytest.fixture(scope="module")
async def admin(make_user: MakeUser) -> AuthedUser:
    return await make_user("admin", "Abdur Rahman")


@pytest.fixture(scope="module")
async def tenant(make_user: MakeUser) -> AuthedUser:
    return await make_user("tenant")


async def create_building(client: AsyncClient, admin: AuthedUser, **overrides: object) -> dict:
    data = {
        "name": f"Test Villa {uuid.uuid4().hex[:6]}",
        "address": "House 12, Road 5, Mirpur 10, Dhaka 1216",
        "area": "Mirpur",
        "total_floors": 6,
        **overrides,
    }
    res = await client.post("/buildings", json=data, headers=admin.headers)
    assert res.status_code == 201, res.text
    return res.json()


def flat_body(building_id: int, **overrides: object) -> dict:
    return {
        "building_id": building_id,
        "flat_no": "3b",
        "floor": 3,
        "bedrooms": 2,
        "bathrooms": 2,
        "size_sqft": 950,
        "monthly_rent": 18000,
        "service_charge": 2000,
        **overrides,
    }


async def test_building_crud(client: AsyncClient, admin: AuthedUser) -> None:
    building = await create_building(client, admin)
    bid = building["id"]

    res = await client.get(f"/buildings/{bid}", headers=admin.headers)
    assert res.status_code == 200 and res.json()["name"] == building["name"]

    res = await client.patch(f"/buildings/{bid}", json={"total_floors": 7}, headers=admin.headers)
    assert res.status_code == 200 and res.json()["total_floors"] == 7

    res = await client.patch(f"/buildings/{bid}", json={"name": None}, headers=admin.headers)
    assert res.status_code == 422

    assert (await client.delete(f"/buildings/{bid}", headers=admin.headers)).status_code == 204
    assert (await client.get(f"/buildings/{bid}", headers=admin.headers)).status_code == 404


async def test_duplicate_building_name_is_409(client: AsyncClient, admin: AuthedUser) -> None:
    building = await create_building(client, admin)
    res = await client.post(
        "/buildings",
        json={**building, "name": building["name"].upper()},
        headers=admin.headers,
    )
    assert res.status_code == 409


async def test_tenant_cannot_write(
    client: AsyncClient, admin: AuthedUser, tenant: AuthedUser
) -> None:
    building = await create_building(client, admin)
    res = await client.post(
        "/buildings", json={**building, "name": "Tenant Tower"}, headers=tenant.headers
    )
    assert res.status_code == 403
    res = await client.post("/flats", json=flat_body(building["id"]), headers=tenant.headers)
    assert res.status_code == 403
    # ...but can read
    assert (await client.get("/flats", headers=tenant.headers)).status_code == 200


async def test_flat_crud_and_duplicate(client: AsyncClient, admin: AuthedUser) -> None:
    building = await create_building(client, admin)
    res = await client.post("/flats", json=flat_body(building["id"]), headers=admin.headers)
    assert res.status_code == 201, res.text
    flat = res.json()
    assert flat["flat_no"] == "3B"
    assert flat["building_name"] == building["name"]
    assert flat["area"] == "Mirpur"
    assert flat["status"] == "vacant"

    dup = await client.post("/flats", json=flat_body(building["id"]), headers=admin.headers)
    assert dup.status_code == 409
    assert "3B" in dup.json()["detail"]

    res = await client.patch(
        f"/flats/{flat['id']}", json={"monthly_rent": 19000}, headers=admin.headers
    )
    assert res.status_code == 200 and res.json()["monthly_rent"] == 19000

    # building with flats cannot be deleted
    res = await client.delete(f"/buildings/{building['id']}", headers=admin.headers)
    assert res.status_code == 409

    assert (await client.delete(f"/flats/{flat['id']}", headers=admin.headers)).status_code == 204
    assert (await client.get(f"/flats/{flat['id']}", headers=admin.headers)).status_code == 404


async def test_flat_validation(client: AsyncClient, admin: AuthedUser) -> None:
    building = await create_building(client, admin, total_floors=4)
    res = await client.post(
        "/flats", json=flat_body(building["id"], floor=9), headers=admin.headers
    )
    assert res.status_code == 422
    assert res.json()["detail"][0]["loc"] == ["body", "floor"]

    res = await client.post(
        "/flats", json=flat_body(building["id"], bedrooms=0), headers=admin.headers
    )
    assert res.status_code == 422

    res = await client.post("/flats", json=flat_body(999_999), headers=admin.headers)
    assert res.status_code == 404


async def test_flat_move_to_another_building(client: AsyncClient, admin: AuthedUser) -> None:
    a = await create_building(client, admin)
    b = await create_building(client, admin, area="Uttara")
    flat = (await client.post("/flats", json=flat_body(a["id"]), headers=admin.headers)).json()

    res = await client.patch(
        f"/flats/{flat['id']}", json={"building_id": b["id"]}, headers=admin.headers
    )
    assert res.status_code == 200
    assert res.json()["building_name"] == b["name"]
    assert res.json()["area"] == "Uttara"


async def test_flat_filters(client: AsyncClient, admin: AuthedUser) -> None:
    building = await create_building(client, admin, area="Bashundhara")
    bid = building["id"]
    for flat_no, beds, rent, status in [
        ("1A", 2, 15000, "vacant"),
        ("1B", 3, 25000, "maintenance"),
        ("2A", 3, 30000, "vacant"),
    ]:
        res = await client.post(
            "/flats",
            json=flat_body(
                bid,
                flat_no=flat_no,
                floor=int(flat_no[0]),
                bedrooms=beds,
                monthly_rent=rent,
                status=status,
            ),
            headers=admin.headers,
        )
        assert res.status_code == 201, res.text

    async def flat_nos(**params: object) -> list[str]:
        res = await client.get(
            "/flats", params={"building_id": bid, **params}, headers=admin.headers
        )
        assert res.status_code == 200, res.text
        return [f["flat_no"] for f in res.json()]

    assert await flat_nos() == ["1A", "1B", "2A"]
    assert await flat_nos(status="vacant") == ["1A", "2A"]
    assert await flat_nos(bedrooms=3) == ["1B", "2A"]
    assert await flat_nos(max_rent=25000) == ["1A", "1B"]
    assert await flat_nos(min_rent=20000, status="vacant") == ["2A"]
    assert await flat_nos(q="2a") == ["2A"]
    assert await flat_nos(area="bashundhara") == ["1A", "1B", "2A"]
    assert await flat_nos(limit=1, offset=1) == ["1B"]

    res = await client.get("/flats", params={"limit": 500}, headers=admin.headers)
    assert res.status_code == 422
