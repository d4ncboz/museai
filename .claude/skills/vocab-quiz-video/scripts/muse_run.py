# browser-harness script (helpers are pre-imported). Run:
#   PROMPT_FILE=/tmp/vocab-x.prompt.txt OUT=videos/x.mp4 [REC=name] timeout 3000 browser-harness < scripts/muse_run.py
# Opens a new muse.ai side chat in a background tab, sends the prompt as one message, waits for the video,
# downloads it to OUT, renames the chat to the prompt's first line "Chat title: ..." and closes the tab.
# Parallel runs: give each its own BU_NAME and the profile's BU_CDP_URL; they share the profile's window.
# ruff: noqa: F821 - browser-harness pre-imports its helpers (js, cdp, page_info, ...) before exec.
import base64
import os
import pathlib
import subprocess
import time

prompt = pathlib.Path(os.environ["PROMPT_FILE"]).read_text(encoding="utf-8").strip()
out = pathlib.Path(os.environ["OUT"]).resolve()
out.parent.mkdir(parents=True, exist_ok=True)
rec = os.environ.get("REC")
if rec:
    print("recording:", start_recording(rec, title=f"vocab quiz {rec}"), flush=True)

# Never activate the tab: parallel runs would take the window from each other.
new_tab("https://muse.ai/thread/new")
for _ in range(3):
    wait_for_load()
    time.sleep(3)
    if page_info()["url"].endswith("/thread/new"):
        break
    goto_url("https://muse.ai/thread/new")  # under load muse.ai sometimes lands on its home page
else:
    raise SystemExit(f"not a new chat: {page_info()['url']}")

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


def download(src: str, path: pathlib.Path) -> None:
    js(
        f"(async()=>{{window.__vb=new Uint8Array(await (await fetch('{src}')).arrayBuffer());return 1}})()"
    )
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


def seconds(path: pathlib.Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
    )
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


# A background tab never loads <video> metadata, so the length cannot be read in the page.
# Wait until muse.ai stops replying, then download the newest video and measure it.
BUSY = (
    "[...document.querySelectorAll('[role=status]')].some(e=>/typing/i.test(e.getAttribute('aria-label')||e.innerText))"
    "||[...document.querySelectorAll('button')].some(b=>(b.getAttribute('aria-label')||'').trim()==='Stop')"
)
SRCS = "[...document.querySelectorAll('video')].map(v=>v.currentSrc||v.src||v.querySelector('source')?.src).filter(Boolean)"
start, checked, idle_since = time.time(), set(), None
while True:
    # Check new videos as soon as they appear: muse.ai can keep its Stop button after the
    # final reply. Scene clips sit next to the final video, so check every new one, newest first.
    found = False
    for src in reversed([s for s in js(SRCS) if s not in checked]):
        checked.add(src)
        download(src, out)
        if seconds(out) > 30:
            found = True
            break
        print(f"video is {seconds(out):.0f} s (a clip), still waiting", flush=True)
    if found:
        break
    busy = js(BUSY)
    idle_since = None if busy else (idle_since or time.time())
    if idle_since and time.time() - idle_since > 900 and time.time() - start > 60:
        raise SystemExit("muse.ai stopped replying 15 min ago without a video over 30 s")
    if time.time() - start > 2700:
        raise SystemExit("timeout: no video after 45 min")
    time.sleep(20)
print(f"video ready after {int(time.time() - start)} s ({seconds(out):.1f} s long)", flush=True)
for _ in range(12):  # up to 2 min for muse.ai to finish its reply (the word list)
    if not js(BUSY):
        break
    time.sleep(10)

text = js("document.body.innerText")
i = text.rfind(prompt.splitlines()[-1]) + len(prompt.splitlines()[-1])
print("=== muse reply ===\n" + text[i : i + 3000], flush=True)


# muse.ai names chats itself; rename this one so episodes are easy to find in the side chat list.
title = prompt.splitlines()[0].removeprefix("Chat title:").strip()
ROW = '[data-testid="hatch-thread-row"][aria-current="page"]'
try:
    x, y = js(
        f"(()=>{{const r=document.querySelector('{ROW}').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}})()"
    )
    cdp("Input.dispatchMouseEvent", type="mouseMoved", x=x, y=y)
    time.sleep(1)
    x, y = js(
        f"(()=>{{const r=document.querySelector('{ROW} button[aria-label=\"More thread actions\"]').getBoundingClientRect();return [r.x+r.width/2,r.y+r.height/2]}})()"
    )
    click_at_xy(x, y)
    time.sleep(1)
    item = next(
        n
        for n in cdp("Accessibility.getFullAXTree")["nodes"]
        if n.get("role", {}).get("value") == "menuitem"
        and n.get("name", {}).get("value") == "Rename"
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
close_tab()
