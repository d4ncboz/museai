# browser-harness script (helpers are pre-imported). Run:
#   PROMPT_FILE=/tmp/vocab-x.prompt.txt OUT=videos/x.mp4 [REC=name] timeout 2100 browser-harness < scripts/muse_run.py
# Opens a new muse.ai side chat, sends the prompt as one message, waits for the final video, downloads it.
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
print("chat:", page_info()["url"], flush=True)

# Status words also appear in the sidebar for other chats, so wait for the final video itself.
start = time.time()
while True:
    vids = json.loads(
        js("JSON.stringify([...document.querySelectorAll('video')].map(v=>v.duration||0))")
    )
    if any(d > 30 for d in vids):
        break
    if time.time() - start > 1800:
        raise SystemExit("timeout: no final video after 30 min")
    time.sleep(20)
print(f"video ready after {int(time.time() - start)} s", flush=True)
time.sleep(10)

text = js("document.body.innerText")
i = text.rfind("Send the final MP4")
print("=== muse reply ===\n" + text[i : i + 3000], flush=True)

src = js("[...document.querySelectorAll('video')].find(v=>v.duration>30).currentSrc")
js(
    f"(async()=>{{window.__vb=new Uint8Array(await (await fetch('{src}')).arrayBuffer());return 1}})()"
)
size, step = js("window.__vb.length"), 3 * 1024 * 1024
with open(out, "wb") as f:
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
print(f"saved {out} ({size} bytes)", flush=True)
if rec:
    stop_recording()
