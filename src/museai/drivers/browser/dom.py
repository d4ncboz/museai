"""DOM selectors and in-page scripts for the muse.ai web client.

All knowledge about the page structure lives here. When muse.ai ships a UI
change, this is normally the only file that needs updating. Scripts return
JSON-serialisable values and never throw (errors are reported in the payload).
"""

from __future__ import annotations

import json

INPUT = "textarea"
AGENT_BUBBLE = 'div[class*="hatch-agent-bubble-bg"]'
ATTACHMENT = '[data-testid^="hatch-chat-attachment-presentation-"]'
STOP_BUTTON = 'button[aria-label*="Stop" i]'
FILE_INPUT = 'input[type="file"]'

LOGIN_HINTS = ("log in", "sign in", "create an account", "use another account")
QUOTA_HINTS = ("out of credits", "usage limit", "limit reached", "token limit")
STALL_HINTS = ("Still sending", "Connecting...")


def q(value: str) -> str:
    """JSON-quote a Python string for safe interpolation into JS."""
    return json.dumps(value)


PAGE_STATE = f"""(() => {{
  const body = document.body ? document.body.innerText : '';
  const hydration = document.querySelector('[data-hatch-shell-hydration-state]');
  return {{
    ready: document.readyState === 'complete' && !!document.querySelector({q(INPUT)})
           && (!hydration || hydration.getAttribute('data-hatch-shell-hydration-state') === 'hydrated')
           && !body.includes('Connecting...'),
    hasInput: !!document.querySelector({q(INPUT)}),
    path: location.pathname,
    head: body.slice(0, 800),
  }};
}})()"""

# Snapshot of the conversation used to detect new output after sending.
CHAT_STATE = f"""(() => {{
  const scrollers = [...document.querySelectorAll('*')].filter(e => {{
    const s = getComputedStyle(e);
    return (s.overflowY === 'auto' || s.overflowY === 'scroll') && e.scrollHeight > e.clientHeight + 50;
  }});
  scrollers.forEach(e => {{ e.scrollTop = e.scrollHeight; }});
  const bubbles = [...document.querySelectorAll({q(AGENT_BUBBLE)})];
  const last = bubbles.length ? (bubbles[bubbles.length - 1].innerText || '').trim() : '';
  const atts = [...document.querySelectorAll({q(ATTACHMENT)})].map(a => {{
    const v = a.querySelector('video'), i = a.querySelector('img');
    const m = v || i;
    return {{
      tid: a.getAttribute('data-testid') || '',
      kind: v ? 'video' : (i ? 'image' : 'unknown'),
      src: m ? (m.currentSrc || m.src || '') : '',
      w: m ? (m.videoWidth || m.naturalWidth || 0) : 0,
      h: m ? (m.videoHeight || m.naturalHeight || 0) : 0,
    }};
  }});
  const tail = document.body ? document.body.innerText.slice(-600) : '';
  return {{ agentCount: bubbles.length, lastText: last,
            generating: !!document.querySelector({q(STOP_BUTTON)}),
            attachments: atts, tail }};
}})()"""


def fill_input(text: str) -> str:
    """Set the textarea value through the native setter so React picks it up."""
    return f"""(() => {{
  const ta = document.querySelector({q(INPUT)});
  if (!ta) return {{ ok: false, err: 'no-input' }};
  ta.focus();
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
  setter.call(ta, {q(text)});
  ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
  return {{ ok: true, len: ta.value.length }};
}})()"""


CLICK_SEND = """(() => {
  const btn = [...document.querySelectorAll('button,[role=button]')]
    .filter(b => b.offsetParent !== null)
    .find(b => /send|发送/i.test((b.getAttribute('aria-label') || '') + ' ' + (b.getAttribute('data-testid') || '')));
  if (!btn) return 'missing';
  if (btn.disabled) return 'disabled';
  btn.click();
  return 'clicked';
})()"""

INPUT_EMPTY = f"!(document.querySelector({q(INPUT)}) || {{value: ''}}).value"


def attach_file(b64: str, mime: str, filename: str) -> str:
    return f"""(() => {{
  try {{
    const input = document.querySelector({q(FILE_INPUT)});
    if (!input) return {{ ok: false, err: 'no-file-input' }};
    const bin = atob({q(b64)});
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    const dt = new DataTransfer();
    dt.items.add(new File([bytes], {q(filename)}, {{ type: {q(mime)} }}));
    input.files = dt.files;
    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
    return {{ ok: true }};
  }} catch (e) {{ return {{ ok: false, err: String(e) }}; }}
}})()"""


def fetch_as_base64(url: str) -> str:
    """Fetch a (possibly blob:) URL inside the page context and return base64 bytes."""
    return f"""(async () => {{
  try {{
    const r = await fetch({q(url)});
    const b = await r.blob();
    const buf = new Uint8Array(await b.arrayBuffer());
    let s = '';
    for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
    return {{ ok: true, mime: b.type || '', b64: btoa(s) }};
  }} catch (e) {{ return {{ ok: false, err: String(e) }}; }}
}})()"""
