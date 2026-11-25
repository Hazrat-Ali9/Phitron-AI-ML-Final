"""Step 3 check: application errors become JSON with the right status, never a traceback."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    UnprocessableError,
)
from app.main import create_app


class Body(BaseModel):
    name: str = Field(min_length=2)


@pytest.fixture(scope="module")
def client() -> TestClient:
    app: FastAPI = create_app()

    @app.get("/boom/not-found")
    async def not_found() -> None:
        raise NotFoundError("Flat not found")

    @app.get("/boom/conflict")
    async def conflict() -> None:
        raise ConflictError("Flat 2A already exists in this building")

    @app.get("/boom/unauthorized")
    async def unauthorized() -> None:
        raise UnauthorizedError()

    @app.get("/boom/forbidden")
    async def forbidden() -> None:
        raise ForbiddenError()

    @app.get("/boom/unprocessable")
    async def unprocessable() -> None:
        raise UnprocessableError("tenant_id", "User is not a tenant")

    @app.post("/boom/validate")
    async def validate(body: Body) -> Body:
        return body

    @app.get("/boom/crash")
    async def crash() -> None:
        raise RuntimeError("secret internal detail")

    return TestClient(app, raise_server_exceptions=False)


def test_not_found_is_json_404(client: TestClient) -> None:
    res = client.get("/boom/not-found")
    assert res.status_code == 404
    assert res.json() == {"detail": "Flat not found", "code": "not_found"}


def test_conflict_is_409(client: TestClient) -> None:
    res = client.get("/boom/conflict")
    assert res.status_code == 409
    assert res.json()["code"] == "conflict"


def test_unauthorized_sets_www_authenticate(client: TestClient) -> None:
    res = client.get("/boom/unauthorized")
    assert res.status_code == 401
    assert res.headers["www-authenticate"] == "Bearer"


def test_forbidden_is_403(client: TestClient) -> None:
    assert client.get("/boom/forbidden").status_code == 403


def test_unprocessable_uses_field_format(client: TestClient) -> None:
    res = client.get("/boom/unprocessable")
    assert res.status_code == 422
    assert res.json()["detail"][0]["loc"] == ["body", "tenant_id"]


def test_request_validation_keeps_fastapi_format(client: TestClient) -> None:
    res = client.post("/boom/validate", json={"name": "x"})
    assert res.status_code == 422
    assert res.json()["detail"][0]["loc"] == ["body", "name"]


def test_unhandled_error_hides_details(client: TestClient) -> None:
    res = client.get("/boom/crash")
    assert res.status_code == 500
    assert res.json() == {"detail": "Internal server error", "code": "internal_error"}
    assert "secret" not in res.text
