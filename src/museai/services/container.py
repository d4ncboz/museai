"""Service container wired once at startup and stored on ``app.state.services``."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..accounts.pool import AccountPool
from ..accounts.store import JsonAccountStore
from ..config import Settings
from ..core.media import MediaStore
from ..drivers.base import MuseDriver
from ..drivers.registry import create_driver
from .captions import CaptionWriter
from .gateway import Gateway
from .oauth import OAuth
from .publishers import Publisher
from .publishers import build as build_publishers
from .push import Push
from .tasks import TaskManager


@dataclass
class Services:
    settings: Settings
    driver: MuseDriver
    pool: AccountPool
    gateway: Gateway
    tasks: TaskManager
    media: MediaStore
    push: Push
    captions: CaptionWriter
    oauth: OAuth
    publishers: dict[str, Publisher]

    @classmethod
    def build(cls, settings: Settings, driver: MuseDriver | None = None) -> Services:
        settings.ensure_dirs()
        driver = driver or create_driver(settings)
        pool = AccountPool(
            JsonAccountStore(settings.accounts_file),
            strategy=settings.pool_strategy,
            max_concurrency=settings.account_max_concurrency,
            cooldown=settings.account_cooldown,
            acquire_timeout=settings.pool_acquire_timeout,
        )
        gateway = Gateway(
            pool,
            driver,
            max_failover=settings.max_failover,
            media_queue_timeout=settings.media_queue_timeout or math.inf,
            video_deadline=settings.video_job_deadline,
            stuck_video_cooldown=settings.stuck_video_cooldown,
        )
        return cls(
            settings=settings,
            driver=driver,
            pool=pool,
            gateway=gateway,
            tasks=TaskManager(settings.tasks_file),
            media=MediaStore(settings.media_dir),
            push=Push(settings.data_dir, settings.post_dir),
            captions=CaptionWriter(gateway, settings.auto_captions),
            oauth=OAuth(settings),
            publishers=build_publishers(settings.autopost_mock, settings.data_dir),
        )
