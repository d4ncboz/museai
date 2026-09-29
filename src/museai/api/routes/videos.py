from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ...core.media import load_image_ref
from ...core.models import resolve_model
from ...drivers.base import InputImage, VideoRequest
from ...errors import NotFound
from ...services.container import Services
from ...services.tasks import Task
from ..deps import get_services, public_base, require_api_key
from ..schemas import VideoCreateRequest

router = APIRouter(tags=["videos"], dependencies=[Depends(require_api_key)])


def _task_view(task: Task) -> dict:
    return {
        "id": task.id,
        "object": "video",
        "status": task.status.value,
        "progress": task.progress,
        "created_at": int(task.created_at),
        "model": task.request.get("model"),
        "result": task.result,
        "error": task.error,
    }


@router.post("/v1/videos")
async def create_video(body: VideoCreateRequest, request: Request,
                       svc: Services = Depends(get_services)) -> dict:
    spec = resolve_model(body.model, "video")
    frame_ref = body.image or body.input_reference
    first_frame = InputImage(*(await load_image_ref(frame_ref))) if frame_ref else None
    base = public_base(request)

    async def runner(progress) -> dict:
        req = VideoRequest(prompt=body.prompt, model=spec.id, size=body.size,
                           duration=body.duration or body.seconds, first_frame=first_frame,
                           timeout=svc.settings.video_timeout, on_progress=progress)
        result = await svc.gateway.generate_video(req)
        name = svc.media.save(result.data, result.mime, prefix="vid")
        return {"url": f"{base}/v1/media/{name}", "mime": result.mime,
                "width": result.width, "height": result.height}

    request_meta = {"model": spec.id, "prompt": body.prompt, "size": body.size,
                    "duration": body.duration or body.seconds, "has_first_frame": bool(first_frame)}
    task = svc.tasks.submit("video", request_meta, runner)
    return _task_view(task)


@router.get("/v1/videos/{task_id}")
async def get_video(task_id: str, svc: Services = Depends(get_services)) -> dict:
    task = svc.tasks.get(task_id)
    if task is None or task.kind != "video":
        raise NotFound(f"video task '{task_id}' not found")
    return _task_view(task)
