from __future__ import annotations

import json
import time


def test_health(client):
    assert client.get("/healthz").json()["ok"] is True
    assert client.get("/readyz").json()["ready"] is True


def test_auth_required(client):
    r = client.get("/v1/models")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_api_key"


def test_models(client, auth):
    ids = {m["id"] for m in client.get("/v1/models", headers=auth).json()["data"]}
    assert {"muse-chat", "muse-image", "muse-video", "gpt-4o"} <= ids


def test_chat_non_stream(client, auth):
    r = client.post("/v1/chat/completions", headers=auth, json={
        "model": "gpt-4o", "messages": [{"role": "user", "content": "hello"}]})
    assert r.status_code == 200
    body = r.json()
    assert body["object"] == "chat.completion"
    assert body["model"] == "gpt-4o"
    assert "hello" in body["choices"][0]["message"]["content"]


def test_chat_stream(client, auth):
    with client.stream("POST", "/v1/chat/completions", headers=auth, json={
        "messages": [{"role": "user", "content": "stream me"}], "stream": True,
        "stream_options": {"include_usage": True},
    }) as r:
        assert r.status_code == 200
        lines = [ln[6:] for ln in r.iter_lines() if ln.startswith("data: ")]
    assert lines[-1] == "[DONE]"
    chunks = [json.loads(x) for x in lines[:-1]]
    text = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks if c["choices"])
    assert "stream me" in text
    assert chunks[-1]["usage"]["total_tokens"] > 0


def test_chat_wrong_model_kind(client, auth):
    r = client.post("/v1/chat/completions", headers=auth, json={
        "model": "muse-video", "messages": [{"role": "user", "content": "x"}]})
    assert r.status_code == 400


def test_image_url_and_media(client, auth):
    r = client.post("/v1/images/generations", headers=auth,
                    json={"prompt": "a cat", "n": 2, "size": "1:1"})
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 2
    path = data[0]["url"].split("testserver", 1)[1]
    media = client.get(path)
    assert media.status_code == 200
    assert media.headers["content-type"] == "image/png"


def test_image_b64(client, auth):
    r = client.post("/v1/images/generations", headers=auth,
                    json={"prompt": "a dog", "response_format": "b64_json"})
    assert r.json()["data"][0]["b64_json"]


def test_video_task(client, auth):
    r = client.post("/v1/videos", headers=auth, json={"prompt": "waves", "duration": 5})
    task_id = r.json()["id"]
    for _ in range(50):
        task = client.get(f"/v1/videos/{task_id}", headers=auth).json()
        if task["status"] in ("succeeded", "failed"):
            break
        time.sleep(0.02)
    assert task["status"] == "succeeded", task
    assert task["result"]["url"].endswith(".mp4")


def test_reserved_endpoints(client, auth):
    assert client.post("/v1/responses", headers=auth, json={}).status_code == 501
    assert client.post("/v1/images/edits", headers=auth).status_code == 501


def test_admin_accounts_crud(client, auth, admin):
    assert client.get("/admin/accounts", headers=auth).status_code == 401

    r = client.post("/admin/accounts", headers=admin,
                    json={"label": "a1", "cookies": {"hatch_sess": "secretvalue123"}})
    assert r.status_code == 200
    acc = r.json()["account"]
    assert acc["cookies"]["hatch_sess"] != "secretvalue123"
    assert "hatch_gw" in r.json()["missing_cookies"]

    r = client.patch(f"/admin/accounts/{acc['id']}", headers=admin, json={"enabled": False})
    assert r.json()["account"]["enabled"] is False

    assert len(client.get("/admin/accounts", headers=admin).json()["data"]) == 1
    assert client.post(f"/admin/accounts/{acc['id']}/renew", headers=admin).json()["ok"]
    assert client.delete(f"/admin/accounts/{acc['id']}", headers=admin).status_code == 200
    assert client.get("/admin/status", headers=admin).json()["accounts"]["total"] == 0
