from __future__ import annotations

import json

import pytest

from museai.services import profiles


@pytest.fixture
def calls(monkeypatch) -> list[tuple[str, ...]]:
    """Fake bh-profile: 'work' runs on port 9300 once started."""
    seen: list[tuple[str, ...]] = []
    up: set[str] = set()

    async def fake(*args: str) -> str:
        seen.append(args)
        if args[0] == "start":
            up.add(args[1])
        elif args[0] == "stop":
            up.discard(args[1])
        elif args[0] == "list":
            return "NAME PORT STATE\n" + "".join(
                f"{n} {9300 + i} {'running' if n in up else 'stopped'}\n"
                for i, n in enumerate(["work", "home"])
            )
        return ""

    monkeypatch.setattr(profiles, "bh_profile", fake)
    return seen


def test_profiles_page(client):
    r = client.get("/profiles")
    assert r.status_code == 200
    assert "Browser profiles" in r.text


def test_page_crud_writes_json_files(client, admin, settings, calls):
    assert client.get("/profiles/data").status_code == 401
    assert client.post("/profiles/data", headers=admin, json={"name": "work"}).status_code == 200
    r = client.post("/profiles/data", headers=admin, json={"name": "work"})
    assert r.status_code == 400

    path = settings.data_dir / "profiles" / "work.json"
    assert json.loads(path.read_text()) == {
        "name": "work",
        "label": "",
        "logged_in": False,
        "verified": False,
    }

    client.put(
        "/profiles/data/work",
        headers=admin,
        json={"label": "Work account", "logged_in": True, "verified": True},
    )
    assert json.loads(path.read_text())["verified"] is True
    assert client.get("/profiles/data", headers=admin).json() == {
        "profiles": [
            {
                "name": "work",
                "label": "Work account",
                "logged_in": True,
                "verified": True,
                "running": False,
                "cdp_url": None,
            }
        ]
    }

    client.post("/profiles/work/launch", headers=admin)
    assert client.delete("/profiles/data/work", headers=admin).json() == {
        "name": "work",
        "deleted": True,
    }
    assert not path.exists()
    assert ("stop", "work") in calls  # a running profile is stopped before its file goes


def test_page_launch_opens_muse_with_label(client, admin, calls):
    client.post("/profiles/data", headers=admin, json={"name": "work", "label": "Work A"})
    r = client.post("/profiles/work/launch", headers=admin).json()
    assert r["cdp_url"] == "http://127.0.0.1:9300"
    assert ("start", "work", "https://muse.ai", "--label", "Work A") in calls


def test_agent_api(client, auth, admin, calls):
    client.post("/profiles/data", headers=admin, json={"name": "work"})
    assert client.get("/v1/profiles").status_code == 401

    r = client.post("/v1/profiles/work/launch", headers=auth, json={"url": "https://example.com"})
    assert r.json() == {
        "name": "work",
        "running": True,
        "cdp_url": "http://127.0.0.1:9300",
        "env": {"BU_NAME": "work", "BU_CDP_URL": "http://127.0.0.1:9300"},
    }
    assert ("start", "work", "https://example.com", "--label", "work") in calls
    assert client.get("/v1/profiles", headers=auth).json()["profiles"][0]["running"] is True

    client.post("/v1/profiles/work/launch", headers=auth)  # no body: muse.ai
    assert ("start", "work", "https://muse.ai", "--label", "work") in calls
    assert client.post("/v1/profiles/work/stop", headers=auth).json() == {
        "name": "work",
        "running": False,
    }


def test_agent_launch_unknown_or_bad_input(client, auth, admin, calls):
    assert client.post("/v1/profiles/nope/launch", headers=auth).status_code == 404
    assert client.post("/v1/profiles/default/launch", headers=auth).status_code == 400
    client.post("/profiles/data", headers=admin, json={"name": "work"})
    r = client.post(
        "/v1/profiles/work/launch", headers=auth, json={"url": "--remote-allow-origins=*"}
    )
    assert r.status_code == 400
    assert not any(c[0] == "start" for c in calls)


def test_missing_cli_is_reported(client, admin, monkeypatch):
    monkeypatch.setattr(profiles.shutil, "which", lambda _: None)
    r = client.get("/profiles/data", headers=admin)
    assert r.status_code == 500
    assert "bh-profile is not installed" in r.json()["error"]["message"]
