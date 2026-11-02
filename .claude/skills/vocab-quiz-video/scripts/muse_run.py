# browser-harness script (helpers are pre-imported). Run:
#   PROMPT_FILE=/tmp/vocab-x.prompt.txt OUT=videos/x.mp4 [REC=name] timeout 3000 browser-harness < scripts/muse_run.py
# Opens a new muse.ai side chat, sends the prompt as one message, waits for both videos and downloads them:
# VERSION 1 (no music) to <OUT stem>-nomusic.mp4, VERSION 2 (with music) to OUT, then renames the chat to the
# prompt's first line "Chat title: ...".
# ruff: noqa: F821 - browser-harness pre-imports its helpers (js, cdp, page_info, ...) before exec.
import base64
import json
import os
import pathlib
import time

prompt = pathlib.Path(os.environ["PROMPT_FILE"]).read_text(encoding="utf-8").strip()
out = pathlib.Path(os.environ["OUT"]).resolve()
out.parent.mkdir(parents=True, exist_ok=True)
rec = os.environ.get("REC")
if rec:
    print("recording:", start_recording(rec, title=f"vocab quiz {rec}"), flush=True)

# Reuse the muse.ai tab if one is attached; otherwise open one.
if "muse.ai" in current_tab().get("url", ""):
    goto_url("https://muse.ai/thread/new")
else:
    new_tab("https://muse.ai/thread/new")
wait_for_load()
time.sleep(3)
assert page_info()["url"].endswith("/thread/new"), f"not a new chat: {page_info()['url']}"

box = next(
    n
    for n in cdp("Accessibility.getFullAXTree")["nodes"]
    if n.get("role", {}).get("value") == "textbox" and n.get("name", {}).get("value") == "Message"
)
q = cdp("DOM.getBoxModel", backendNodeId=box["backendDOMNodeId"])["model"]["content"]
click_at_xy(sum(q[0::2]) / 4, sum(q[1::2]) / 4)
cdp("Input.insertText", text=prompt)
time.sleep(1)
typed = js("(document.activeElement.value ?? document.activeElement.innerText)")
assert len(typed) == len(prompt), f"prompt not typed fully: {len(typed)} of {len(prompt)}"
press_key("Enter")
time.sleep(5)
# Chromium does not load <video> metadata in a background tab, so the duration check would never pass.
activate_tab(current_tab())
print("chat:", page_info()["url"], flush=True)

# Status words also appear in the sidebar for other chats, so wait for the two final videos themselves.
start = time.time()
while True:
    vids = json.loads(
        js("JSON.stringify([...document.querySelectorAll('video')].map(v=>v.duration||0))")
    )
    if sum(d > 30 for d in vids) >= 2:
        break
    if time.time() - start > 2700:
        raise SystemExit(f"timeout: {sum(d > 30 for d in vids)} of 2 videos after 45 min")
    time.sleep(20)
print(f"videos ready after {int(time.time() - start)} s", flush=True)
time.sleep(10)

text = js("document.body.innerText")
i = text.rfind("VERSION 2")
print("=== muse reply ===\n" + text[i : i + 3000], flush=True)


def download(src: str, path: pathlib.Path) -> None:
    js(f"(async()=>{{window.__vb=new Uint8Array(await (await fetch('{src}')).arrayBuffer());return 1}})()")
    size, step = js("window.__vb.length"), 3 * 1024 * 1024
    with open(path, "wb") as f:
        for off in range(0, size, step):
            f.write(
                base64.b64decode(
                    js(
                        f"(()=>{{const c=window.__vb.subarray({off},{off + step});let s='';"
                        f"for(let i=0;i<c.length;i+=32768)s+=String.fromCharCode.apply(null,c.subarray(i,i+32768));return btoa(s)}})()"
                    )
                )
            )
    js("delete window.__vb")
    print(f"saved {path} ({size} bytes)", flush=True)


# Videos appear in chat order: VERSION 1 first, VERSION 2 last.
srcs = js("[...document.querySelectorAll('video')].filter(v=>v.duration>30).map(v=>v.currentSrc)")
download(srcs[0], out.with_name(out.stem + "-nomusic.mp4"))
download(srcs[-1], out)

# muse.ai names chats itself; rename this one so episodes are easy to find in the side chat list.
title = prompt.splitlines()[0].removeprefix("Chat title:").strip()
ROW = '[data-testid="hatch-thread-row"][aria-current="page"]'
try:
    x, y = js(f"(()=>{{const r=document.querySelector('{ROW}').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}})()")
    cdp("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
    time.sleep(1)
    x, y = js(f"(()=>{{const r=document.querySelector('{ROW} button[aria-label=\"More thread actions\"]').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}})()")
    click_at_xy(x, y)
    time.sleep(1)
    item = next(
        n
        for n in cdp("Accessibility.getFullAXTree")["nodes"]
        if n.get("role", {}).get("value") == "menuitem" and n.get("name", {}).get("value") == "Rename"
    )
    q = cdp("DOM.getBoxModel", backendNodeId=item["backendDOMNodeId"])["model"]["content"]
    click_at_xy(sum(q[0::2]) / 4, sum(q[1::2]) / 4)
    time.sleep(1)
    press_key("ctrl+a")
    cdp("Input.insertText", text=title)
    press_key("Enter")
    print("chat renamed:", title, flush=True)
except Exception as e:
    print(f"rename failed ({e}); rename the chat by hand to: {title}", flush=True)
if rec:
    stop_recording()
