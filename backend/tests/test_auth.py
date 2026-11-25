"""Step 4 checks: register 201, identical login errors, 401 without/with expired token, roles."""

from datetime import timedelta

from httpx import AsyncClient

from app.core.security import create_access_token
from tests.conftest import MakeUser


async def test_register_creates_tenant(client: AsyncClient) -> None:
    res = await client.post(
        "/auth/register",
        json={
            "full_name": "Nadia Rahman",
            "email": "Nadia.Rahman@Example.com",
            "phone": "01711-482913",
            "password": "secret123",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["role"] == "tenant"
    assert body["email"] == "nadia.rahman@example.com"
    assert body["phone"] == "01711482913"
    assert "password" not in res.text and "password_hash" not in body


async def test_register_duplicate_email_is_409(client: AsyncClient) -> None:
    data = {"full_name": "Dup User", "email": "dup@example.com", "password": "secret123"}
    assert (await client.post("/auth/register", json=data)).status_code == 201
    data["email"] = "DUP@example.com"
    assert (await client.post("/auth/register", json=data)).status_code == 409


async def test_register_rejects_bad_phone_and_short_password(client: AsyncClient) -> None:
    res = await client.post(
        "/auth/register",
        json={"full_name": "X Y", "email": "x@example.com", "phone": "12345", "password": "short"},
    )
    assert res.status_code == 422
    fields = {err["loc"][-1] for err in res.json()["detail"]}
    assert {"phone", "password"} <= fields


async def test_login_errors_are_identical(client: AsyncClient, make_user: MakeUser) -> None:
    user = await make_user("tenant")
    wrong_email = await client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": user.password}
    )
    wrong_password = await client.post(
        "/auth/login", json={"email": user.email, "password": "not-the-password"}
    )
    assert wrong_email.status_code == wrong_password.status_code == 401
    assert wrong_email.json() == wrong_password.json()


async def test_login_then_me(client: AsyncClient, make_user: MakeUser) -> None:
    user = await make_user("staff")
    res = await client.post("/auth/login", json={"email": user.email, "password": user.password})
    assert res.status_code == 200
    token = res.json()
    assert token["token_type"] == "bearer" and token["expires_in"] > 0

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert me.status_code == 200
    assert me.json()["role"] == "staff"


async def test_me_without_token_is_401(client: AsyncClient) -> None:
    res = await client.get("/auth/me")
    assert res.status_code == 401
    assert res.headers["www-authenticate"] == "Bearer"


async def test_me_with_expired_token_is_401(client: AsyncClient, make_user: MakeUser) -> None:
    user = await make_user("tenant")
    expired = create_access_token(user.id, expires_delta=timedelta(seconds=-5)).token
    res = await client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Token has expired"


async def test_me_with_garbage_token_is_401(client: AsyncClient) -> None:
    res = await client.get("/auth/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert res.status_code == 401


async def test_users_list_requires_admin_or_staff(client: AsyncClient, make_user: MakeUser) -> None:
    tenant = await make_user("tenant")
    admin = await make_user("admin")
    assert (await client.get("/users", headers=tenant.headers)).status_code == 403

    res = await client.get("/users", params={"role": "admin"}, headers=admin.headers)
    assert res.status_code == 200
    assert all(u["role"] == "admin" for u in res.json())
    assert any(u["id"] == admin.id for u in res.json())
