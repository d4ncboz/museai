"""Background task manager for long-running jobs (video generation, batch images, ...)."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ..errors import Muse2APIError

log = logging.getLogger(__name__)

Runner = Callable[[Callable[[int], None]], Awaitable[dict[str, Any]]]


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: "task_" + uuid.uuid4().hex[:16])
    kind: str
    status: TaskStatus = TaskStatus.QUEUED
    progress: int = 0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    request: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    @property
    def finished(self) -> bool:
        return self.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED)


class TaskManager:
    def __init__(self, path: Path, *, max_kept: int = 500) -> None:
        self.path = path
        self.max_kept = max_kept
        self._tasks: dict[str, Task] = {}
        self._running: dict[str, asyncio.Task] = {}

    async def load(self) -> None:
        if not self.path.is_file():
            return
        try:
            items = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        except json.JSONDecodeError:
            log.warning("tasks file corrupted, starting empty")
            return
        for item in items:
            task = Task.model_validate(item)
            if not task.finished:
                task.status = TaskStatus.FAILED
                task.error = {"message": "interrupted by server restart", "code": "interrupted"}
            self._tasks[task.id] = task

    def _persist(self) -> None:
        tasks = sorted(self._tasks.values(), key=lambda t: t.created_at)[-self.max_kept :]
        self._tasks = {t.id: t for t in tasks}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps([t.model_dump(mode="json") for t in tasks], ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def get(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def list(self, limit: int = 100) -> list[Task]:
        return sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)[:limit]

    def submit(self, kind: str, request: dict[str, Any], runner: Runner) -> Task:
        task = Task(kind=kind, request=request)
        self._tasks[task.id] = task
        self._persist()
        self._running[task.id] = asyncio.create_task(self._run(task, runner))
        return task

    async def _run(self, task: Task, runner: Runner) -> None:
        def progress(p: int) -> None:
            task.progress = max(task.progress, min(99, int(p)))
            task.updated_at = time.time()

        task.status = TaskStatus.RUNNING
        try:
            task.result = await runner(progress)
            task.status = TaskStatus.SUCCEEDED
            task.progress = 100
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
        except Muse2APIError as exc:
            task.status = TaskStatus.FAILED
            task.error = {"message": exc.message, "code": exc.code}
        except Exception as exc:  # noqa: BLE001
            log.exception("task %s crashed", task.id)
            task.status = TaskStatus.FAILED
            task.error = {"message": str(exc), "code": "internal_error"}
        finally:
            task.updated_at = time.time()
            self._running.pop(task.id, None)
            self._persist()

    async def cancel(self, task_id: str) -> bool:
        running = self._running.get(task_id)
        if running is None:
            return False
        running.cancel()
        return True

    async def shutdown(self) -> None:
        for t in list(self._running.values()):
            t.cancel()
        if self._running:
            await asyncio.gather(*self._running.values(), return_exceptions=True)
