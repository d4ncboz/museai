from __future__ import annotations

import base64
import time

from fastapi import APIRouter, Depends, Request

from ...core.models import resolve_model
from ...drivers.base import ImageRequest, MediaResult
from ...errors import FeatureNotImplemented
from ...services.container import Services
from ..deps import get_services, public_base, require_api_key
from ..schemas import ImageGenerationRequest

router = APIRouter(tags=["images"], dependencies=[Depends(require_api_key)])


def _image_item(r: MediaResult, fmt: str, svc: Services, base: str) -> dict:
    item: dict = {"revised_prompt": r.revised_prompt}
    if fmt == "b64_json":
        item["b64_json"] = base64.b64encode(r.data).decode()
    else:
        name = svc.media.save(r.data, r.mime, prefix="img")
        item["url"] = f"{base}/v1/media/{name}"
    return item


@router.post("/v1/images/generations")
async def generate_images(body: ImageGenerationRequest, request: Request,
                          svc: Services = Depends(get_services)) -> dict:
    spec = resolve_model(body.model, "image")
    req = ImageRequest(prompt=body.prompt, model=spec.id, size=body.size, n=body.n,
                       timeout=svc.settings.image_timeout)
    results = await svc.gateway.generate_image(req)
    base = public_base(request)
    return {"created": int(time.time()),
            "data": [_image_item(r, body.response_format, svc, base) for r in results]}


@router.post("/v1/images/edits")
async def edit_images() -> None:
    # TODO(contributors): parse multipart (image[], prompt, size, response_format), load files
    # into ImageRequest.reference_images and reuse generate_images' response shaping.
    raise FeatureNotImplemented("/v1/images/edits is planned")
