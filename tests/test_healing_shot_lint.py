"""healing-video scripts/shot rejects briefs that made muse spill fruit or pour from a lidded teapot."""
import os
import subprocess
from pathlib import Path

import pytest

SHOT = Path(__file__).resolve().parent.parent / ".claude/skills/healing-video/scripts/shot"


def run(brief, tmp_path, **env):
    fake = tmp_path / "muse-video"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    e = {**os.environ, "MUSE_VIDEO": str(fake), **env}
    return subprocess.run(["bash", str(SHOT), brief, str(tmp_path / "o.mp4")], env=e, capture_output=True, text=True)


@pytest.mark.parametrize("brief", [
    "Her hand pours tea from a white teapot into a cup.",
    "A blue kettle pouring hot water into a jug.",
    "She rinses berries in a colander, tossing them gently.",
    "Apples tumble out of the basket onto the grass.",
])
def test_rejects_spill_and_lidded_pour(brief, tmp_path):
    r = run(brief, tmp_path)
    assert r.returncode == 2, r.stderr


@pytest.mark.parametrize("brief", [
    "A white teapot, its lid lifted off and set beside it, pours tea into a cup.",
    "She holds a colander of berries under the tap; no berry leaves the colander.",
    "Steam rises from a kettle on the stove.",
])
def test_accepts_clean_briefs(brief, tmp_path):
    assert run(brief, tmp_path).returncode == 0


def test_brief_ok_skips(tmp_path):
    assert run("Her hand pours tea from a teapot.", tmp_path, BRIEF_OK="1").returncode == 0
