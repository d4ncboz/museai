"""Runtime configuration, loaded from environment variables (prefix ``MUSE2API_``) and ``.env``."""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DriverName = Literal["mock", "browser", "http"]
PoolStrategyName = Literal["round_robin", "lru", "affinity"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MUSE2API_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- server ---
    host: str = "127.0.0.1"
    port: int = 18610
    log_level: str = "INFO"
    public_base: str = Field(
        default="",
        description="Externally reachable base URL used when building media links. "
        "Empty means derive from the incoming request.",
    )

    # --- auth ---
    api_key: str = Field(default="", description="Bearer key for /v1/*. Auto-generated if empty.")
    admin_key: str = Field(
        default="", description="Bearer key for /admin/*. Falls back to api_key."
    )

    # --- storage ---
    data_dir: Path = Path("data")
    # Finished videos waiting to be posted to social media (the dashboard's posting queue).
    post_dir: Path = Path.home() / "Desktop"
    # Give each delivered video its own numbered folder there (video, thumbnails, captions.txt), in
    # posting order, so one folder holds all a post needs and deleting it clears the post.
    post_folders: bool = True
    # Push "ready to post" to phones that installed the dashboard and turned notifications on.
    push_enabled: bool = True
    # Write the per-platform captions a queued video is missing through muse chat.
    auto_captions: bool = True
    # Post queued videos by the auto-post rules when their slot comes (dashboard "Auto-post").
    autopost_enabled: bool = True
    # Dry run: every platform posts through the mock driver (nothing leaves the machine).
    autopost_mock: bool = False
    autopost_interval: float = 60.0
    # Developer apps the user creates for auto-posting (docs/auto-post.md). Never logged or shown.
    google_client_id: str = ""
    google_client_secret: str = ""
    meta_app_id: str = ""
    meta_app_secret: str = ""
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""

    # --- upstream driver ---
    driver: DriverName = "mock"
    site_url: str = "https://muse.ai"

    # browser driver
    chromium_path: str = ""
    cdp_port: int = 19210
    headless: bool = True
    browser_proxy: str = Field(
        default="",
        description="Proxy for the browser only, e.g. socks5://127.0.0.1:10808 or http://10.144.1.10:8080. "
        "Python's own calls (session renewal) follow http_proxy/https_proxy instead.",
    )
    browser_profile_dir: Path | None = None
    page_ready_timeout: float = 45.0

    # --- timeouts (seconds) ---
    chat_timeout: float = 300.0
    first_token_timeout: float = 45.0
    image_timeout: float = 240.0
    video_timeout: float = 1500.0  # 30-40 s videos often take 10+ min
    # A clip of known length gets base + per_second * duration (capped by video_timeout):
    # 6-10 s clips finish in 2-4 min (p95 638 s for 10 s), so a stuck one fails over after
    # ~16 min instead of holding its account for 25.
    video_timeout_base: float = 360.0
    video_timeout_per_second: float = 60.0

    # --- account pool ---
    pool_strategy: PoolStrategyName = "affinity"
    pool_acquire_timeout: float = 60.0
    # How long an image/video job waits for a free account (up to account_max_concurrency jobs per account).
    # 0 = queue until one is free.
    media_queue_timeout: float = 0.0
    account_max_concurrency: int = 6
    account_cooldown: float = 120.0
    max_failover: int = 2
    # On stop/restart, how long running image/video jobs may still finish before they are cancelled.
    shutdown_grace: float = 900.0

    # --- keepalive (session renewal) ---
    keepalive_enabled: bool = False
    keepalive_interval: float = 6 * 3600

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media"

    @property
    def posts_file(self) -> Path:
        return self.data_dir / "posts.json"

    @property
    def accounts_file(self) -> Path:
        return self.data_dir / "accounts.json"

    @property
    def tasks_file(self) -> Path:
        return self.data_dir / "tasks.json"

    @property
    def key_file(self) -> Path:
        return self.data_dir / "api_key"

    @property
    def profile_dir(self) -> Path:
        return self.browser_profile_dir or (self.data_dir / "browser-profile")

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.media_dir):
            d.mkdir(parents=True, exist_ok=True)

    def resolve_api_key(self) -> str:
        """Return the configured key, or load/generate a persistent one under ``data_dir``."""
        if self.api_key:
            return self.api_key
        self.ensure_dirs()
        if self.key_file.is_file():
            key = self.key_file.read_text(encoding="utf-8").strip()
            if key:
                self.api_key = key
                return key
        key = "m2a-" + secrets.token_urlsafe(24)
        self.key_file.write_text(key + "\n", encoding="utf-8")
        self.key_file.chmod(0o600)
        self.api_key = key
        return key

    @property
    def effective_admin_key(self) -> str:
        return self.admin_key or self.api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
