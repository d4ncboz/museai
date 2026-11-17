// The popup's list = the museai dashboard's "Ready to post" list. Pure: panel.js feeds it the queue
// items and the dashboard's /dashboard/posts videos; tests/test_postq_follow.py runs it under node.
//
// A dashboard video is open on a postq platform when one of that platform's boxes is in the video's
// `open` list (the dashboard computes it: not ticked yet, and in the channel's own platforms).
// Returns
//   items:   the queue items of open dashboard videos, in the dashboard's slot order, with the
//            dashboard's current slot time;
//   missing: open (video, platform) pairs with no queue item, so list + missing = the dashboard list;
//   off:     queue items the dashboard does not list (or lists as done there): not shown as cards;
//   dups:    a second queue item for the same video and platform (an older sync or a renamed folder
//            queued it twice): one card each, the approved one (else the oldest) shows.
const BOX_PLATFORM = { youtube: 'youtube', facebook: 'meta', instagram: 'meta', x: 'x', tiktok: 'tiktok' };
const META_AHEAD = 28 * 86400000 - 10 * 60000; // Business Suite schedules at most 28 days out (postq META_AHEAD)

// The feed's videos, each with its `open` list. A gateway started before `open` existed sends none: then
// it is what the dashboard page itself shows unticked, the channel's platforms minus the posted ones.
function dashboardVideos(feed) {
  const plats = new Map((feed.channels || []).map((c) => [c.id, c.platforms]));
  const all = (feed.platforms || []).map((p) => p.id ?? p);
  return (feed.videos || []).map((v) => (Array.isArray(v.open) ? v
    : { ...v, open: (plats.get(v.channel) || all).filter((p) => !(v.posted || {})[p]) }));
}

function followDashboard(items, videos, now = Date.now()) {
  const boxes = (v, p) => (v.open || []).filter((b) => BOX_PLATFORM[b] === p);
  const metaAt = (v) => v.schedule?.facebook || v.schedule?.instagram;
  const byName = new Map(videos.map((v, n) => [v.name, { n, v }]));
  const dash = (i) => byName.get(i.video?.name);
  const open = (i) => {
    const d = dash(i);
    const want = boxes(d?.v || {}, i.platform);
    return d && (i.targets?.length ? i.targets.some((t) => want.includes(t)) : want.length > 0);
  };
  const first = new Map();
  const dups = [];
  for (const i of [...items.filter(open)].sort((a, b) => !!b.auto - !!a.auto || String(a.id).localeCompare(String(b.id)))) {
    const k = i.platform + '|' + i.video.name;
    if (first.has(k)) dups.push(i);
    else first.set(k, i);
  }
  const shown = [...first.values()];
  const queued = new Set(first.keys());
  const missing = [];
  for (const v of videos)
    for (const p of [...new Set((v.open || []).map((b) => BOX_PLATFORM[b]).filter(Boolean))])
      if (!queued.has(p + '|' + v.name)) {
        const at = p === 'meta' && metaAt(v);
        const why = at && Date.parse(at) - now > META_AHEAD
          ? `queues on ${new Date(Date.parse(at) - META_AHEAD).toISOString().slice(0, 10)} (Meta: 28 days ahead at most)`
          : !v.slot ? 'no slot yet' : !v.folder ? 'not in its posting folder yet' : 'not queued yet';
        missing.push({ channel: v.channel, platform: p, name: v.name, slot: v.slot, why });
      }
  return {
    items: shown
      .sort((a, b) => dash(a).n - dash(b).n || a.platform.localeCompare(b.platform))
      // The time is the dashboard's current slot time (slots move; the queued schedule_at goes stale).
      .map((i) => ({ ...i, schedule_at: dash(i).v.schedule?.[i.platform === 'meta' ? 'facebook' : i.platform] || i.schedule_at })),
    missing,
    off: items.filter((i) => !open(i)),
    dups,
  };
}

if (typeof module !== 'undefined') module.exports = { followDashboard, dashboardVideos };
