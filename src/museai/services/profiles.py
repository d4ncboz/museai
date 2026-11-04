"""Browser profiles: one JSON file per profile, browsers run through the ``bh-profile`` CLI.

``<data_dir>/profiles/<name>.json`` holds what the user records by hand (login and account
status). Whether a profile runs, and on which debug port, always comes from ``bh-profile``.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field

from ..errors import InvalidRequest, Muse2APIError, NotFound

_NAME = re.compile(r"[A-Za-z0-9_-]{1,64}")


class Profile(BaseModel):
    name: str  # id: also the bh-profile folder name and BU_NAME, fixed once created
    label: str = Field("", max_length=100)  # display name shown in the table
    logged_in: bool = False
    verified: bool = False


def check_name(name: str) -> str:
    if not _NAME.fullmatch(name) or name == "default":
        raise InvalidRequest("profile name must match [A-Za-z0-9_-]{1,64} and not be 'default'")
    return name


class ProfileStore:
    def __init__(self, folder: Path) -> None:
        self.folder = folder

    def _path(self, name: str) -> Path:
        return self.folder / f"{check_name(name)}.json"

    def all(self) -> list[Profile]:
        if not self.folder.is_dir():
            return []
        out = []
        for f in sorted(self.folder.glob("*.json")):
            try:
                out.append(Profile.model_validate_json(f.read_text(encoding="utf-8")))
            except ValueError:
                continue  # a hand-edited file that no longer parses is skipped, not fatal
        return out

    def get(self, name: str) -> Profile:
        path = self._path(name)
        if not path.is_file():
            raise NotFound(f"profile '{name}' not found")
        return Profile.model_validate_json(path.read_text(encoding="utf-8"))

    def exists(self, name: str) -> bool:
        return self._path(name).is_file()

    def save(self, profile: Profile) -> None:
        path = self._path(profile.name)
        self.folder.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.folder, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(profile.model_dump(), f, indent=2)
        os.replace(tmp, path)

    def delete(self, name: str) -> None:
        self._path(name).unlink(missing_ok=True)


async def bh_profile(*args: str) -> str:
    """Run ``bh-profile`` and return its stdout; a non-zero exit becomes a 500 with its stderr."""
    exe = shutil.which("bh-profile")
    if exe is None:
        raise Muse2APIError("bh-profile is not installed; run browser-harness-setup/install.sh")
    # Plain subprocess in a thread, not asyncio's: uvloop leaks the output pipes into the
    # browser that `bh-profile start` leaves running, so reading them never reaches EOF.
    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            [exe, *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        raise Muse2APIError(f"bh-profile {args[0]} timed out") from None
    if proc.returncode != 0:
        raise Muse2APIError(proc.stderr.strip() or f"bh-profile {args[0]} failed")
    return proc.stdout


async def running_ports() -> dict[str, int]:
    """Name -> debug port of every running profile."""
    # `bh-profile list` prints "NAME PORT STATE" rows after a header line.
    rows = [line.split() for line in (await bh_profile("list")).splitlines()[1:]]
    return {r[0]: int(r[1]) for r in rows if len(r) == 3 and r[2] == "running" and r[1].isdigit()}


async def launch(name: str, url: str, label: str) -> None:
    """Start the browser; ``label`` becomes Chromium's profile name (applied while it is closed)."""
    if not url.startswith(("https://", "http://")):
        raise InvalidRequest("url must start with http:// or https://")
    await bh_profile("start", check_name(name), url, "--label", label)


async def stop(name: str) -> None:
    await bh_profile("stop", check_name(name))
