import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models as _models  # noqa: F401  (registers every ORM model up front)
from app.core.config import get_settings
from app.core.database import engine
from app.core.handlers import register_exception_handlers
from app.mcp.http import mount_mcp
from app.mcp.server import mcp
from app.modules.auth.controllers import router as auth_router
from app.modules.buildings.controllers import router as buildings_router
from app.modules.chat.controllers import router as chat_router
from app.modules.flats.controllers import router as flats_router
from app.modules.health.controllers import router as health_router
from app.modules.knowledge.controllers import router as knowledge_router
from app.modules.leases.controllers import router as leases_router
from app.modules.maintenance.controllers import router as maintenance_router
from app.modules.payments.controllers import router as payments_router
from app.modules.users.controllers import router as users_router

# Fails fast with a clear error if a required setting is missing.
settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # The MCP session manager must be running before /mcp can serve any request.
    async with mcp.session_manager.run():
        yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title="BariBhara API",
        description="Rent, flat, tenant and maintenance management for small Dhaka landlords.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    routers = (
        health_router,
        auth_router,
        users_router,
        buildings_router,
        flats_router,
        leases_router,
        payments_router,
        maintenance_router,
        chat_router,
        knowledge_router,
    )
    for router in routers:
        app.include_router(router, prefix=settings.API_V1_PREFIX)

    mount_mcp(app, settings)

    return app


app = create_app()
