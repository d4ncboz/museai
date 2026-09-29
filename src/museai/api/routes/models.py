import time

from fastapi import APIRouter, Depends

from ...core.models import ALIASES, MODELS
from ..deps import require_api_key

router = APIRouter(tags=["models"], dependencies=[Depends(require_api_key)])

_CREATED = int(time.time())


@router.get("/v1/models")
async def list_models() -> dict:
    data = [
        {"id": m.id, "object": "model", "created": _CREATED, "owned_by": m.owned_by, "kind": m.kind}
        for m in MODELS.values()
    ]
    data += [
        {"id": alias, "object": "model", "created": _CREATED, "owned_by": "muse",
         "kind": MODELS[target].kind, "alias_of": target}
        for alias, target in ALIASES.items()
    ]
    return {"object": "list", "data": data}
