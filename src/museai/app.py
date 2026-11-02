"""FastAPI application factory."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import __version__
from .accounts.keepalive import keepalive_loop
from .api.routes import autopost, build_router
from .config import Settings, get_settings
from .drivers.base import MuseDriver
from .errors import Muse2APIError
from .services.container import Services
from .services.push import watch_loop

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

        def captions() -> dict[str, str]:
            try:
                state = json.loads(settings.posts_file.read_text())
            except (FileNotFoundError, json.JSONDecodeError):
                return {}
            return {name: e.get("caption", "") for name, e in state.items()}

        watcher = asyncio.create_task(watch_loop(services.push, captions)) \
            if settings.push_enabled else None
        poster = asyncio.create_task(autopost.loop(services)) if settings.autopost_enabled else None
        log.info("museai %s ready (driver=%s)", __version__, services.driver.name)
        try:
            yield
        finally:
            for loop in (keepalive, watcher, poster):
                if loop:
                    loop.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await loop
            await services.tasks.shutdown(settings.shutdown_grace)
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
