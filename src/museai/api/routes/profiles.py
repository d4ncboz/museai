"""Browser profiles: the /profiles page, its data routes, and the agent API under /v1/profiles."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ...errors import InvalidRequest
from ...services import profiles as bh
from ...services.container import Services
from ...upstream import muse
from ..deps import get_services, require_api_key
from .dashboard import _local_or_admin

router = APIRouter(tags=["profiles"])

_PAGE = Path(__file__).resolve().parent.parent / "static" / "profiles.html"
_LOCAL = [Depends(_local_or_admin)]


def _store(svc: Services = Depends(get_services)) -> bh.ProfileStore:
    return bh.ProfileStore(svc.settings.data_dir / "profiles")


class ProfileUpdate(BaseModel):
    label: str = Field("", max_length=100)
    logged_in: bool = False
    verified: bool = False


class LaunchRequest(BaseModel):
    url: str = muse.SITE


async def _listing(store: bh.ProfileStore) -> list[dict]:
    ports = await bh.running_ports()
    return [
        {
            **p.model_dump(),
            "running": p.name in ports,
            "cdp_url": f"http://127.0.0.1:{ports[p.name]}" if p.name in ports else None,
        }
        for p in store.all()
    ]


async def _launch(store: bh.ProfileStore, name: str, url: str) -> dict:
    profile = store.get(name)
    await bh.launch(name, url, profile.label or name)
    port = (await bh.running_ports()).get(name)
    cdp = f"http://127.0.0.1:{port}" if port else None
    # The env is what browser-harness needs to drive this profile's browser.
    return {
        "name": name,
        "running": True,
        "cdp_url": cdp,
        "env": {"BU_NAME": name, "BU_CDP_URL": cdp},
    }


async def _stop(store: bh.ProfileStore, name: str) -> dict:
    store.get(name)
    await bh.stop(name)
    return {"name": name, "running": False}


# Page and its data (local or admin key, like /dashboard).


@router.get("/profiles", include_in_schema=False)
async def profiles_page() -> FileResponse:
    return FileResponse(_PAGE, media_type="text/html", headers={"Cache-Control": "no-cache"})


@router.get("/profiles/data", include_in_schema=False, dependencies=_LOCAL)
async def page_list(store: bh.ProfileStore = Depends(_store)) -> dict:
    return {"profiles": await _listing(store)}


@router.post("/profiles/data", include_in_schema=False, dependencies=_LOCAL)
async def page_create(body: bh.Profile, store: bh.ProfileStore = Depends(_store)) -> dict:
    if store.exists(body.name):
        raise InvalidRequest(f"profile '{body.name}' already exists")
    store.save(body)
    return body.model_dump()


@router.put("/profiles/data/{name}", include_in_schema=False, dependencies=_LOCAL)
async def page_update(
    name: str, body: ProfileUpdate, store: bh.ProfileStore = Depends(_store)
) -> dict:
    profile = store.get(name).model_copy(update=body.model_dump())
    store.save(profile)
    return profile.model_dump()


@router.delete("/profiles/data/{name}", include_in_schema=False, dependencies=_LOCAL)
async def page_delete(name: str, store: bh.ProfileStore = Depends(_store)) -> dict:
    """Stop the browser and delete the JSON file; the browser profile folder stays on disk."""
    store.get(name)
    if name in await bh.running_ports():
        await bh.stop(name)
    store.delete(name)
    return {"name": name, "deleted": True}


@router.post("/profiles/{name}/launch", include_in_schema=False, dependencies=_LOCAL)
async def page_launch(name: str, store: bh.ProfileStore = Depends(_store)) -> dict:
    return await _launch(store, name, muse.SITE)


@router.post("/profiles/{name}/stop", include_in_schema=False, dependencies=_LOCAL)
async def page_stop(name: str, store: bh.ProfileStore = Depends(_store)) -> dict:
    return await _stop(store, name)


# Agent API (API key). Launch returns BU_NAME/BU_CDP_URL so an agent can drive the browser.


@router.get("/v1/profiles", dependencies=[Depends(require_api_key)])
async def agent_list(store: bh.ProfileStore = Depends(_store)) -> dict:
    """List profiles with their status and, when running, their CDP URL."""
    return {"profiles": await _listing(store)}


@router.post("/v1/profiles/{name}/launch", dependencies=[Depends(require_api_key)])
async def agent_launch(
    name: str, body: LaunchRequest | None = None, store: bh.ProfileStore = Depends(_store)
) -> dict:
    """Start a profile's browser at ``url`` (default muse.ai). An already running one is reused."""
    return await _launch(store, name, (body or LaunchRequest()).url)


@router.post("/v1/profiles/{name}/stop", dependencies=[Depends(require_api_key)])
async def agent_stop(name: str, store: bh.ProfileStore = Depends(_store)) -> dict:
    """Close a profile's browser and its browser-harness daemon."""
    return await _stop(store, name)
