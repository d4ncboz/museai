// Meta Business Suite Reel composer (business.facebook.com/latest/reels_composer), one post for the
// Facebook Page and its linked Instagram account. Steps run in the isolated world through postqRun.
// The composer opens files through a detached <input type=file> + .click() (the native picker);
// background.js hooks that click in the page's MAIN world, so the input lands in the DOM marked
// data-postq-file and attach() fills it from here. Selectors checked against the live page 2026-11.
(() => {
  const { sleep, visible, $, waitFor, takeFile, attach, setValue, key } = globalThis.postqLib;

  const SEL = {
    postTo: '[role=combobox]',
    option: '[role=option]',
    hooked: 'input[type=file][data-postq-file]',
    customise: 'input[role=switch][aria-label^="Customise post"]',
    editor: '[role=textbox][contenteditable=true]',
    date: 'input[placeholder="dd/mm/yyyy"]',
    hours: 'input[role=spinbutton][aria-label=hours]',
    minutes: 'input[role=spinbutton][aria-label=minutes]',
    platformImg: 'img[alt=Facebook], img[alt=Instagram]',
    storySwitch: 'input[role=switch][aria-label="Share to Facebook story"]',
    row: '[role=row]',
  };
  const PLATFORM = { Facebook: 'facebook', Instagram: 'instagram' };

  const text = (el) => (el?.innerText || '').replace(/​/g, '').replace(/\s+/g, ' ').trim();
  const fold = (s) => (s || '').replace(/đ/g, 'd').replace(/Đ/g, 'D').normalize('NFD').replace(/[̀-ͯ]/g, '')
    .toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();

  // Visible button or link whose text is exactly `label` (the last one: the footer button comes after
  // the identically named scheduling-options tab).
  function button(label, { last = false } = {}) {
    const all = [...document.querySelectorAll('[role=button], button, [role=link]')].filter((b) => visible(b) && text(b) === label);
    return last ? all.at(-1) : all[0];
  }
  async function waitButton(label, opts = {}) {
    const end = Date.now() + (opts.timeout || 30000);
    for (;;) {
      const b = button(label, opts);
      if (b && b.getAttribute('aria-disabled') !== 'true') return b;
      if (Date.now() > end) throw new Error(`no "${label}" button${b ? ' (disabled)' : ''}`);
      await sleep(300);
    }
  }

  // Comboboxes and menus here open on pointer events, not on a bare .click().
  function press(el) {
    for (const type of ['pointerdown', 'mousedown', 'pointerup', 'mouseup', 'click']) {
      const Ev = type.startsWith('pointer') ? PointerEvent : MouseEvent;
      el.dispatchEvent(new Ev(type, { bubbles: true, cancelable: true, view: window, button: 0, pointerType: 'mouse' }));
    }
  }
  const escape = () => document.activeElement?.dispatchEvent(
    new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true }));

  // The Page and its Instagram account are the first option of each kind; Facebook groups come after
  // under their own heading and are never touched. "Save preference" is not an option to tick.
  async function targetOptions() {
    const box = await waitFor(SEL.postTo, { what: '"Post to" picker' });
    if (box.getAttribute('aria-expanded') !== 'true') press(box);
    await waitFor(SEL.option, { timeout: 5000, what: '"Post to" options' });
    const opts = [...document.querySelectorAll(SEL.option)];
    const kind = (o) => PLATFORM[o.querySelector(SEL.platformImg)?.alt];
    return {
      box,
      facebook: opts.find((o) => kind(o) === 'facebook'),
      instagram: opts.find((o) => kind(o) === 'instagram'),
    };
  }
  const picked = (o) => o?.getAttribute('aria-selected') === 'true';

  // Hooked inputs the composer created, newest last (an earlier attach leaves its input behind).
  async function hookedInput(accept, before) {
    const end = Date.now() + 15000;
    for (;;) {
      const fresh = [...document.querySelectorAll(SEL.hooked)].filter((i) => !before.includes(i) && (i.accept || '').includes(accept));
      if (fresh.length) return fresh.at(-1);
      if (Date.now() > end) throw new Error(`the composer opened no ${accept} file input (MAIN-world hook missing?)`);
      await sleep(200);
    }
  }

  // Caption box is Draft.js: a paste over select-all replaces the text and keeps line breaks.
  // insertText with "\n" garbles lines; execCommand delete/insertParagraph break Draft's DOM.
  // The paste only changes the editor; the post keeps its caption from the editor's blur handler.
  // A real blur never comes in an unfocused window (postq opens posts in background windows), and a
  // reel posted without it has an empty caption, so blur is sent as events here.
  async function paste(el, value) {
    el.focus();
    await sleep(150);
    document.execCommand('selectAll', false);
    await sleep(150);
    const dt = new DataTransfer();
    dt.setData('text/plain', value);
    el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
    await sleep(400);
    // The handler ignores a blur while the box is not focused (the paste can drop focus, seen on the
    // Instagram tab), so focus it again first.
    const box = $(SEL.editor) || el;
    box.focus();
    box.dispatchEvent(new FocusEvent('focus'));
    box.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));
    await sleep(150);
    box.dispatchEvent(new FocusEvent('focusout', { bubbles: true, relatedTarget: document.body }));
    box.dispatchEvent(new FocusEvent('blur', { relatedTarget: document.body }));
    await sleep(400);
  }

  // The caption the post will carry, as the composer's preview renders it (the editor's own text is
  // no proof: see paste). `kind`: "Facebook Feed preview" or "Instagram reel preview" (the Facebook
  // reel preview never shows a caption).
  const previewMenu = () => [...document.querySelectorAll('[role=button][aria-haspopup=menu]')]
    .find((b) => visible(b) && / preview$/.test(text(b)));
  async function previewText(kind) {
    const menu = previewMenu();
    if (!menu) throw new Error('no preview menu');
    if (text(menu) !== kind) {
      menu.click();
      let item;
      for (let i = 0; i < 20 && !item; i++) {
        await sleep(150);
        item = [...document.querySelectorAll('[role=menuitem]')].find((x) => visible(x) && text(x) === kind);
      }
      if (!item) throw new Error(`no "${kind}" in the preview menu`);
      item.click();
      for (let i = 0; i < 20 && text(previewMenu()) !== kind; i++) await sleep(150);
      if (text(previewMenu()) !== kind) throw new Error(`could not switch to ${kind}`);
    }
    await sleep(400);
    const s = document.body.innerText;
    const i = s.lastIndexOf(kind);
    const j = s.indexOf('Give us feedback', i);
    return s.slice(i + kind.length, j < 0 ? undefined : j);
  }
  // Longest start of `want` (folded) that `shown` (folded) contains.
  function shownPrefix(shown, want) {
    let lo = 0, hi = want.length;
    while (lo < hi) {
      const mid = Math.ceil((lo + hi) / 2);
      if (shown.includes(want.slice(0, mid))) lo = mid; else hi = mid - 1;
    }
    return lo;
  }
  // Throws unless the preview for `platform` shows `caption`. Previews may cut long text, so a start is
  // enough, but it must reach 30 characters past the title line both captions share, or the whole caption.
  async function checkStored(platform, caption, title) {
    const kind = platform === 'instagram' ? 'Instagram reel preview' : 'Facebook Feed preview';
    const want = fold(caption);
    if (!want) throw new Error(`${platform} caption is empty in the item`);
    const need = Math.min(want.length, Math.max(60, fold(title).length + 30));
    let shown = '';
    let got = 0;
    for (let i = 0; i < 5; i++) {
      shown = await previewText(kind);
      got = shownPrefix(fold(shown), want);
      if (got >= need) return got;
      await sleep(1000);
    }
    throw new Error(`${platform} caption not stored (${got}/${need} characters match): ${kind} shows ${JSON.stringify(shown.replace(/\s+/g, ' ').trim().slice(0, 120))}`);
  }
  // Facebook / Instagram caption tabs (Customise on); they switch on pointer events only.
  async function captionTab(name) {
    // The tabs render a moment after "Customise post" is switched on: wait for them before giving up.
    const find = () => [...document.querySelectorAll('[role=tab]')].find((x) => visible(x) && text(x) === name);
    let t = find();
    for (let i = 0; i < 40 && !t; i++) { await sleep(150); t = find(); }
    if (!t) {
      const tabs = [...new Set([...document.querySelectorAll('[role=tab]')].filter(visible).map((x) => text(x)))];
      throw new Error(`no ${name} caption tab; visible tabs: ${tabs.join(' | ') || 'none'}`);
    }
    if (t.getAttribute('aria-selected') !== 'true') press(t);
    for (let i = 0; i < 20 && t.getAttribute('aria-selected') !== 'true'; i++) await sleep(150);
    if (t.getAttribute('aria-selected') !== 'true') throw new Error(`${name} caption tab did not open`);
    await sleep(250);
  }
  const sameText = (a, b) => (a || '').replace(/\s+/g, ' ').trim() === (b || '').replace(/\s+/g, ' ').trim();

  // Date/time parts of `ms` in `tz`, as the composer shows them.
  function parts(ms, tz) {
    const get = (opts) => Object.fromEntries(new Intl.DateTimeFormat('en-GB', { timeZone: tz, ...opts })
      .formatToParts(new Date(ms)).map((x) => [x.type, x.value]));
    const n = get({ year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
    return { d: +n.day, dd: n.day, mm: n.month, m: get({ month: 'long' }).month, y: n.year, h: +n.hour, min: +n.minute };
  }
  // The composer labels its zone with any IANA name of the same offset (Asia/Saigon, Asia/Jakarta for
  // a +07 Page), so zones are compared by their UTC offset at the post time.
  const offset = (tz, ms) => new Intl.DateTimeFormat('en-US', { timeZone: tz, timeZoneName: 'longOffset' })
    .formatToParts(new Date(ms)).find((x) => x.type === 'timeZoneName').value;
  const sameZone = (a, b, ms) => { try { return offset(a, ms) === offset(b, ms); } catch { return false; } };

  // Fields here keep their value on blur, and a real blur never comes in an unfocused window (postq
  // opens posts in background windows), so it is also sent as events.
  function unfocus(el) {
    el.blur();
    el.dispatchEvent(new FocusEvent('focusout', { bubbles: true, relatedTarget: document.body }));
    el.dispatchEvent(new FocusEvent('blur', { relatedTarget: document.body }));
  }

  // Spinbuttons only take typed characters (no setter, no synthetic keydown).
  async function typeSpin(el, n) {
    el.focus();
    await sleep(50);
    document.execCommand('selectAll', false);
    for (const c of String(n).padStart(2, '0')) document.execCommand('insertText', false, c);
    await sleep(150);
    unfocus(el);
  }

  // Each schedule row (one per platform) follows its platform's logo in document order.
  function scheduleRows() {
    const imgs = [...document.querySelectorAll(SEL.platformImg)].filter(visible);
    return [...document.querySelectorAll(SEL.date)].filter(visible).map((date) => {
      const logo = imgs.filter((i) => i.compareDocumentPosition(date) & Node.DOCUMENT_POSITION_FOLLOWING).at(-1);
      let box = date;
      while (box && !box.querySelector(SEL.hours)) box = box.parentElement;
      const zone = (box?.innerText.match(/[A-Z][a-z]+\/[A-Za-z_]+/) || [])[0];
      return { platform: PLATFORM[logo?.alt], date, hours: box?.querySelector(SEL.hours), minutes: box?.querySelector(SEL.minutes), zone };
    });
  }
  const readRow = (r) => ({ date: r.date.value, time: `${String(r.hours.getAttribute('aria-valuenow') ?? r.hours.value).padStart(2, '0')}:${String(r.minutes.getAttribute('aria-valuenow') ?? r.minutes.value).padStart(2, '0')}`, zone: r.zone });

  globalThis.postqAdapters.meta = {
    async ready() {
      await waitFor(SEL.postTo, { timeout: 90000, what: 'Reel composer ("Post to" picker)' });
      await waitButton('Add video', { timeout: 60000 });
      return true;
    },

    // The Page + Instagram account the composer posts to (ticked options) and the asset in the URL.
    async whoami() {
      const { facebook, instagram } = await targetOptions();
      const who = {
        name: text(facebook).replace(/ ?Public group.*/, ''), ig: text(instagram) || null,
        id: new URL(location.href).searchParams.get('asset_id'), facebook: picked(facebook), instagram: picked(instagram),
      };
      escape();
      await sleep(300);
      return who;
    },

    // Tick exactly the wanted targets; read the picker back.
    async setTargets(targets) {
      const want = new Set(targets);
      const opts = await targetOptions();
      for (const t of ['facebook', 'instagram']) {
        if (!opts[t]) {
          if (want.has(t)) throw new Error(`this Page has no ${t} account to post to`);
          continue;
        }
        if (picked(opts[t]) !== want.has(t)) {
          opts[t].click();
          await sleep(500);
        }
      }
      const after = await targetOptions();
      const got = ['facebook', 'instagram'].filter((t) => picked(after[t]));
      escape();
      await sleep(300);
      if (got.join() !== ['facebook', 'instagram'].filter((t) => want.has(t)).join()) {
        throw new Error(`"Post to" shows ${got.join('+') || 'nothing'}, wanted ${[...want].join('+')}`);
      }
      return got;
    },

    async setVideo(name, type) {
      const before = [...document.querySelectorAll(SEL.hooked)];
      const add = await waitButton('Add video', { timeout: 8000 }).catch(() => null);
      let input;
      if (add) { add.click(); input = await hookedInput('video', before); }
      else input = [...document.querySelectorAll(SEL.hooked)].filter((i) => (i.accept || '').includes('video')).at(-1); // retry: composer already open
      if (!input) throw new Error('no video input in the composer');
      attach(input, takeFile('video', name, type));
      await waitFor('[role=progressbar], [aria-valuenow]', { timeout: 60000, what: 'video upload progress' }).catch(() => {});
      return name;
    },

    // Upload state of the attached video: percent + Meta's copyright check line.
    // `name`: the video's file name. Its own card ("name.mp4 1080 x 1920 ... 37%") is the only honest source:
    // the first "%" or progress bar anywhere on the page can be something else and sat at 0%.
    async progress(name) {
      const body = document.body.innerText;
      let pct;
      const label = name && [...document.querySelectorAll('span, div')].filter((e) => e.children.length === 0 && text(e) === name)[0];
      for (let box = label, i = 0; box && i < 6 && pct === undefined; box = box.parentElement, i++) {
        const own = box.querySelector('[role=progressbar][aria-valuenow]');
        const m = text(box).match(/(\d{1,3})%/);
        if (own) pct = +own.getAttribute('aria-valuenow');
        else if (m) pct = +m[1];
      }
      if (pct === undefined) {
        const bars = [...document.querySelectorAll('[role=progressbar][aria-valuenow]')].map((x) => +x.getAttribute('aria-valuenow'));
        pct = bars.length ? Math.max(...bars) : +([...body.matchAll(/(\d{1,3})%/g)].map((x) => x[1]).at(-1) ?? 0);
      }
      const check = body.match(/Your video is safe to publish!|[^\n]*copyright[^\n]*/i)?.[0] || null;
      const failed = /upload failed|couldn.t upload|try again/i.test(body) ? 'upload failed' : null;
      const hasBar = !!document.querySelector('[role=progressbar]');
      const snap = body.replace(/\s+/g, ' ').slice(0, 300);
      return { pct, uploading: pct < 100 && !failed, check, failed, hasBar, snap };
    },

    async setCover(name, type) {
      // Meta labels the thumbnail entry point differently by state (new reel / cover already set / other layout)
      const entry = await Promise.any(['Upload image', 'Change image', 'Add cover', 'Edit cover'].map((l) => waitButton(l, { timeout: 30000 }))).catch(() => {
        const labels = [...document.querySelectorAll('[role=button],button')].map((b) => (b.innerText || b.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ')).filter((t) => t && t.length < 40);
        throw new Error(`no thumbnail button; visible: ${[...new Set(labels)].slice(0, 40).join(' | ')}`);
      });
      entry.click();
      await sleep(800);
      const before = [...document.querySelectorAll(SEL.hooked)];
      (await waitButton('Upload Image', { timeout: 10000 }).catch(() => waitButton('Change Image', { timeout: 2000 }))).click();
      attach(await hookedInput('image', before), takeFile('cover', name, type));
      await waitButton('Change Image', { timeout: 60000 });
      return name;
    },

    // Captions go in last: switching the thumbnail tab re-renders "Reel details" and drops typed text.
    // One caption for both, or Customise on with each platform's own (Facebook / Instagram tabs).
    async fill(item) {
      // Customise is always on for Facebook + Instagram: each tab gets its own caption (the IG one
      // falls back to the Facebook caption), and each is read back on its own.
      const own = item.targets.includes('facebook') && item.targets.includes('instagram');
      const sw = $(SEL.customise);
      if (sw && sw.checked !== !!own) {
        sw.click();
        await sleep(800);
      }
      if (own && !$(SEL.customise)?.checked) throw new Error('could not turn on "Customise post for Facebook and Instagram"');
      const plan = own ? [['Facebook', item.caption], ['Instagram', item.caption_ig || item.caption]] : [[null, item.caption]];
      for (const [tab, value] of plan) {
        if (tab) await captionTab(tab);
        await paste(await waitFor(SEL.editor, { what: 'caption box' }), value);
        const got = $(SEL.editor)?.innerText;
        if (!sameText(got, value)) throw new Error(`${tab || ''} caption reads back as ${JSON.stringify((got || '').slice(0, 80))}`);
      }
      return own ? 'captions: own Facebook + Instagram' : 'caption: one for all targets';
    },

    // Re-check the caption(s) right before leaving the Create step: the editor text (it survives only
    // if nothing re-rendered) and the caption the post stores, per target, from the preview.
    // The flow never reaches submit when this throws.
    async checkCaptions(item) {
      const own = item.targets.includes('facebook') && item.targets.includes('instagram');
      if (own && !$(SEL.customise)?.checked) throw new Error('"Customise post for Facebook and Instagram" is off before Next');
      const ig = item.caption_ig || item.caption;
      const plan = own ? [['Facebook', item.caption], ['Instagram', ig]] : [[null, item.caption]];
      for (const [tab, value] of plan) {
        if (tab) await captionTab(tab);
        const got = $(SEL.editor)?.innerText;
        if (!sameText(got, value)) throw new Error(`${tab || ''} caption box reads ${JSON.stringify((got || '').trim().slice(0, 80))} before Next, not its caption`);
      }
      const stored = {};
      for (const p of item.targets) {
        const value = p === 'instagram' ? ig : item.caption;
        stored[p] = `${await checkStored(p, value, item.title)}/${fold(value).length} characters`;
      }
      return stored;
    },

    // Create -> Edit -> Share.
    async toShare() {
      const end = Date.now() + 60000;
      while (!button('Save as draft')) {
        if (Date.now() > end) throw new Error('did not reach the Share step');
        const next = button('Next');
        if (next && next.getAttribute('aria-disabled') !== 'true') next.click();
        await sleep(3000); // let the step render before the next press (a fast second click is lost)
      }
      return true;
    },

    // Schedule each platform row at `when` (ms) in `tz`, or pick Share now; read every row back.
    async schedule(when, tz) {
      if (!when) {
        (await waitButton('Share now')).click();
        return { mode: 'now' };
      }
      (await waitButton('Schedule')).click();
      await waitFor(SEL.date, { timeout: 10000, what: 'schedule date' });
      await sleep(500);
      const want = parts(when, tz);
      const out = [];
      for (const r of scheduleRows()) {
        if (r.zone && !sameZone(r.zone, tz, when)) throw new Error(`${r.platform} schedule is in ${r.zone}, item wants ${tz}`);
        r.date.focus();
        setValue(r.date, `${want.dd}/${want.mm}/${want.y}`);
        key(r.date, 'Enter');
        unfocus(r.date);
        await sleep(400);
        await typeSpin(r.hours, want.h);
        await typeSpin(r.minutes, want.min);
        await sleep(300);
      }
      await sleep(600);
      const wantDate = `${want.d} ${want.m} ${want.y}`;
      const wantTime = `${String(want.h).padStart(2, '0')}:${String(want.min).padStart(2, '0')}`;
      for (const r of scheduleRows()) {
        const got = readRow(r);
        if (got.date !== wantDate || got.time !== wantTime) {
          throw new Error(`${r.platform} schedule reads ${got.date} ${got.time}, wanted ${wantDate} ${wantTime}`);
        }
        out.push({ platform: r.platform, ...got });
      }
      const bad = document.body.innerText.match(/Scheduled posts need to be shared between[^\n]*/);
      if (bad && [...document.querySelectorAll('[role=alert], [aria-invalid=true]')].some(visible)) throw new Error(bad[0]);
      return { mode: 'scheduled', rows: out, zone: out[0]?.zone || tz };
    },

    // Toggles on the Share step worth logging (story share defaults ON for the Facebook Page).
    async extras() {
      return { story: $(SEL.storySwitch, { hidden: true })?.checked ?? null };
    },

    // The footer button: "Schedule" or "Share". Waits until the composer leaves (or says it is done).
    async submit() {
      const label = button('Schedule', { last: true }) && button('Save as draft') ? 'Schedule' : 'Share';
      const b = await waitButton(label, { last: true, timeout: 60000 });
      b.click();
      const end = Date.now() + 120000;
      while (Date.now() < end) {
        await sleep(1000);
        if (!location.pathname.includes('reels_composer')) return { button: label, confirm: `left composer for ${location.pathname}` };
        const done = document.body.innerText.match(/Your reel (?:has been|was) (?:scheduled|shared|published)[^\n]*|Reel scheduled[^\n]*/i);
        if (done) return { button: label, confirm: done[0] };
        const err = [...document.querySelectorAll('[role=alert]')].find(visible);
        if (err && text(err)) throw new Error(`after "${label}": ${text(err)}`);
      }
      throw new Error(`pressed "${label}", the composer did not confirm within 2 min`);
    },

    // Scheduled list (Content > Posts and reels > Scheduled): every row; `match` when its text starts
    // like one of `captions` (the Facebook and the Instagram caption differ when Customise was on),
    // `blank` when it has no caption (the list then shows "Your reel" in place of the text).
    async findScheduled(captions) {
      await waitFor(SEL.row, { timeout: 60000, what: 'scheduled posts table' });
      await sleep(800);
      const heads = [].concat(captions).filter(Boolean).map((c) => fold(c).slice(0, 40));
      const header = document.querySelector(SEL.row);
      const found = new Map();
      // The list renders lazily (and may drop rows that scrolled away): collect on every pass while
      // scrolling to the end, until a pass adds nothing.
      const scrollParent = (el) => {
        for (let p = el?.parentElement; p; p = p.parentElement) {
          if (p.scrollHeight > p.clientHeight + 20 && /auto|scroll/.test(getComputedStyle(p).overflowY)) return p;
        }
        return document.scrollingElement;
      };
      for (let i = 0, idle = 0; i < 40 && idle < 2; i++) {
        const before = found.size;
        const rows = [...document.querySelectorAll(SEL.row)];
        for (const r of rows) {
          if (r === header || r.querySelector('[role=columnheader]')) continue;
          const cells = [...r.querySelectorAll('[role=gridcell], [role=cell]')].map(text);
          const imgs = [...r.querySelectorAll('img')];
          const title = cells[1] || '';
          const date = cells[2] || '';
          const platform = PLATFORM[imgs.find((x) => PLATFORM[x.alt])?.alt] || null;
          const key = `${title}|${date}|${platform}`;
          if (found.has(key)) continue;
          found.set(key, {
            title, date, platform,
            thumb: imgs.find((x) => x.width >= 32 && /fbcdn/.test(x.src))?.src || null,
            match: heads.some((h) => fold(title).startsWith(h)),
            blank: !fold(title) || /^your reel reel\b/.test(fold(title)), // "Your reel Reel · <Page>"
          });
        }
        idle = found.size === before ? idle + 1 : 0;
        const last = rows.at(-1);
        if (last) { last.scrollIntoView({ block: 'end' }); const sp = scrollParent(last); if (sp) sp.scrollTop += 1500; }
        await sleep(700);
      }
      document.scrollingElement?.scrollTo(0, 0);
      return [...found.values()];
    },
  };
})();
