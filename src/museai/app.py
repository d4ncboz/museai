"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import __version__
from .accounts.keepalive import keepalive_loop
from .api.routes import build_router
from .config import Settings, get_settings
from .drivers.base import MuseDriver
from .errors import Muse2APIError
from .services.container import Services

log = logging.getLogger("museai")


def create_app(settings: Settings | None = None, driver: MuseDriver | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.resolve_api_key()
    services = Services.build(settings, driver)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        await services.pool.load()
        await services.tasks.load()
        await services.driver.startup()
        keepalive = None
        if settings.keepalive_enabled and services.driver.capabilities.renew_session:
            keepalive = asyncio.create_task(
                keepalive_loop(services.pool, services.driver, settings.keepalive_interval)
            )
        log.info("museai %s ready (driver=%s)", __version__, services.driver.name)
        try:
            yield
        finally:
            if keepalive:
                keepalive.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await keepalive
            await services.tasks.shutdown()
            await services.driver.shutdown()

    app = FastAPI(title="museai", version=__version__, lifespan=lifespan)
    app.state.services = services

    @app.exception_handler(Muse2APIError)
    async def _muse_error(_: Request, exc: Muse2APIError) -> JSONResponse:
        return JSONResponse(exc.to_body(), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        msg = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        return JSONResponse(
            {"error": {"message": msg, "type": "invalid_request_error", "code": "invalid_request"}},
            status_code=400,
        )

    app.include_router(build_router())
    return app
