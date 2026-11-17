importScripts('follow.js'); // followDashboard: the badge counts the popup's list, the dashboard's "Ready to post"
const QUEUE = 'http://127.0.0.1:8766';
const DASH = 'http://127.0.0.1:18610/dashboard/posts';
const CHUNK = 4 * 1024 * 1024; // bytes per executeScript call while moving a video into the tab
const UPLOAD_TIMEOUT_MS = 60 * 60 * 1000;
const log = (...args) => console.debug('[post-approve]', ...args);

// Background side of each platform: where the composer lives and which page scripts drive it.
const ADAPTERS = {
  youtube: { url: 'https://www.youtube.com/upload', host: 'studio.youtube.com', files: ['adapters/lib.js', 'adapters/youtube.js'], flow: youtubeFlow },
  x: { url: 'https://x.com/compose/post', host: 'x.com', files: ['adapters/lib.js', 'adapters/x.js'], flow: xFlow },
  meta: { url: 'https://business.facebook.com/latest/', host: 'business.facebook.com', files: ['adapters/lib.js', 'adapters/meta.js'], flow: metaFlow },
  tiktok: { url: 'https://www.tiktok.com/tiktokstudio/upload', host: 'www.tiktok.com', files: ['adapters/lib.js', 'adapters/tiktok.js'], flow: tiktokFlow },
};

const api = (path, body) => fetch(`${QUEUE}/api/items${path}`, {
  method: 'POST', headers: { 'X-Postq': '1', 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}),
});

// Progress lines the popup shows while a post runs (the popup may be closed and reopened meanwhile).
async function progress(id, line) {
  log(id, line);
  const { progress: all = {} } = await chrome.storage.session.get('progress');
  await chrome.storage.session.set({ progress: { ...all, [id]: line } });
}

async function refreshBadge() {
  try {
    // The header tells the queue server the extension is alive (`postq approve` warns when it is not).
    const items = await (await fetch(`${QUEUE}/api/items`, { headers: { 'X-Postq-Poller': chrome.runtime.getManifest().version } })).json();
    let shown = items;
    try {
      const feed = await (await fetch(DASH, { signal: AbortSignal.timeout(4000) })).json();
      if (Array.isArray(feed.videos)) shown = followDashboard(items, dashboardVideos(feed)).items;
    } catch { /* dashboard down: count the whole queue */ }
    chrome.action.setBadgeText({ text: shown.length ? String(shown.length) : '' });
    chrome.action.setBadgeBackgroundColor({ color: '#cc0000' });
    autoPost(items);
  } catch {
    chrome.action.setBadgeText({ text: '' });
  }
}

// `postq approve` sets item.auto. The claim stops a second start while one runs, and a failed post
// comes back from the server with auto cleared, so it is not retried until approved again.
// One platform at a time (curPlatform, drained before the next), one account at a time within it; each post in its own window. A window of its own renders even when
// another is in front (Chrome pauses only hidden tabs and fully covered windows), and it never takes
// focus, so the popup stays open. YouTube: three lanes on one channel until it is empty (a lane
// never joins another channel while a post runs, a channel switch is login-wide); Business Suite and X pick the account per post.
const LANES = { youtube: 3, meta: 1, x: 1, tiktok: 1 };
const laneBusy = {};
const ytActive = new Map(); // id -> account of in-flight auto posts: a new one joins only that account
const skipUntil = new Map(); // id -> ms: a refused claim (held or posting elsewhere) waits, no spin
// Facebook blocked Business Suite ("You're Temporarily Blocked", 2026-11-05) after a reel every ~75 s
// back to back. Meta posts now start GAP apart (with jitter), and a block page pauses the lane for
// PAUSE. Both live in chrome.storage.local, so an extension reload does not reset them.
const GAP_MS = { meta: [8 * 60000, 12 * 60000] };
const PAUSE_MS = 6 * 60 * 60000;
const BLOCKED = /temporarily blocked|you can.t use this feature right now|going too fast|misusing this feature/i;
class Blocked extends Error {}
let laneNext = {}; // platform -> ms before which the lane starts nothing new
let ytCurrent = ''; // YouTube channel Studio is on, as last confirmed: drained before any switch
// Series channel ("dream", "travel", "healing", "chinese") that posts first on every platform. '' = none.
// Change: chrome.storage.local.set({ priorityChannel: 'travel' }) in the service worker console.
let priorityChannel = 'dream';
const laneNextLoaded = chrome.storage.local.get(['laneNext', 'ytCurrent', 'priorityChannel']).then(({ laneNext: ln, ytCurrent: yc, priorityChannel: pc }) => {
  laneNext = ln || {};
  ytCurrent = yc || '';
  if (typeof pc === 'string') priorityChannel = pc;
});
async function setYtCurrent(account) {
  ytCurrent = account;
  await chrome.storage.local.set({ ytCurrent });
}
async function holdLane(platform, ms) {
  laneNext = { ...laneNext, [platform]: Math.max(laneNext[platform] || 0, Date.now() + ms) };
  await chrome.storage.local.set({ laneNext });
}
let curPlatform = ''; // the one platform the auto queue works on: drained before it moves to the next
const lastAcct = {}; // platform -> account last started (YouTube uses ytCurrent)
async function autoPost(items) {
  await laneNextLoaded;
  const now = Date.now();
  const ready = (i, p) => i.auto && i.platform === p && !running.has(i.id)
    && !starting.has(i.id) && !((skipUntil.get(i.id) || 0) > now);
  const isPrio = (i) => priorityChannel && i.channel === priorityChannel;
  // A held lane (Meta gap) is waited out; a long pause (block page) lets the next platform go.
  const waitOk = (p) => (laneNext[p] || 0) - now < 15 * 60000;
  // A rush item (a "post now" tap) starts at once: past the Meta gap and the platform being drained.
  for (const item of items.filter((i) => i.rush && LANES[i.platform] && ready(i, i.platform))) {
    if (!laneBusy[item.platform]) start(item, item.platform); // an idle lane only: no account switch mid-run
  }
  const busy = Object.keys(LANES).find((p) => (laneBusy[p] || 0) > 0);
  if (busy) curPlatform = busy;
  else if (!curPlatform || !items.some((i) => ready(i, curPlatform)) || !waitOk(curPlatform)) {
    const cand = items.filter((i) => LANES[i.platform] && ready(i, i.platform) && waitOk(i.platform));
    curPlatform = (cand.find(isPrio) || cand[0])?.platform || '';
  }
  const platform = curPlatform;
  if (!platform) return;
  const n = LANES[platform];
  while ((laneBusy[platform] || 0) < n) {
    if ((laneNext[platform] || 0) > Date.now()) break;
    // Priority channel (Dream) goes first; then the rest in queue order.
    const pool = items.filter((i) => ready(i, platform) && isPrio(i));
    const rest = items.filter((i) => ready(i, platform) && !isPrio(i));
    const queue = [...pool, ...rest];
    // One account at a time: the in-flight one, else the priority channel's, else the one last used while
    // it has auto items; switch only when none are left (an account switch costs a re-login / page reload).
    const last = platform === 'youtube' ? ytCurrent : lastAcct[platform];
    const acct = [...ytActive.values()][0] ?? pool[0]?.account ?? (queue.some((i) => i.account === last) ? last : undefined);
    const item = queue.find((i) => acct === undefined || i.account === acct);
    if (!item) break;
    start(item, platform);
  }
}

function start(item, platform) {
  laneBusy[platform] = (laneBusy[platform] || 0) + 1;
  starting.add(item.id);
  ytActive.set(item.id, item.account);
  lastAcct[platform] = item.account;
  const gap = GAP_MS[platform];
  if (gap) holdLane(platform, gap[0] + Math.random() * (gap[1] - gap[0]));
  approve(item, {})
    .catch((e) => {
      log('auto failed', item.id, e.message);
      if (/Already being posted/.test(e.message)) skipUntil.set(item.id, Date.now() + 120000);
    })
    .finally(() => { laneBusy[platform] -= 1; starting.delete(item.id); ytActive.delete(item.id); });
}

const starting = new Set();
const running = new Set();
const slots = new Set(); // window positions in use (cascaded, so each window keeps a visible strip)
async function approve(item, edits, manual = false) {
  if (running.has(item.id)) throw new Error('Already posting.');
  const adapter = ADAPTERS[item.platform];
  if (!adapter) throw new Error(`No ${item.platform} adapter yet.`);
  const claim = await api(`/${item.id}/claim`);
  if (!claim.ok) throw new Error('Already being posted (or posted) elsewhere: skipped.');
  running.add(item.id);
  const post = { ...item, ...edits };
  let tabId;
  try {
    // Visible tab: Studio renders its upload form with requestAnimationFrame, which Chrome pauses
    // in background tabs, so a hidden tab never shows the details form (checked 2026-11).
    // More windows than slots (or a slot never freed) must not leave `slot` undefined: windows.create
    // rejects a NaN position.
    const slot = [...Array(8).keys()].find((k) => !slots.has(k)) ?? slots.size % 8;
    slots.add(slot);
    post.slot = slot;
    // A single card's Approve opens maximized and focused so the schedule date is easy to change;
    // the auto queue keeps small unfocused cascaded windows (several maximized ones would hide each other).
    const win = await chrome.windows.create(manual
      ? { url: adapter.url, focused: true, type: 'normal', state: 'maximized' }
      : { url: adapter.url, focused: false, type: 'normal',
        left: 40 + slot * 70, top: 40 + slot * 50, width: 1280, height: 900 });
    tabId = win.tabs[0].id;
    const result = await adapter.flow(post, page(tabId, item.platform, adapter));
    await api(`/${item.id}`, { ...edits, ...result });
    await progress(item.id, `${result.status}${result.url ? ` · ${result.url}` : ''}`);
    if (result.status !== 'dry-run') chrome.tabs.remove(tabId).catch(() => {}); // last tab: closes its window
    return result;
  } catch (e) {
    // An upload that got as far as a video id is kept, so the retry finishes that video, no second copy.
    await api(`/${item.id}/release`, { error: e.message, video_id: post.video_id });
    if (e instanceof Blocked) {
      // Not the item's fault: pause the whole lane and keep the item approved for after the pause.
      await holdLane(item.platform, e.ms || PAUSE_MS);
      await api(`/${item.id}/approve`);
      const until = new Date(laneNext[item.platform]).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      await progress(item.id, `paused: ${e.message} · ${item.platform} posts wait until ${until}`);
    } else await progress(item.id, `failed: ${e.message}`);
    // Close it too: the error is in the queue (last_error) and a retry opens a fresh window.
    if (tabId) chrome.tabs.remove(tabId).catch(() => {});
    throw e;
  } finally {
    running.delete(item.id);
    slots.delete(post.slot);
    refreshBadge();
  }
}

// Page driver for one tab: waits for the platform host, injects lib + adapter, runs steps.
function page(tabId, platform, adapter) {
  async function inject() {
    const end = Date.now() + 60000;
    for (;;) {
      const tab = await chrome.tabs.get(tabId);
      if (/facebook\.com\/checkpoint/.test(tab.url || '')) throw new Blocked(`Facebook checkpoint (${tab.url})`);
      if (tab.status === 'complete' && new URL(tab.url || 'about:blank').host === adapter.host) break;
      if (Date.now() > end) throw new Error(`${adapter.host} did not load (logged in? tab url: ${tab.url})`);
      await new Promise((r) => setTimeout(r, 500));
    }
    const [{ result: text }] = await chrome.scripting.executeScript({
      target: { tabId }, func: () => (document.body?.innerText || '').slice(0, 3000),
    });
    if (platform === 'meta' && BLOCKED.test(text)) throw new Blocked(`${adapter.host} says: ${text.trim().split('\n').slice(0, 2).join(' ').slice(0, 160)}`);
    await chrome.scripting.executeScript({ target: { tabId }, files: adapter.files });
  }
  async function step(name, ...args) {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId }, func: (p, s, a) => globalThis.postqRun(p, s, a), args: [platform, name, args],
    });
    if (!result) throw new Error(`step ${name}: no answer from the page (navigated away?)`);
    if (result.error) throw new Error(`step ${name}: ${result.error}`);
    return result.value;
  }
  // Pull the file from the queue server in ranges and hand it to the page chunk by chunk.
  async function send(slot, media, onPct) {
    for (let start = 0; start < media.size; start += CHUNK) {
      const end = Math.min(start + CHUNK, media.size) - 1;
      const res = await fetch(`${QUEUE}/media/${media.file}`, { headers: { Range: `bytes=${start}-${end}` } });
      if (res.status !== 206) throw new Error(`queue server answered ${res.status} for ${media.file}`);
      const bytes = new Uint8Array(await res.arrayBuffer());
      let bin = '';
      for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
      const got = await chrome.scripting.executeScript({
        target: { tabId }, func: (s, b) => globalThis.postqLib.chunk(s, b), args: [slot, btoa(bin)],
      });
      if (got[0].result !== end + 1) throw new Error(`${slot} transfer broke at byte ${start}`);
      onPct?.(Math.round(((end + 1) / media.size) * 100));
    }
  }
  // Load another page in the same tab and re-inject (status reads 'complete' until the new load starts).
  // `until`: the URL prefix to wait for, where the site rewrites the query string on load.
  async function go(url, until = url) {
    await chrome.tabs.update(tabId, { url, active: true });
    const end = Date.now() + 60000;
    while (!(await chrome.tabs.get(tabId)).url?.startsWith(until)) {
      if (Date.now() > end) throw new Error(`tab did not go to ${url} (a "leave page?" prompt?)`);
      await new Promise((r) => setTimeout(r, 500));
    }
    await inject();
  }
  // After a channel switch: let Studio's own reload settle, then load the upload page again.
  async function reopen(url = adapter.url) {
    const end = Date.now() + 30000;
    const before = (await chrome.tabs.get(tabId)).url;
    while ((await chrome.tabs.get(tabId)).url === before && Date.now() < end) await new Promise((r) => setTimeout(r, 500));
    while ((await chrome.tabs.get(tabId)).status !== 'complete' && Date.now() < end) await new Promise((r) => setTimeout(r, 500));
    await chrome.tabs.update(tabId, { url, active: true });
    while ((await chrome.tabs.get(tabId)).status === 'complete' && Date.now() < end) await new Promise((r) => setTimeout(r, 200));
    await inject();
  }
  // Run `func` in the page's own (MAIN) world, e.g. to patch a prototype the page itself calls.
  async function main(func, ...args) {
    await chrome.scripting.executeScript({ target: { tabId }, world: 'MAIN', func, args });
  }
  return { inject, step, send, go, reopen, main };
}

const mimeOf = (file) => ({ mp4: 'video/mp4', mov: 'video/quicktime', webm: 'video/webm', jpg: 'image/jpeg',
  jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp' })[file.split('.').pop()];

const accountMatches = (want, who) => {
  const norm = (s) => (s || '').trim().replace(/^@/, '').toLowerCase();
  return [who.name, who.id].some((v) => v && norm(v) === norm(want));
};

async function youtubeFlow(item, pg) {
  const say = (line) => progress(item.id, line);
  await say('Opening YouTube Studio…');
  await pg.inject();
  await pg.step('ready');
  let who = await pg.step('whoami');
  if (!accountMatches(item.account, who)) {
    await say(`Studio is on "${who.name}", switching to "${item.account}"…`);
    await pg.step('switchChannel', item.account);
    await pg.reopen(); // the switch reloads Studio on the channel's dashboard
    await pg.step('ready');
    who = await pg.step('whoami');
    if (!accountMatches(item.account, who)) {
      throw new Error(`switched channel, but Studio is on "${who.name}" (${who.id}), item wants "${item.account}"`);
    }
  }
  await setYtCurrent(item.account);
  const when = item.schedule_at ? Date.parse(item.schedule_at) : null;
  // A run killed between upload and saving the id (reload, crash, closed window) left a copy on the
  // channel: find it by title (or the filename title a fresh draft gets) and finish that one instead.
  if (!item.video_id) {
    await say(`Channel ${who.name} ✓ · checking it has no copy of this video yet…`);
    await pg.go(`https://studio.youtube.com/channel/${who.id}/videos/short`);
    const want = new Set([item.title, item.video.name.replace(/\.[^.]+$/, '').replace(/[-_]+/g, ' ')].map(fold));
    const copies = (await pg.step('uploads')).filter((u) => want.has(fold(u.title)));
    if (copies.length > 1) throw new Error(`${copies.length} copies of "${item.title}" already on the channel (${copies.map((c) => `${c.id} ${c.vis}`).join(', ')}): delete the extras in Studio, then approve again`);
    const copy = copies[0];
    if (copy && !/draft/i.test(copy.vis)) {
      // Already public / scheduled: this item is done; touching it again could only break it.
      return { status: /schedul/i.test(copy.vis) ? 'scheduled' : 'posted', url: `https://youtube.com/shorts/${copy.id}`,
        video_id: copy.id, log: `already on the channel as ${copy.id} (${copy.vis}): not uploaded again` };
    }
    if (copy) {
      item.video_id = copy.id;
      await say(`Found an earlier draft ${copy.id}: finishing it, no second copy`);
    } else {
      await pg.go(ADAPTERS.youtube.url, 'https://studio.youtube.com');
      await pg.step('ready');
    }
  }
  // Already uploaded (`postq approve --video <id>`): no second copy, only finish and check that video.
  if (item.video_id) {
    await say(`Channel ${who.name} ✓ · resuming video ${item.video_id}`);
    return checkOnEditPage(item, pg, item.video_id, `https://youtube.com/shorts/${item.video_id}`, when, 'resumed');
  }
  await say(`Channel ${who.name} ✓ · moving video into the tab…`);
  await pg.send('video', item.video, (p) => say(`Moving video into the tab ${p}%`));
  await pg.step('setVideo', item.video.name, mimeOf(item.video.file));
  item.video_id = (await pg.step('progress')).url?.match(/(?:shorts\/|youtu\.be\/|[?&]v=)([\w-]{11})/)?.[1];
  await say('Filling details…');
  const warnings = await pg.step('fill', item);
  await pg.step('toVisibility');
  const vis = await pg.step('visibility', item, when);
  const note = [vis.mode === 'scheduled' ? `scheduled ${vis.date} ${vis.time} (${vis.zone})` : vis.mode, ...warnings].join(' · ');
  await say(note);

  const end = Date.now() + UPLOAD_TIMEOUT_MS;
  for (let p = await pg.step('progress'); p.uploading; p = await pg.step('progress')) {
    if (Date.now() > end) throw new Error(`upload did not finish within 60 min (${p.label})`);
    await say(`${p.label}`);
    await new Promise((r) => setTimeout(r, 3000));
  }
  const { url } = await pg.step('progress');
  if (item.dry_run) return { status: 'dry-run', url, log: `${note} · form filled, not submitted (tab left open)` };
  const sent = await pg.step('submit');
  const link = sent.url || url;
  await say(`${sent.confirm} · checking the edit page`);
  const id = link?.match(/(?:shorts\/|youtu\.be\/|[?&]v=)([\w-]{11})/)?.[1];
  if (!id) throw new Error(`pressed "${sent.button}" but got no video id to check (link: ${link})`);
  return checkOnEditPage(item, pg, id, link, when, note);
}

// Only the saved video counts: reopen it in Studio, schedule it if it is still a draft, fix what
// drifted, read the schedule back.
async function checkOnEditPage(item, pg, id, link, when, note) {
  const say = (line) => progress(item.id, line);
  const edit = `https://studio.youtube.com/video/${id}/edit`;
  await pg.go(edit);
  if (await pg.step('openDraft')) {
    await say('Still a draft: setting its schedule…');
    await pg.step('toVisibility');
    await pg.step('visibility', item, when);
    const sent = await pg.step('submit');
    await say(`${sent.confirm} · checking the edit page`);
    await pg.go(edit);
    if (await pg.step('openDraft')) throw new Error(`video ${id} is still a draft after "${sent.button}"`);
  }
  // Cover goes up on the edit page: the upload dialog has no thumbnail picker for Shorts.
  if (item.cover) await pg.send('cover', item.cover, (p) => say(`Moving thumbnail into the tab ${p}%`));
  const checks = await pg.step('verify', { ...item, cover: item.cover && { name: item.cover.name, type: mimeOf(item.cover.file) } }, when);
  return { status: when ? 'scheduled' : 'posted', url: link, log: [note, ...checks].join(' · ') };
}

const X_SCHEDULED = 'https://x.com/compose/post/unsent/scheduled';

// X: one composer, no account switch here (the wrong @handle stops the post), no custom thumbnail.
// The Scheduled list is checked first (a retry must not schedule a second copy) and after.
async function xFlow(item, pg) {
  const say = (line) => progress(item.id, line);
  await say('Opening the X composer…');
  await pg.inject();
  await pg.step('ready');
  const who = await pg.step('whoami');
  if (!accountMatches(item.account, who)) {
    throw new Error(`x.com is on @${who.id}, item wants @${item.account.replace(/^@/, '')}: switch account on x.com, then approve again`);
  }
  const when = item.schedule_at ? Date.parse(item.schedule_at) : null;
  if (when && !item.dry_run) {
    await say(`@${who.id} ✓ · checking the Scheduled list…`);
    await pg.go(X_SCHEDULED);
    const there = await pg.step('findScheduled', item.caption, when);
    if (there?.line) return { status: 'scheduled', url: X_SCHEDULED, log: `already scheduled: ${there.line}` };
    if (there?.wrong) throw new Error(`same text already scheduled at another time (${there.wrong}): fix it on x.com`);
    await pg.go(ADAPTERS.x.url);
    await pg.step('ready');
  }
  await say(`@${who.id} ✓ · moving video into the tab…`);
  await pg.send('video', item.video, (p) => say(`Moving video into the tab ${p}%`));
  await pg.step('setVideo', item.video.name, mimeOf(item.video.file));
  await say('Filling text…');
  await pg.step('fill', item);
  const sched = when ? await pg.step('schedule', when) : null;
  const note = [sched ? `${sched.line} (${sched.zone})` : 'post now', 'no custom thumbnail on X'].join(' · ');
  await say(note);
  // Uploading -> Processing -> Ready; the Schedule/Post button turns on once X has the video.
  const end = Date.now() + UPLOAD_TIMEOUT_MS;
  let idle = 0; // checks with the button off and nothing uploading (text over 280?)
  for (let p = await pg.step('progress'); p.error || p.uploading || p.off; p = await pg.step('progress')) {
    if (p.error) throw new Error(`X rejected the video: ${p.error}`);
    if (Date.now() > end) throw new Error(`upload did not finish within 60 min (${p.label})`);
    if (!p.uploading && ++idle > 10) throw new Error(`"${p.button}" stays off with the video ready (${p.label}): text too long?`);
    await say(p.label || 'waiting for X…');
    await new Promise((r) => setTimeout(r, 3000));
  }
  if (item.dry_run) return { status: 'dry-run', url: null, log: `${note} · composer filled, not sent (tab left open)` };
  const sent = await pg.step('submit');
  if (!when) return { status: 'posted', url: `https://x.com/${who.id}`, log: `${note} · ${sent.confirm}` };
  await say(`${sent.confirm} · checking the Scheduled list`);
  await pg.go(X_SCHEDULED);
  const got = await pg.step('findScheduled', item.caption, when);
  if (!got?.line) throw new Error(`pressed "${sent.button}" but the Scheduled list has no matching post${got?.wrong ? ` (found ${got.wrong})` : ''}`);
  return { status: 'scheduled', url: X_SCHEDULED, log: `${note} · on the Scheduled list: ${got.line}` };
}

// MAIN world: Business Suite opens its file picker with .click() on a detached <input type=file>.
// Keep that input instead (in the DOM, marked), so the adapter can set its files; no native dialog.
function hookFileInputs() {
  if (window.__postqFileHook) return;
  window.__postqFileHook = true;
  const click = HTMLInputElement.prototype.click;
  HTMLInputElement.prototype.click = function () {
    if (this.type !== 'file') return click.call(this);
    this.dataset.postqFile = String(Date.now());
    this.style.display = 'none';
    if (!this.isConnected) document.body.appendChild(this);
  };
}

const BS = 'https://business.facebook.com/latest';
// "17 November 12:00": how the Scheduled list shows a time in the Page's zone.
function listTime(ms, tz) {
  const p = Object.fromEntries(new Intl.DateTimeFormat('en-GB', { timeZone: tz, day: 'numeric', month: 'long',
    hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).formatToParts(new Date(ms)).map((x) => [x.type, x.value]));
  return `${p.day} ${p.month} ${p.hour}:${p.minute}`;
}

// Reels have no title field: item.title goes in as each caption's first line, unless that line already is it.
const fold = (s) => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
function titled(title, caption) {
  if (!title || !caption || fold(caption.split('\n')[0]) === fold(title)) return caption;
  return `${title}\n${caption}`;
}

// One Business Suite Reel for the Page and/or its Instagram account (item.targets).
// Business Suite takes a scheduled post only 20 min to 29 days ahead. A past slot goes out soon after
// now; a slot too far ahead is never moved (2026-11: clamping it to now+28 d saved reels at the run
// time of day, e.g. 16:38 for a 19:00 slot): the item waits until its slot is inside the window.
const META_MIN_MS = 25 * 60000;
const META_MAX_MS = 29 * 86400000 - 30 * 60000;
function metaWhen(when) {
  if (!when) return when;
  const now = Date.now();
  if (when < now + META_MIN_MS) return now + META_MIN_MS;
  if (when > now + META_MAX_MS) {
    throw new Error(`slot is more than 29 days ahead (Business Suite's limit): run it again after ${new Date(when - META_MAX_MS).toISOString().slice(0, 16)}Z`);
  }
  return when;
}

async function metaFlow(stored, pg) {
  // Steps see the titled captions; `stored` (persisted) keeps them apart so an edit or retry never doubles the title.
  const item = { ...stored, caption: titled(stored.title, stored.caption), caption_ig: titled(stored.title, stored.caption_ig) };
  const say = (line) => progress(item.id, line);
  const a = item.asset;
  if (!a?.asset_id || !a?.business_id) throw new Error('item has no Business Suite asset (postq add --asset BUSINESS_ID:ASSET_ID)');
  const q = `asset_id=${a.asset_id}&business_id=${a.business_id}`;
  const when = item.schedule_at ? Date.parse(item.schedule_at) : null;
  const list = `${BS}/posts/${when ? 'scheduled' : 'published'}_posts?${q}`;
  if (!item.video_id) metaWhen(when); // a slot too far ahead stops here, before any upload

  // Never a second post: a submitted item, or one whose caption is already in the list, is only checked;
  // a reel already at this slot for a target (one saved without its caption looks like nobody's) stops it.
  if (!item.dry_run) {
    await say('Opening Business Suite…');
    // The other list too: a reel scheduled earlier (or already gone out) is this item, at whatever time.
    const other = `${BS}/posts/${when ? 'published' : 'scheduled'}_posts?${q}`;
    await pg.go(other, `${BS}/posts/`);
    const elsewhere = (await pg.step('findScheduled', [item.caption, item.caption_ig])).filter((r) => r.match);
    if (elsewhere.length) {
      await say(`Already ${when ? 'posted' : 'scheduled'} (${elsewhere.length} row(s)) · checking it`);
      return checkMetaList(item, pg, other, null, 'resumed', elsewhere);
    }
    await pg.go(list, `${BS}/posts/`);
    const rows = await pg.step('findScheduled', [item.caption, item.caption_ig]);
    const found = rows.filter((r) => r.match);
    if (item.video_id || found.length) {
      await say(`Already ${when ? 'scheduled' : 'posted'} (${found.length} row(s)) · checking it`);
      return checkMetaList(item, pg, list, when, 'resumed', found);
    }
    const slot = when && listTime(when, item.tz);
    const taken = rows.filter((r) => slot && r.date === slot && item.targets.includes(r.platform));
    if (taken.length) {
      const what = taken.map((r) => `${r.platform} "${r.blank ? '(no caption)' : r.title.slice(0, 40)}"`).join(', ');
      throw new Error(`${slot} already has ${what} in ${list}: not posting a second reel (fix or remove it there, or move this item)`);
    }
  }
  await say('Opening the Reel composer…');
  await pg.go(`${BS}/reels_composer/?${q}`, `${BS}/reels_composer/`);
  await pg.main(hookFileInputs);
  await pg.step('ready');
  const who = await pg.step('whoami');
  if (who.id !== a.asset_id || !accountMatches(item.account, who)) {
    throw new Error(`composer is on "${who.name}" (${who.id}), item wants "${item.account}" (${a.asset_id})`);
  }
  const targets = await pg.step('setTargets', item.targets);
  await say(`${who.name}${who.ig ? ` + ${who.ig}` : ''} ✓ · ${targets.join('+')} · moving video into the tab…`);
  await pg.send('video', item.video, (p) => say(`Moving video into the tab ${p}%`));
  await pg.step('setVideo', item.video.name, mimeOf(item.video.file));
  const end = Date.now() + UPLOAD_TIMEOUT_MS;
  let up = await pg.step('progress', item.video.name);
  let lastPct = -1, lastMove = Date.now(), retries = 0;
  for (; up.uploading; up = await pg.step('progress', item.video.name)) {
    if (up.pct !== lastPct) { lastPct = up.pct; lastMove = Date.now(); }
    // Still 0% after 90 s: the composer never took the file (it still shows the "Upload video" prompt). Send it again.
    if (up.pct === 0 && retries < 2 && Date.now() - lastMove > 90000) {
      retries++;
      await say(`No upload progress after 90 s, sending the video again (${retries}/2)…`);
      try {
        await pg.send('video', item.video, (p) => say(`Moving video into the tab ${p}%`));
        await pg.step('setVideo', item.video.name, mimeOf(item.video.file));
      } catch (e) { await say(`retry failed: ${e.message}`); }
      lastMove = Date.now();
    }
    if (Date.now() - lastMove > 5 * 60000) throw new Error(`upload stalled at ${up.pct}% for 5 min (progress bar: ${up.hasBar}; page: "${up.snap}")`);
    if (Date.now() > end) throw new Error(`upload did not finish within 60 min (${up.pct}%)`);
    await say(`Uploading ${up.pct}%`);
    await new Promise((r) => setTimeout(r, 2000));
  }
  if (up.failed) throw new Error(up.failed);
  // Thumbnail first: switching the thumbnail tab re-renders "Reel details" and drops typed captions.
  if (item.cover) {
    await say('Moving thumbnail into the tab…');
    await pg.send('cover', item.cover, (p) => say(`Moving thumbnail into the tab ${p}%`));
    try {
      await pg.step('setCover', item.cover.name, mimeOf(item.cover.file));
    } catch (e) {
      await say(`Thumbnail skipped (Meta default used): ${e.message}`.slice(0, 300));
    }
  }
  const captions = await pg.step('fill', item);
  await pg.step('checkCaptions', item);
  await pg.step('toShare');
  const at = metaWhen(when);
  const sch = await pg.step('schedule', at, item.tz);
  const { story } = await pg.step('extras');
  const note = [
    sch.mode === 'scheduled' ? sch.rows.map((r) => `${r.platform} ${r.date} ${r.time}`).join(', ') + ` (${sch.zone})` : 'share now',
    captions, up.check, story ? 'Facebook story share on' : null,
  ].filter(Boolean).join(' · ');
  await say(note);
  if (item.dry_run) return { status: 'dry-run', url: `${BS}/reels_composer/?${q}`, log: `${note} · form filled, not submitted (tab left open)` };
  // Marked on the server before the press: whatever happens next (no confirmation, the extension dies),
  // a retry finds video_id and only checks the list.
  stored.video_id = item.video_id = 'meta-submitted';
  const mark = await api(`/${item.id}/mark`, { video_id: stored.video_id });
  if (!mark.ok) throw new Error(`could not mark the item submitted (HTTP ${mark.status}): not pressing ${when ? 'Schedule' : 'Share'}`);
  const sent = await pg.step('submit');
  await say(`${sent.confirm} · checking the ${when ? 'Scheduled' : 'Published'} list`);
  await pg.go(list, `${BS}/posts/`);
  return checkMetaList(item, pg, list, at, note);
}

// Only the saved post counts: each target has a row with the caption, the time and a thumbnail.
// `when` = the time typed into the composer. A row at another time is still this item's post: it is
// done (never a second reel) and the log says the time differs, so the item leaves the queue.
async function checkMetaList(item, pg, list, when, note, rows) {
  let found = rows;
  // Few, slow reloads: a resumed check whose rows are missing will not find them by reloading
  // (2026-11-05: 10 reloads 6 s apart per captionless reel helped get Business Suite blocked).
  const tries = note === 'resumed' ? 2 : 4;
  for (let i = 0; i < tries && (!found || found.length < item.targets.length); i++) {
    if (i) {
      await new Promise((r) => setTimeout(r, 20000));
      await pg.go(list, `${BS}/posts/`);
    }
    found = (await pg.step('findScheduled', [item.caption, item.caption_ig])).filter((r) => r.match);
  }
  const checks = [];
  for (const t of item.targets) {
    const row = found.find((r) => r.platform === t);
    if (!row) throw new Error(`no ${t} row with this caption in ${list}${item.video_id ? ' (item is marked submitted, so it is never posted again; if nothing went out, clear its video_id)' : ''}`);
    if (!row.thumb) throw new Error(`${t} row has no thumbnail`);
    const off = when && row.date !== listTime(when, item.tz) ? ` ⚠ slot was ${listTime(when, item.tz)}` : '';
    checks.push(`${t} ${row.date || 'posted'}${off} ✓ thumbnail ✓`);
  }
  return { status: /published_posts/.test(list) ? 'posted' : 'scheduled', url: list, log: [note, ...checks].join(' · ') };
}

const TT_CONTENT = 'https://www.tiktok.com/tiktokstudio/content';

// TikTok Studio upload (one account per browser login, no switch here: the wrong @handle stops it).
// Like Meta: the content list is checked first, the item is marked before the press, and only a
// row with this caption at this time counts as done.
async function tiktokFlow(stored, pg) {
  const item = { ...stored, caption: titled(stored.title, stored.caption) };
  const say = (line) => progress(item.id, line);
  const when = item.schedule_at ? Date.parse(item.schedule_at) : null;
  await say('Opening TikTok Studio…');
  await pg.inject();
  await pg.step('ready');
  const who = await pg.step('whoami');
  if (!accountMatches(item.account, who)) {
    throw new Error(`TikTok is logged in as @${who.id}, item wants @${item.account.replace(/^@/, '')}: switch account on tiktok.com, then approve again`);
  }
  if (!item.dry_run) {
    await say(`@${who.id} ✓ · checking the post list…`);
    await pg.go(TT_CONTENT);
    const rows = await pg.step('findScheduled', item.caption);
    if (item.video_id || rows.some((r) => r.match)) {
      await say('Already on TikTok · checking it');
      return checkTiktokList(item, pg, when, 'resumed', rows);
    }
    const taken = when && rows.find((r) => r.at === when);
    if (taken) throw new Error(`${taken.line} already has "${taken.caption.slice(0, 40)}" (video ${taken.id}): not posting a second video at this slot`);
    await pg.go(ADAPTERS.tiktok.url);
    await pg.step('ready');
  }
  await say(`@${who.id} ✓ · moving video into the tab…`);
  await pg.send('video', item.video, (p) => say(`Moving video into the tab ${p}%`));
  await pg.step('setVideo', item.video.name, mimeOf(item.video.file));
  const end = Date.now() + UPLOAD_TIMEOUT_MS;
  let up = await pg.step('progress');
  for (; up.uploading; up = await pg.step('progress')) {
    if (up.failed) break;
    if (Date.now() > end) throw new Error(`upload did not finish within 60 min (${up.label})`);
    await say(up.label || 'Uploading…');
    await new Promise((r) => setTimeout(r, 3000));
  }
  if (up.failed) throw new Error(`TikTok upload failed: ${up.failed}`);
  const chars = await pg.step('fill', item);
  if (item.cover) {
    await pg.send('cover', item.cover, (p) => say(`Moving cover into the tab ${p}%`));
    await pg.step('setCover', item.cover.name, mimeOf(item.cover.file));
  }
  const sch = when ? await pg.step('schedule', when) : null;
  const note = [sch ? `scheduled ${sch.date} ${sch.time} ${sch.zone}` : 'post now', `caption ${chars}`,
    item.cover ? 'cover uploaded' : 'no cover'].join(' · ');
  await say(note);
  if (item.dry_run) return { status: 'dry-run', url: ADAPTERS.tiktok.url, log: `${note} · form filled, not submitted (tab left open)` };
  // Marked before the press: a retry finds video_id and only checks the list, never posts twice.
  stored.video_id = item.video_id = 'tiktok-submitted';
  const mark = await api(`/${item.id}/mark`, { video_id: stored.video_id });
  if (!mark.ok) throw new Error(`could not mark the item submitted (HTTP ${mark.status}): not pressing ${when ? 'Schedule' : 'Post'}`);
  const sent = await pg.step('submit');
  await say(`${sent.confirm} · checking the post list`);
  return checkTiktokList(item, pg, when, note);
}

// Only the saved post counts: a row with this caption (and, scheduled, at this time).
async function checkTiktokList(item, pg, when, note, rows) {
  let row = rows?.find((r) => r.match);
  for (let i = 0; i < 10 && !row; i++) {
    if (i) await new Promise((r) => setTimeout(r, 6000));
    await pg.go(TT_CONTENT);
    row = (await pg.step('findScheduled', item.caption)).find((r) => r.match);
  }
  if (!row) throw new Error(`no post with this caption in ${TT_CONTENT}${item.video_id ? ' (item is marked submitted, so it is never posted again; if nothing went out, clear its video_id)' : ''}`);
  if (when && row.at !== when) throw new Error(`video ${row.id} is "${row.line || 'not scheduled'}", wanted ${new Date(when).toISOString()}`);
  const url = `https://www.tiktok.com/@${item.account.replace(/^@/, '')}/video/${row.id}`;
  return { status: when ? 'scheduled' : 'posted', url, video_id: row.id,
    log: [note, `on TikTok as ${row.id}: ${row.line || 'posted'}`, row.thumb ? 'cover ✓' : 'no cover shown'].join(' · ') };
}

// Duplicate cleaner: a window on `account`'s Content > Shorts list, closed again when `fn` is done.
async function onChannelShorts(account, fn) {
  const adapter = ADAPTERS.youtube;
  // Studio's dashboard, not the upload page: no upload dialog to wait for.
  const STUDIO = 'https://studio.youtube.com/';
  const win = await chrome.windows.create({ url: STUDIO, focused: false, type: 'normal', left: 600, top: 40, width: 1280, height: 900 });
  const tabId = win.tabs[0].id;
  try {
    const pg = page(tabId, 'youtube', adapter);
    await pg.inject();
    await pg.step('studio');
    let who = await pg.step('whoami');
    if (!accountMatches(account, who)) {
      await pg.step('switchChannel', account);
      await pg.reopen(STUDIO);
      await pg.step('studio');
      who = await pg.step('whoami');
      if (!accountMatches(account, who)) throw new Error(`Studio is on "${who.name}", wanted "${account}"`);
    }
    await pg.go(`https://studio.youtube.com/channel/${who.id}/videos/short`);
    return await fn(pg);
  } finally {
    chrome.tabs.remove(tabId).catch(() => {});
  }
}

// Same-title groups on the channel: keep the copy the queue tracks, else the most public one; every
// other copy, and every lone draft, is offered for deletion (one click each in the panel).
const RANK = (vis) => [/public/i, /schedul/i, /unlisted/i, /private/i, /draft/i].findIndex((r) => r.test(vis)) + 1 || 9;
// Scan state lives in storage, not in the popup: opening the scan window closes the popup, and the
// user reopens it later to find the list (and each delete's outcome) still there.
// One writer at a time: Delete all fires many updates at once, a plain read-modify-write loses some.
let dupWrites = Promise.resolve();
function dupState(account, patch) {
  const run = dupWrites.then(async () => {
    const { dups = {} } = await chrome.storage.session.get('dups');
    dups[account] = typeof patch === 'function' ? patch(dups[account] || {}) : { ...(dups[account] || {}), ...patch };
    await chrome.storage.session.set({ dups });
  });
  dupWrites = run.catch(() => {});
  return run;
}

async function dupScan(account) {
  await dupState(account, { state: 'scanning', error: null, rows: [], at: Date.now() });
  try {
    const tracked = await (await fetch(`${QUEUE}/api/tracked`)).json();
    const rows = await onChannelShorts(account, (pg) => pg.step('uploads'));
    const groups = new Map();
    for (const r of rows) groups.set(fold(r.title), [...(groups.get(fold(r.title)) || []), r]);
    const out = [];
    for (const g of groups.values()) {
      if (g.length === 1) {
        if (/draft/i.test(g[0].vis) && !tracked[g[0].id]) out.push({ ...g[0], why: 'Draft, no published copy with this title' });
        continue;
      }
      // Only drafts, none tracked: leftovers of interrupted uploads, all of them go.
      const keep = g.find((r) => tracked[r.id]) || (g.every((r) => /draft/i.test(r.vis)) ? null
        : [...g].sort((a, b) => RANK(a.vis) - RANK(b.vis))[0]);
      if (!keep) { for (const r of g) out.push({ ...r, why: 'Draft, only drafts carry this title' }); continue; }
      for (const r of g) if (r !== keep && !tracked[r.id]) out.push({ ...r, why: `Extra copy · ${keep.id} (${keep.vis}) stays` });
    }
    await dupState(account, { state: 'done', total: rows.length, rows: out });
    return { total: rows.length, rows: out };
  } catch (e) {
    await dupState(account, { state: 'error', error: e.message });
    throw e;
  }
}

const rowState = (account, id, patch) => dupState(account, (d) => ({ ...d, rows: (d.rows || []).map((r) => (r.id === id ? { ...r, ...patch } : r)) }));

// Deletes collect per channel; one Studio window takes every id clicked so far (Delete all is one
// window, one channel read), checking each against that read, which it updates as rows go.
const delWant = new Map(); // account -> Map(id -> title)
async function dupDelete(account, id, title) {
  if (!delWant.has(account)) delWant.set(account, new Map());
  delWant.get(account).set(id, title);
  await rowState(account, id, { del: 'queued', delError: null });
  return ytQueued(() => dupDrain(account))();
}

async function dupDrain(account) {
  const want = delWant.get(account);
  delWant.delete(account);
  if (!want?.size) return;
  const fail = (id, e) => rowState(account, id, { del: 'error', delError: e.message || String(e) });
  let tracked;
  try { tracked = await (await fetch(`${QUEUE}/api/tracked`)).json(); } catch (e) {
    for (const id of want.keys()) await fail(id, e);
    return;
  }
  try {
    await onChannelShorts(account, async (pg) => {
      let rows = await pg.step('uploads');
      const shorts = `https://studio.youtube.com/channel/${(await pg.step('whoami')).id}/videos/short`;
      for (const [id, title] of want) {
        try {
          await rowState(account, id, { del: 'deleting' });
          if (tracked[id]) throw new Error(`${id} is the copy the queue tracks (${tracked[id].item}): not deleted`);
          const me = rows.find((r) => r.id === id);
          if (!me) throw new Error(`${id} is not on the channel any more`);
          // Never the last copy of a title unless it is a draft.
          if (!/draft/i.test(me.vis) && !rows.some((r) => r.id !== id && fold(r.title) === fold(me.title))) {
            throw new Error(`${id} is the only copy of "${me.title}": not deleted`);
          }
          await pg.go(shorts);
          await pg.step('deleteForever', id, title);
          rows = rows.filter((r) => r.id !== id);
          await rowState(account, id, { del: 'deleted' });
        } catch (e) { await fail(id, e); }
      }
    });
  } catch (e) {
    for (const [id] of want) {
      const { dups = {} } = await chrome.storage.session.get('dups');
      const row = dups[account]?.rows?.find((r) => r.id === id);
      if (!row || row.del === 'queued' || row.del === 'deleting') await fail(id, e);
    }
  }
}

// Deletes wait their turn: one Studio window at a time, so clicking several rows quickly is fine.
let ytChain = Promise.resolve();
const ytQueued = (fn) => () => {
  const run = ytChain.then(ytIdle(fn));
  ytChain = run.catch(() => {});
  return run;
};

// A channel switch is login-wide: never while a YouTube post runs in another window.
const ytIdle = (fn) => async () => {
  if (laneBusy.youtube) throw new Error('a YouTube post is running: try again when it is done');
  laneBusy.youtube = LANES.youtube; // holds the auto queue off YouTube while this runs
  try { return await fn(); } finally { laneBusy.youtube = 0; }
};

// Posting runs here, not in the popup: the popup closes on blur, an upload must not.
chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  const run = {
    dupScan: ytQueued(() => dupScan(msg.account)),
    dupDelete: () => dupDelete(msg.account, msg.id, msg.title),
    approve: () => approve(msg.item, msg.edits || {}, true),
    discard: () => api(`/${msg.item.id}`, { status: 'discarded' }).then(refreshBadge),
    kick: () => refreshBadge(),
  }[msg.type];
  if (!run || sender.tab) return false;
  run().then((data) => reply({ data }), (e) => reply({ error: e.message }));
  return true;
});

chrome.alarms.create('badge', { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener(refreshBadge);
chrome.runtime.onStartup.addListener(refreshBadge);
chrome.runtime.onInstalled.addListener(refreshBadge);
