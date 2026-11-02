"""When to post dream-life reels: the posting time per platform and weekday for the dream account's
audience, and the first-weeks plan for a new account.

  python3 scripts/post_time.py                       # best New York time per platform and weekday
  python3 scripts/post_time.py --mix "New_York=.6,Chicago=.2,Los_Angeles=.2"
  python3 scripts/post_time.py --insights ig.json    # the account's own "most active times" instead
  python3 scripts/post_time.py --plan 2026-11-03 --ready 5 --per-week 5

Score of posting at hour h (New York clock), per platform and weekday:

  score(h) = sum over zones z of  share(z) * mean(curve(local_z(h + k)) for k in 0..window-1)

A Reel or Short is tested on a seed audience in its first hours, so a time scores well when those
first ``window`` hours fall in the peak of most of the audience, wherever it lives. curve() is 1.0 at
the platform's best hour that weekday (Buffer's 2026 studies, social-captions/references/posting-times.md),
0.7 in the evening window 18-23 h and 0.25 otherwise. --insights replaces curve() with the account's
own activity (Instagram Insights > Total followers > Most active times, 24 values per weekday), which
beats the study averages once the account has about 100 followers.

The posting.py ``TIMES["dream"]`` table is this script's default output.
"""

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HOME = ZoneInfo("America/New_York")
# US viewers by time zone (US Census 2020, rounded): the dream account speaks to US viewers first.
MIX = {
    "America/New_York": 0.47,
    "America/Chicago": 0.29,
    "America/Denver": 0.07,
    "America/Los_Angeles": 0.17,
}
# Best local hour per weekday (Monday first), from the Buffer studies the Travel table uses.
BEST = {
    "youtube": [20, 20, 19, 19, 18, 19, 19],
    "tiktok": [19, 19, 19, 18, 18, 18, 18],
    "facebook": [20, 20, 20, 20, 19, 20, 19],
    "instagram": [19, 19, 18, 20, 18, 19, 19],
    "x": [18, 18, 18, 18, 18, 18, 18],
    "threads": [18, 18, 18, 18, 18, 18, 18],
}
LEAD = {"tiktok": 15}  # minutes before the hour: TikTok's first test audience arrives with the peak
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def curve(platform, weekday, hour, insights=None):
    if insights:
        return insights[DAYS[weekday]][hour % 24]
    if hour == BEST[platform][weekday]:
        return 1.0
    return 0.7 if 18 <= hour <= 23 else 0.25


def score(platform, weekday, h, mix, window, insights=None):
    """Audience-weighted peak cover of the first ``window`` hours after posting at ``h`` (New York)."""
    base = datetime(
        2026, 11, 2 + weekday, h, tzinfo=HOME
    )  # 2026-11-02 is a Monday, after the DST end
    total = 0.0
    for zone, share in mix.items():
        cover = []
        for k in range(window):
            local = (base + timedelta(hours=k)).astimezone(ZoneInfo(zone))
            cover.append(curve(platform, local.weekday(), local.hour, insights))
        total += share * sum(cover) / window
    return total


def best_times(mix, window, insights=None):
    out = {}
    for p in BEST:
        week = []
        for d in range(7):
            h = max(range(6, 24), key=lambda h: (score(p, d, h, mix, window, insights), -h))
            hh, mm = divmod(h * 60 - LEAD.get(p, 0), 60)
            week.append(f"{hh:02d}:{mm:02d}")
        out[p] = week
    return out


def plan(start, ready, per_week, days=30):
    """Posting days of a new account's first ``days``: one reel a day while a finished video is
    waiting, never two (each post is one more seed-audience test, so the account learns its hooks
    fastest, and a second one the same day competes with the first). ``ready`` videos wait on day 1;
    ``per_week`` more are made each week, so once the stock runs out the rhythm settles at the
    production rate, spread evenly."""
    rows, stock = [], float(ready)
    for i in range(days):
        if stock >= 1:
            stock -= 1
            rows.append(start + timedelta(days=i))
        stock += per_week / 7
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mix", help='"Zone=share,..." (IANA names, America/ may be left out)')
    ap.add_argument(
        "--window", type=int, default=2, help="hours of seed-audience test after posting"
    )
    ap.add_argument("--insights", help="JSON {Mon: [24 activity values, New York clock], ...}")
    ap.add_argument("--plan", help="first posting day YYYY-MM-DD: print the 30-day plan")
    ap.add_argument("--ready", type=int, default=5, help="finished videos waiting on day 1")
    ap.add_argument("--per-week", type=int, default=5, help="videos made per week")
    a = ap.parse_args()
    mix = MIX
    if a.mix:
        mix = {}
        for part in a.mix.split(","):
            zone, share = part.split("=")
            mix[zone if "/" in zone else f"America/{zone}"] = float(share)
    insights = json.loads(Path(a.insights).read_text()) if a.insights else None
    if a.plan:
        rows = plan(date.fromisoformat(a.plan), a.ready, a.per_week)
        times = best_times(mix, a.window, insights)["instagram"]
        for d in rows:
            ny = datetime(
                d.year, d.month, d.day, *map(int, times[d.weekday()].split(":")), tzinfo=HOME
            )
            vn = ny.astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
            print(
                f"{d} {DAYS[d.weekday()]}  IG {times[d.weekday()]} New York = {vn:%a %H:%M} GMT+7"
            )
        print(f"{len(rows)} posts in 30 days")
        return
    for p, week in best_times(mix, a.window, insights).items():
        print(f"{p:10}", " ".join(f"{DAYS[d]} {t}" for d, t in enumerate(week)))


if __name__ == "__main__":
    main()
