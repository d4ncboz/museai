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

Runner = Callable[["Task", Callable[[int], None]], Awaitable[dict[str, Any]]]


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
    # Account the job runs on; earlier ones in ``attempts`` failed over.
    account_id: str | None = None
    account_label: str | None = None
    attempts: list[str] = Field(default_factory=list)
    # When the current attempt got its account; before that the job waits in the queue.
    started_at: float | None = None
    # Identical in-flight submissions share one task instead of rendering again.
    dedupe_key: str | None = None
    # Client session (X-Muse-Session). Free accounts go to the waiting session that holds
    # the fewest (see AccountPool), so one client uses idle accounts but never starves others.
    session: str | None = None

    def assign(self, account_id: str, label: str) -> None:
        self.account_id, self.account_label = account_id, label
        self.attempts.append(account_id)
        self.started_at = self.updated_at = time.time()

    @property
    def finished(self) -> bool:
        return self.status in (TaskStatus.SUCCEEDED, TaskStatus.FAILED, TaskStatus.CANCELLED)


class TaskManager:
    def __init__(self, path: Path, *, max_kept: int = 500) -> None:
        self.path = path
        self.max_kept = max_kept
        self._tasks: dict[str, Task] = {}
        self._running: dict[str, asyncio.Task] = {}
        self._stopping = False

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

    def submit(
        self,
        kind: str,
        request: dict[str, Any],
        runner: Runner,
        *,
        dedupe_key: str | None = None,
        session: str | None = None,
        reuse: Callable[[Task], bool] | None = None,
    ) -> Task:
        if dedupe_key:
            for task_id in self._running:
                same = self._tasks.get(task_id)
                if same and same.dedupe_key == dedupe_key and not same.finished:
                    log.info("duplicate %s request joined in-flight %s", kind, same.id)
                    return same
            # The same request sent again after it finished renders the same thing again
            # on another account; hand back the finished result unless ``reuse`` says no.
            done = [t for t in self._tasks.values() if t.dedupe_key == dedupe_key
                    and t.status == TaskStatus.SUCCEEDED]
            if done and reuse:
                last = max(done, key=lambda t: t.updated_at)
                if reuse(last):
                    log.info("duplicate %s request reused finished %s", kind, last.id)
                    return last
        task = Task(kind=kind, request=request, dedupe_key=dedupe_key, session=session)
        self._tasks[task.id] = task
        self._persist()
        self._running[task.id] = asyncio.create_task(self._run(task, runner))
        return task

    async def _run(self, task: Task, runner: Runner) -> None:
        def progress(p: int) -> None:
            task.progress = max(task.progress, min(99, int(p)))
            task.updated_at = time.time()

        try:
            task.status = TaskStatus.RUNNING
            task.result = await runner(task, progress)
            task.status = TaskStatus.SUCCEEDED
            task.progress = 100
        except asyncio.CancelledError:
            if self._stopping:
                # Same code load() gives jobs a crash left behind: clients resubmit on it.
                task.status = TaskStatus.FAILED
                task.error = {"message": "interrupted by server restart", "code": "interrupted"}
            else:
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

    async def shutdown(self, grace: float = 0) -> None:
        """Stop the running jobs. With ``grace``, first let them finish for up to that many seconds: the
        server no longer listens by then, and clients keep polling until it is back, so a restart loses no
        render. Jobs still running after it are cancelled ("interrupted": clients resubmit)."""
        if grace > 0 and self._running:
            log.info("waiting up to %.0fs for %d running job(s) to finish", grace, len(self._running))
            await asyncio.wait(list(self._running.values()), timeout=grace)
        self._stopping = True
        for t in list(self._running.values()):
            t.cancel()
        if self._running:
            await asyncio.gather(*self._running.values(), return_exceptions=True)
