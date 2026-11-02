import asyncio

from museai.services.tasks import TaskManager, TaskStatus


def _render(seconds: float):
    async def runner(task, progress):
        await asyncio.sleep(seconds)
        return {"url": "done"}

    return runner


async def test_shutdown_lets_running_jobs_finish_within_grace(tmp_path):
    tasks = TaskManager(tmp_path / "tasks.json")
    quick = tasks.submit("video", {}, _render(0.05))
    slow = tasks.submit("video", {}, _render(5))
    await tasks.shutdown(grace=0.3)
    assert quick.status == TaskStatus.SUCCEEDED
    assert slow.status == TaskStatus.FAILED and slow.error["code"] == "interrupted"
    reloaded = TaskManager(tmp_path / "tasks.json")
    await reloaded.load()
    assert reloaded.get(quick.id).status == TaskStatus.SUCCEEDED
