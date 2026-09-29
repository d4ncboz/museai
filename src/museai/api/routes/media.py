from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from ...services.container import Services
from ..deps import get_services

# Media URLs are unguessable (random names) and must be embeddable in clients that
# cannot send auth headers, so this route is intentionally public.
router = APIRouter(tags=["media"])


@router.get("/v1/media/{name}")
async def get_media(name: str, svc: Services = Depends(get_services)) -> FileResponse:
    path = svc.media.path_of(name)
    return FileResponse(path, media_type=svc.media.mime_of(name),
                        headers={"Cache-Control": "public, max-age=86400"})
