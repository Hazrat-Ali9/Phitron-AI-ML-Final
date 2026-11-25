"""Mount the MCP server's streamable-HTTP transport at /mcp inside the FastAPI app."""

import hmac

from fastapi import FastAPI
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import Settings
from app.mcp.server import mcp

MCP_PATH = "/mcp"


class RequireApiKey:
    """If MCP_API_KEY is set, every /mcp request must send it in the X-API-Key header."""

    def __init__(self, app: ASGIApp, api_key: str | None) -> None:
        self.app = app
        self.api_key = api_key

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self.api_key and scope["type"] == "http":
            sent = dict(scope["headers"]).get(b"x-api-key", b"").decode()
            if not hmac.compare_digest(sent, self.api_key):
                response = JSONResponse(
                    {"detail": "Missing or invalid X-API-Key", "code": "unauthorized"},
                    status_code=401,
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def mount_mcp(app: FastAPI, settings: Settings) -> None:
    # The SDK's default DNS-rebinding guard only accepts localhost Host headers, which
    # would reject every request on Render. Locally keep the guard; in production the
    # endpoint is public by design (optionally protected by MCP_API_KEY).
    security = (
        TransportSecuritySettings(enable_dns_rebinding_protection=False)
        if settings.is_production
        else None
    )
    mcp_app = mcp.streamable_http_app(
        streamable_http_path=MCP_PATH,
        stateless_http=True,  # no server-side sessions: survives restarts and free-tier sleep
        json_response=True,
        transport_security=security,
    )
    # A plain Route (not Mount) so /mcp matches exactly without a redirect to /mcp/,
    # and unknown API paths keep FastAPI's JSON 404.
    app.router.routes.append(Route(MCP_PATH, endpoint=RequireApiKey(mcp_app, settings.MCP_API_KEY)))
