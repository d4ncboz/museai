from fastapi import APIRouter

from . import (
    admin,
    autopost,
    campaign,
    chat,
    dashboard,
    health,
    images,
    media,
    models,
    posting,
    responses,
    videos,
)


def build_router() -> APIRouter:
    router = APIRouter()
    for module in (health, models, chat, responses, images, videos, media, admin, dashboard, posting, autopost, campaign):
        router.include_router(module.router)
    router.include_router(autopost.callback_router)
    return router
