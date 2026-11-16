const QUEUE = 'http://127.0.0.1:8766';
const READY = new Set(['youtube', 'x', 'meta']); // platforms with an adapter (mirror of ADAPTERS in background.js)
const LIMITS = { youtube: { title: 100, caption: 5000 }, meta: { caption: 2200 }, tiktok: { caption: 2200 }, x: { caption: 280 } };
const list = document.getElementById('list');
const cards = new Map();

// <input type=datetime-local> works in this browser's zone: so does YouTube Studio's scheduler.
const toLocalInput = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;

function counter(input, max) {
  const el = document.createElement('span');
  el.className = 'count';
  const update = () => {
    el.textContent = `${input.value.length}/${max}`;
    el.classList.toggle('over', input.value.length > max);
  };
  input.addEventListener('input', update);
  update();
  return el;
}

function render(item) {
  const lim = LIMITS[item.platform] || {};
  const el = document.createElement('section');
  el.className = 'card';
  el.innerHTML = `
    <div class="meta"><span class="pill"></span><span class="who"></span><span class="pill dry" hidden>dry run</span><span class="pill state" hidden></span><span class="when"></span></div>
    <div class="top">
      <video muted controls preload="none"></video>
      <div class="fields">
        ${lim.title ? '<label>Title <input name="title"></label>' : ''}
        <label>${item.platform === 'youtube' ? 'Description' : 'Caption'} <textarea name="caption"></textarea></label>
        <div class="row">
          <label>Publish at (${zone}, empty = now) <input type="datetime-local" name="at"></label>
          ${item.platform === 'youtube' ? `<label>Related video <input name="related" placeholder="Tập 36 / latest:Tập"></label>` : ''}
          ${item.platform === 'youtube' ? `<label>Visibility <select name="visibility">
            <option>public</option><option>unlisted</option><option>private</option></select></label>` : ''}
        </div>
      </div>
    </div>
    <div class="row">
      <button class="primary" data-act="approve">Approve</button>
      <button data-act="discard">Discard</button>
      <label class="check"><input type="checkbox" name="dry"> dry run</label>
      <span class="status"></span>
    </div>`;
  const q = (s) => el.querySelector(s);
  const [platformPill, who, dryPill, badge, whenEl] = el.querySelectorAll('.meta > *');
  platformPill.textContent = item.platform + (item.targets?.length ? ` → ${item.targets.join(' + ')}` : '');
  who.textContent = item.account + (item.playlist ? ` · playlist: ${item.playlist}` : '');
  dryPill.hidden = !item.dry_run;
  whenEl.textContent = item.created;
  // No preload: 100+ cards each fetching video metadata made the popup open slowly. The cover is the poster.
  q('video').src = `${QUEUE}/media/${item.video.file}`;
  if (item.cover) q('video').poster = `${QUEUE}/media/${item.cover.file}`;
  const title = q('[name=title]');
  if (title) {
    title.value = item.title;
    title.parentElement.prepend(counter(title, lim.title));
  }
  const caption = q('[name=caption]');
  caption.value = item.caption;
  caption.parentElement.prepend(counter(caption, lim.caption));
  q('[name=at]').value = toLocalInput(item.schedule_at);
  if (q('[name=visibility]')) q('[name=visibility]').value = item.visibility;
  if (q('[name=related]')) q('[name=related]').value = item.related || '';
  q('[name=dry]').checked = item.dry_run;
  const c = { item, el, badge, status: q('.status'), buttons: [...el.querySelectorAll('button')] };
  c.edits = () => {
    const at = q('[name=at]').value;
    return {
      ...(title && { title: title.value }),
      caption: caption.value,
      schedule_at: at ? new Date(at).toISOString() : null,
      ...(q('[name=visibility]') && { visibility: q('[name=visibility]').value }),
      ...(q('[name=related]') && { related: q('[name=related]').value.trim() || null }),
      dry_run: q('[name=dry]').checked,
    };
  };
  q('[data-act=approve]').onclick = () => approve(c);
  q('[data-act=discard]').onclick = () => discard(c);
  if (!READY.has(item.platform)) {
    c.buttons[0].disabled = true;
    setStatus(c, '', `no ${item.platform} adapter yet`);
  } else if (item.auto) {
    // Already approved: the background posts these one by one, a channel at a time. Approving it
    // again here would start a second post next to that one, and the claim refuses it anyway.
    c.queued = true;
    setStatus(c, '', 'Approved · posts automatically in queue order');
  }
  // The last try's failure survives a closed popup and a restarted extension: shown until the next try.
  if (item.last_error && !c.queued) setStatus(c, 'bad', `Last try failed: ${item.last_error.replace(/\s+/g, ' ').slice(0, 200)}`);
  cards.set(item.id, c);
  list.append(el);
  if (c.queued) setState(c, 'approved');
}

// One visible state per card, so approved / posting / done / failed never look like an untouched card:
// the Approve button turns into a disabled label, the card gets a coloured edge and a badge.
const STATES = {
  approved: ['Approved ✓', 'queued'], posting: ['Posting…', 'posting'], done: ['Done ✓', 'done'], failed: ['Approve', 'failed'],
};
function setState(c, kind) {
  c.state = kind;
  const [label, cls] = STATES[kind] || ['Approve', ''];
  c.el.dataset.state = cls;
  c.buttons[0].textContent = label;
  c.buttons[0].disabled = kind !== 'failed';
  c.badge.hidden = !cls || kind === 'failed';
  c.badge.textContent = kind === 'approved' ? 'approved · queued' : kind === 'posting' ? 'posting now' : kind === 'done' ? 'posted' : '';
  c.el.style.display = shown(c) ? '' : 'none';
  renderSummary();
}
function renderSummary() {
  const all = [...cards.values()].filter((c) => READY.has(c.item.platform));
  const n = (k) => all.filter((c) => c.state === k).length;
  document.getElementById('sum').textContent =
    `${all.length - all.filter((c) => c.state && c.state !== 'failed').length} to approve · ${n('approved')} approved · ${n('posting')} posting · ${n('done')} posted`;
}

function setStatus(c, cls, line) {
  c.status.className = `status ${cls}`;
  const url = line.match(/https?:\/\/\S+/)?.[0];
  c.status.textContent = url ? line.replace(url, '') : line;
  if (url) c.status.append(Object.assign(document.createElement('a'), { href: url, target: '_blank', textContent: url }));
}

async function approve(c) {
  if (c.busy || c.done || c.queued || c.state === 'posting' || !READY.has(c.item.platform)) return;
  c.busy = true;
  c.buttons.forEach((b) => (b.disabled = true));
  setState(c, 'posting');
  c.buttons[0].disabled = true;
  setStatus(c, '', 'Starting…');
  const res = await chrome.runtime.sendMessage({ type: 'approve', item: c.item, edits: c.edits() });
  c.busy = false;
  if (res?.error) {
    // A claim refusal means another post (the auto queue) holds it: not an error the user caused.
    setStatus(c, /Already being posted/.test(res.error) ? '' : 'bad',
      /Already being posted/.test(res.error) ? 'In the auto queue (or posting now): nothing to do' : res.error);
    c.buttons.forEach((b) => (b.disabled = false));
    setState(c, 'failed');
  } else {
    c.done = true;
    setState(c, 'done');
    setStatus(c, 'ok', `${res.data.status}${res.data.url ? ` · ${res.data.url}` : ''}`);
  }
}

async function discard(c) {
  await chrome.runtime.sendMessage({ type: 'discard', item: c.item });
  c.el.remove();
  cards.delete(c.item.id);
  renderEmpty();
}

function renderEmpty(msg = 'Nothing pending. Queue with: postq add --platform youtube --account … --file v.mp4 --title …') {
  const empty = list.querySelector('.empty');
  if (cards.size) return empty?.remove();
  if (!empty) list.insertAdjacentHTML('beforeend', '<div class="empty"></div>');
  list.querySelector('.empty').textContent = msg;
}

// Live progress written by the background worker (also for posts started before this popup opened).
async function showProgress() {
  const { progress = {} } = await chrome.storage.session.get('progress');
  for (const [id, line] of Object.entries(progress)) {
    const c = cards.get(id);
    if (c && !c.done) {
      const failed = line.startsWith('failed');
      setStatus(c, failed ? 'bad' : '', line);
      if (failed) { if (!c.item.auto && !c.busy) setState(c, 'failed'); }
      else if (c.state !== 'posting') setState(c, 'posting');
    }
  }
}
chrome.storage.onChanged.addListener((ch, area) => area === 'session' && ch.progress && showProgress());

// Channel filter, across platforms: one brand at a time. A brand = the shortest account name that
// is a whole-word prefix of the others ("Dream Jobs" on Meta, "Dream Jobs Daily" on YouTube).
const chanSel = document.getElementById('chan');
let brands = [];
const brandOf = (a) => brands.find((b) => a === b || a?.startsWith(b + ' ')) || a;
const hideDone = document.getElementById('hide');
const platSel = document.getElementById('plat');
// Filter choices survive closing the popup (chrome.storage.local); saved.chan is applied once, when the channel list is built.
const saved = { chan: null };
const saveFilter = () => chrome.storage.local.set({ popupFilter: { chan: chanSel.value, plat: platSel.value, hide: hideDone.checked } }).catch(() => {});
const filterLoaded = chrome.storage.local.get('popupFilter').then(({ popupFilter: f }) => {
  if (!f) return;
  platSel.value = f.plat || '';
  hideDone.checked = !!f.hide;
  if (typeof f.chan === 'string') saved.chan = f.chan;
}).catch(() => {});
const shown = (c) => (!chanSel.value || brandOf(c.item.account) === chanSel.value)
  && (!platSel.value || c.item.platform === platSel.value)
  && !(hideDone.checked && ['approved', 'posting', 'done'].includes(c.state));
function renderFilter() {
  const names = [...new Set([...cards.values()].map((c) => c.item.account).filter(Boolean))]
    .sort((x, y) => x.length - y.length);
  brands = names.filter((n, i) => !names.slice(0, i).some((b) => n.startsWith(b + ' ')));
  const count = {};
  for (const c of cards.values()) { const k = brandOf(c.item.account); count[k] = (count[k] || 0) + 1; }
  const accounts = Object.keys(count).filter(Boolean).sort();
  const want = ['', ...accounts].map((a) => `${a}|${a ? count[a] : cards.size}`).join();
  if (chanSel.dataset.sig !== want) {
    const cur = saved.chan ?? chanSel.value;
    if (saved.chan === '') chanPicked = true;
    saved.chan = null;
    chanSel.replaceChildren(new Option(`All channels (${cards.size})`, ''),
      ...accounts.map((a) => new Option(`${a} (${count[a]})`, a)));
    // Opens on ONE channel (the Dream series first), never "All": the user picks All on purpose.
    const first = [...cards.values()].find((c) => c.item.channel === 'dream') || [...cards.values()][0];
    const dflt = first ? brandOf(first.item.account) : '';
    chanSel.value = chanPicked && cur === '' ? '' : accounts.includes(cur) ? cur : (accounts.includes(dflt) ? dflt : '');
    chanSel.dataset.sig = want;
  }
  for (const c of cards.values()) c.el.style.display = shown(c) ? '' : 'none';
  renderSummary();
}
let chanPicked = false;
chanSel.onchange = () => { chanPicked = true; saveFilter(); renderFilter(); };
platSel.onchange = () => { saveFilter(); renderFilter(); };
hideDone.onchange = () => { saveFilter(); renderFilter(); };

// The popup follows the museai dashboard list: only videos the dashboard lists, only platforms not yet
// ticked there, in slot order. The queue server queues every open dashboard video itself (postq sync_dashboard).
// Dashboard unreachable: the whole queue shows.
const DASH = 'http://127.0.0.1:18610/dashboard/posts';
async function followDashboard(items) {
  let videos;
  try {
    const res = await fetch(DASH, { signal: AbortSignal.timeout(4000) });
    videos = (await res.json()).videos;
  } catch { return items; }
  if (!Array.isArray(videos)) return items;
  // Meta schedules at most 28 days ahead: later slots stay out until the queue server can queue them.
  const farMeta = (i, d) => i.platform === 'meta' && Date.parse(d.schedule.facebook || d.schedule.instagram || 0) - Date.now() > 28 * 86400000;
  const byName = new Map(videos.map((v, n) => [v.name, { n, v, posted: v.posted || {}, schedule: v.schedule || {} }]));
  const dash = (i) => byName.get(i.video?.name);
  return items
    .filter((i) => {
      const d = dash(i);
      return d && !farMeta(i, d) && (i.targets?.length ? i.targets : [i.platform]).some((box) => !d.posted[box]);
    })
    .sort((a, b) => dash(a).n - dash(b).n)
    // The time is the dashboard's current slot time (slots move; the queued schedule_at goes stale).
    .map((i) => ({ ...i, schedule_at: dash(i).schedule[i.platform === 'meta' ? 'facebook' : i.platform] || i.schedule_at }));
}
let orderSig = '';
async function poll() {
  try {
    const items = await followDashboard(await (await fetch(`${QUEUE}/api/items`)).json());
    // An item whose approval was withdrawn (auto cleared in the queue) must not stay a stuck 'approved' card.
    for (const item of items) {
      const c = cards.get(item.id);
      if (c && c.queued && !item.auto && !c.busy && c.state !== 'posting') { c.el.remove(); cards.delete(item.id); }
    }
    for (const item of items) if (!cards.has(item.id)) render(item);
    const sig = items.map((i) => i.id).join();
    if (sig !== orderSig) {
      orderSig = sig;
      for (const i of items) { const c = cards.get(i.id); if (c) list.append(c.el); }
    }
    // Posted (or discarded) items leave the queue: drop their cards, the dashboard has them ticked.
    const live = new Set(items.map((i) => i.id));
    for (const [id, c] of cards) if (!live.has(id) && !c.busy) { c.el.remove(); cards.delete(id); }
    renderEmpty();
    renderFilter();
    showProgress();
  } catch {
    if (!cards.size) renderEmpty('Queue server not reachable. Run: postq serve');
  }
}

// All at once: each card is marked for auto-post with its edits, and the background starts them in
// parallel lanes (own window each), keeping YouTube on one channel at a time.
async function approveAll() {
  const todo = [...cards.values()].filter((c) => !c.busy && !c.done && !c.queued && c.state !== 'posting' && c.el.style.display !== 'none' && shown(c) && READY.has(c.item.platform));
  await Promise.all(todo.map(async (c) => {
    const res = await fetch(`${QUEUE}/api/items/${c.item.id}/approve`, {
      method: 'POST', headers: { 'X-Postq': '1', 'Content-Type': 'application/json' }, body: JSON.stringify(c.edits()),
    });
    if (!res.ok) return setStatus(c, 'bad', `approve failed (${res.status})`);
    c.queued = true;
    setStatus(c, '', 'Approved · starting in parallel');
    setState(c, 'approved');
  }));
  chrome.runtime.sendMessage({ type: 'kick' });
}
document.getElementById('all').onclick = approveAll;
document.addEventListener('keydown', (e) => {
  const inField = ['TEXTAREA', 'INPUT', 'SELECT', 'BUTTON', 'A'].includes(document.activeElement?.tagName);
  if (e.key === 'Enter' && !inField) { e.preventDefault(); approveAll(); }
});

// Duplicate cleaner: one button per channel starts a scan; each video then has its own delete button
// (press twice: never a bulk delete). State is kept by the background, so closing the popup (the scan
// window takes focus) loses nothing: reopen it to see the list and each delete's outcome.
const $id = (id) => document.getElementById(id);
const CHANNELS = ['Dream Jobs Daily', 'Blue Eyes Wander', 'Slow Sunlit Days', 'Chinese Everyday For Everyone'];
let dupOpen = false;
const dupAccounts = async () => {
  let tracked = {};
  try { tracked = await (await fetch(`${QUEUE}/api/tracked`)).json(); } catch { /* the four known channels still show */ }
  const queued = [...cards.values()].filter((c) => c.item.platform === 'youtube').map((c) => c.item.account);
  return [...new Set([...CHANNELS, ...Object.values(tracked).map((t) => t.account), ...queued].filter(Boolean))];
};

async function renderDups() {
  if (!dupOpen) return;
  const { dups = {} } = await chrome.storage.session.get('dups');
  const chips = $id('dupch');
  if (!chips.childElementCount) {
    for (const a of await dupAccounts()) {
      const b = Object.assign(document.createElement('button'), { className: 'chip', textContent: a });
      b.dataset.account = a;
      b.onclick = () => { chrome.runtime.sendMessage({ type: 'dupScan', account: a }); dupShown = a; renderDups(); };
      chips.append(b);
    }
  }
  const busy = Object.values(dups).some((d) => d.state === 'scanning');
  for (const b of chips.children) {
    const d = dups[b.dataset.account];
    b.classList.toggle('on', b.dataset.account === dupShown);
    b.disabled = busy;
    b.textContent = b.dataset.account + (d?.state === 'scanning' ? ' · scanning…' : d?.state === 'done' ? ` · ${d.rows.filter((r) => r.del !== 'deleted').length}` : '');
  }
  const d = dups[dupShown];
  const st = $id('dupst');
  const list = $id('duplist');
  list.replaceChildren();
  if (!dupShown || !d) { st.className = 'status'; st.textContent = dupShown ? `Starting the scan of ${dupShown}…` : 'Pick a channel to scan it (opens Studio in a background window, about 1 min).'; return; }
  if (d.state === 'scanning') { st.className = 'status'; st.textContent = `Scanning ${dupShown}… you can close this popup, the result waits here.`; return; }
  if (d.state === 'error') { st.className = 'status bad'; st.textContent = d.error; return; }
  const left = d.rows.filter((r) => r.del !== 'deleted').length;
  st.className = `status ${left ? '' : 'ok'}`;
  st.textContent = `${d.total} videos on ${dupShown} · ${left ? `${left} to clean up` : 'no duplicates left ✓'}`;
  // Delete all: same two presses as a row, then every listed video queues one by one (each still
  // re-checked by the background: tracked copy, last copy and title guards apply per video).
  const todo = d.rows.filter((r) => !r.del || r.del === 'error');
  if (todo.length > 1) {
    const all = Object.assign(document.createElement('button'), { className: 'danger', textContent: `Delete all ${todo.length}` });
    let armed;
    all.onclick = () => {
      if (!armed) {
        armed = setTimeout(() => { armed = null; all.textContent = `Delete all ${todo.length}`; all.classList.remove('armed'); }, 4000);
        all.textContent = `Sure? Delete ${todo.length} forever`;
        all.classList.add('armed');
        return;
      }
      clearTimeout(armed);
      all.disabled = true;
      all.textContent = 'Queued…';
      for (const r of todo) chrome.runtime.sendMessage({ type: 'dupDelete', account: dupShown, id: r.id, title: r.title });
    };
    const bar = document.createElement('div');
    bar.className = 'dupall';
    bar.append(all);
    list.append(bar);
  }
  for (const r of d.rows) {
    const el = document.createElement('div');
    el.className = `dup${r.del === 'deleted' ? ' gone' : ''}`;
    el.innerHTML = '<div class="dtop"><img><div class="dinfo"><b class="t"></b><div class="meta"><a target="_blank"></a><span class="v"></span></div><div class="meta w"></div></div><button class="danger"></button></div><div class="status"></div>';
    el.querySelector('img').src = `https://i.ytimg.com/vi/${r.id}/default.jpg`;
    el.querySelector('.t').textContent = r.title || '(no title)';
    Object.assign(el.querySelector('a'), { href: `https://studio.youtube.com/video/${r.id}/edit`, textContent: r.id });
    el.querySelector('.v').textContent = `${r.vis}${r.date ? ` · ${r.date}` : ''}`;
    el.querySelector('.w').textContent = r.why;
    const btn = el.querySelector('button');
    const rst = el.querySelector('.status');
    if (r.del === 'deleted') { btn.remove(); rst.className = 'status ok'; rst.textContent = 'Deleted ✓'; }
    else if (r.del === 'deleting' || r.del === 'queued') { btn.disabled = true; btn.textContent = r.del === 'queued' ? 'Queued…' : 'Deleting…'; }
    else {
      btn.textContent = 'Delete';
      if (r.del === 'error') { rst.className = 'status bad'; rst.textContent = r.delError; }
      let armed;
      btn.onclick = () => {
        if (!armed) {
          armed = setTimeout(() => { armed = null; btn.textContent = 'Delete'; btn.classList.remove('armed'); }, 4000);
          btn.textContent = 'Sure? Delete forever';
          btn.classList.add('armed');
          return;
        }
        clearTimeout(armed);
        btn.disabled = true;
        btn.textContent = 'Queued…';
        chrome.runtime.sendMessage({ type: 'dupDelete', account: dupShown, id: r.id, title: r.title });
      };
    }
    list.append(el);
  }
}
let dupShown = null;
$id('dups').onclick = async () => {
  dupOpen = !dupOpen;
  $id('dupbox').hidden = !dupOpen;
  $id('list').hidden = dupOpen;
  $id('dups').classList.toggle('on', dupOpen);
  if (dupOpen && !dupShown) {
    const { dups = {} } = await chrome.storage.session.get('dups');
    dupShown = Object.entries(dups).sort((x, y) => (y[1].at || 0) - (x[1].at || 0))[0]?.[0] || null;
  }
  renderDups();
};
chrome.storage.onChanged.addListener((ch, area) => area === 'session' && ch.dups && renderDups());

filterLoaded.then(poll);
setInterval(poll, 5000);
