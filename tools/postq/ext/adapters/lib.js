// Shared page helpers, injected into the platform tab (isolated world) before an adapter.
// Every adapter step runs through postqRun(), so a thrown error comes back as {error} instead of
// a silent undefined from chrome.scripting.executeScript.
globalThis.postqLib ??= (() => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  const visible = (el) => el && el.isConnected && el.getClientRects().length > 0;

  // First element matching any selector (a list survives a renamed id); visible unless {hidden: true}.
  function $(selectors, { root = document, hidden = false } = {}) {
    for (const sel of [].concat(selectors)) {
      for (const el of root.querySelectorAll(sel)) if (hidden || visible(el)) return el;
    }
    return null;
  }

  async function waitFor(selectors, { timeout = 30000, hidden = false, what } = {}) {
    const end = Date.now() + timeout;
    while (Date.now() < end) {
      const el = $(selectors, { hidden });
      if (el) return el;
      await sleep(250);
    }
    throw new Error(`not found after ${timeout / 1000}s: ${what || [].concat(selectors).join(' | ')}`);
  }

  // Contenteditable boxes (YouTube title/description, Meta/X composers): select all + insertText
  // goes through the editor's own input handling, unlike setting textContent.
  async function typeInto(el, text) {
    el.focus();
    el.click();
    await sleep(100);
    document.execCommand('selectAll', false);
    document.execCommand(text ? 'insertText' : 'delete', false, text);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    await sleep(200);
  }

  // Plain <input>: native setter + input/change, so framework-bound inputs notice the value.
  function setValue(input, value) {
    const proto = input instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function key(el, k) {
    for (const type of ['keydown', 'keypress', 'keyup']) {
      el.dispatchEvent(new KeyboardEvent(type, { key: k, code: k, keyCode: { Enter: 13, Escape: 27 }[k] || 0, bubbles: true }));
    }
  }

  // Media arrives from the extension in base64 chunks (a whole video does not fit one message).
  const buffers = new Map();
  function chunk(slot, b64, first) {
    if (first) buffers.delete(slot); // a retry in the same page starts clean, not on top of the last try
    const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
    buffers.set(slot, [...(buffers.get(slot) || []), bytes]);
    return buffers.get(slot).reduce((n, b) => n + b.length, 0);
  }
  function takeFile(slot, name, type) {
    const parts = buffers.get(slot) || [];
    buffers.delete(slot);
    return new File(parts, name, { type });
  }

  function attach(input, file) {
    const dt = new DataTransfer();
    dt.items.add(file);
    input.files = dt.files;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  return { sleep, visible, $, waitFor, typeInto, setValue, key, chunk, takeFile, attach };
})();

globalThis.postqAdapters ??= {};

globalThis.postqRun ??= async (platform, step, args) => {
  try {
    const adapter = globalThis.postqAdapters[platform];
    if (!adapter?.[step]) throw new Error(`adapter ${platform} has no step ${step}`);
    return { value: await adapter[step](...args) };
  } catch (e) {
    return { error: e.message || String(e) };
  }
};
