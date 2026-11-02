# Posting times per platform and content (researched 2026-10-29, revised 2026-11-02)

The dashboard's "Ready to post" schedule (`src/museai/api/routes/posting.py` `TIMES`, `AUDIENCE`) gives
each video a slot (day + slot 1 or 2, two a day per channel) and each platform its own time for that
slot. Each channel has its own table, because learning and travel videos are watched at different
moments. Times are set in the audience's local time and shown in GMT+7. Each channel's queue fills its free
slots back to back (history: `data/post-history.jsonl`).

## Whose clock
- **Chinese** (Vietnamese captions, Vietnamese learners): Vietnam, GMT+7, both slots.
- **Dream** (dream-life reels, their own account): US viewers, two slots a day in New York time (from
  2026-11-02; a new account needs volume to fill YouTube's 90-day Shorts-views window, and 10+ hours
  apart each reel still gets its own seed test). Slot 1, the US evening, comes from
  `dream-life/scripts/post_time.py`, which weights the US time zones by population and scores each hour
  by how much of its first two hours falls in their evening peak (dream-life `references/account-kit.md`):
  New York 20-21 h = 08-09 h the next day in GMT+7. Slot 2 is the US morning commute, New York 08 h
  (10 h at weekends) = 19-22 h the same day in GMT+7.
- **Healing** (healing-video, its own account since 2026-11-02): the same US evening wind-down, one
  slot a day: slot 1 of the Dream table.
- **Travel** and the other English formats (nostalgia, gown, product): English viewers.
  Slot 1 is in London time, slot 2 in New York time, on the audience's day before the calendar day.
  Every travel time is 18:00 or later, so both land on the calendar day in GMT+7 (about 01-03 h and
  06-09 h). Schedule them in each platform's scheduler.

## Chinese lessons (GMT+7, slot 1 · slot 2)
| | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| YouTube Shorts | 17:00 · 20:00 | 19:00 · 21:00 | 19:00 · 21:00 | 19:00 · 21:00 | 16:00 · 19:00 | 11:00 · 19:00 | 17:00 · 20:00 |
| TikTok | 11:45 · 20:45 | 11:45 · 20:45 | 11:45 · 20:45 | 11:45 · 18:45 | 11:45 · 20:45 | 08:45 · 19:45 | 08:45 · 19:45 |
| Facebook Reels | 11:30 · 20:30 | 11:30 · 20:30 | 11:30 · 20:30 | 11:30 · 20:30 | 11:30 · 20:30 | 09:00 · 20:30 | 09:00 · 20:30 |
| Instagram Reels | 09:00 · 21:00 | 09:00 · 21:00 | 12:00 · 21:00 | 09:00 · 20:00 | 12:00 · 21:00 | 09:00 · 20:00 | 09:00 · 20:00 |
| X | 08:00 · 12:00 | 08:00 · 12:00 | 08:00 · 12:00 | 08:00 · 12:00 | 08:00 · 12:00 | 09:00 · 12:00 | 09:00 · 12:00 |
| Threads | 08:00 · 12:00 | 08:00 · 12:00 | 08:00 · 12:00 | 08:00 · 12:00 | 08:00 · 12:00 | 09:00 · 12:00 | 09:00 · 12:00 |

## Travel (slot 1 London · slot 2 New York, both local)
| | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| YouTube Shorts | 20:00 | 20:00 | 19:00 | 19:00 | 18:00 | 19:00 | 19:00 |
| TikTok | 19:45 | 19:45 | 19:45 | 18:45 | 18:45 | 18:45 | 18:45 |
| Facebook Reels | 20:00 | 20:00 | 20:00 | 20:00 | 19:00 | 20:00 | 19:00 |
| Instagram Reels | 19:00 | 19:00 | 18:00 | 20:00 | 18:00 | 19:00 | 19:00 |
| X, Threads | 18:00 | 18:00 | 18:00 | 18:00 | 18:00 | 18:00 | 18:00 |

The slot's day and its free / taken / passed state follow YouTube's time.

## Why
- **YouTube Shorts** (Buffer, 1.8M videos, 2026): Shorts peak 18-23 h; the worst hours are 12-17 h,
  except Friday, whose 16, 18 and 19 h are the week's top three. Best per day: Mon 20 h, Tue 20-21 h,
  Wed/Thu 19-21 h, Sat 19 h and 11 h, Sun 19-20 h, 17 h. Until 2026-11-02 the Chinese slot 1 posted
  Shorts at 11-12 h, in their weakest window: the main reason YouTube did badly. Shorts keep resurfacing
  for days, so the hour matters less than on TikTok.
- **Learning content** (TAKI Academy, VN; CommentGrid's review of Buffer, Sprout, Hootsuite, Later and
  Adobe data): learners watch in short breaks (lunch 12 h, morning 9-11 h, which wins on saves) and study
  after dinner (21 h); weekends 9 h and 20 h. Vietnamese TikTok peaks 19-22 h; posting 15 minutes before
  the peak gives the video its first test audience as viewers arrive (hence 11:45, 20:45). Thursday 19 h is
  Vietnam's top TikTok hour. OpusClip's 223K education clips cluster at the same lunch hours (creator
  activity, not engagement).
- **Travel content** (ReelReady travel niche; Buffer): travel is a wind-down and daydream watch: evenings,
  Friday for weekend trips (earlier, 18 h), Sunday evening for trip planning. TikTok gets 15 minutes'
  head start. X and Threads peak in the morning, but a morning in London or New York lands on the
  previous calendar day in GMT+7, so they take the earliest evening hour (18 h).
- **Facebook Reels** (Buffer, 14M posts; Seongon VN): Vietnamese Reels peak 11:30-13 h and 20-22 h.
- **Instagram Reels** (Buffer, 9.6M posts): 18-23 h, Wednesday noon, Thursday 8-9 h.
- **X / Threads** (Buffer, 8.7M / 2.5M posts): weekday mornings, early afternoon; evenings weakest.

## How much the hour matters (checked 2026-11-01)
The hour is a small lever. A video with almost no views usually has another cause:
- **YouTube Shorts:** each Short goes to a seed audience, and reach grows if viewers watch rather than
  swipe away. YouTube's Shorts product lead said time of day is "not something that we think about
  optimizing for", and that posting more per day unlocks nothing. Since 2026-10-01, original Shorts rank
  higher and re-uploads get less reach (OutlierKit's summary of YouTube's statements).
- **TikTok:** the newsroom post lists country setting and language as low-weight signals. It says a weak
  signal such as "the video's viewer and creator are both in the same country" counts less than
  completion. An account set up in Vietnam that posts English travel reels sends a weak, mismatched
  signal. Keep the English channel's account, app language and region consistent with English viewers.
- **Instagram / Facebook Reels:** Mosseri (January 2025) named watch time, likes per reach and sends per
  reach as the top ranking signals. Trial Reels show a reel to non-followers first, which tests a hook
  without followers.
- **Channel mix:** one account that posts lessons, travel, dream and healing videos confuses interest
  matching. Keep each account to one kind of video.
- **Hook and loop:** the first 1-2 s decide whether viewers stay. A replay loop raises completion.
- **API visibility:** auto-posts from an unaudited TikTok app or Google project are private
  (publishers/tiktok.py, youtube.py). Check that each post is public.

After two or three weeks, read each platform's own analytics for when the account's viewers are online,
and change `TIMES` if they differ.

## Sources
- TAKI Academy, TikTok golden hours 2026 (VN, education channels): https://taki.vn/gio-vang-dang-tiktok-2026-bang-chuan-7-ngay-trong-tuan/
- CommentGrid, best time by niche: https://commentgrid.com/blog/best-time-to-post-on-tiktok-and-instagram
- OpusClip, education & tutorials on TikTok: https://www.opus.pro/research/best-time-education-tutorials-tiktok
- ReelReady, travel creators: https://www.goreelready.com/tools/best-time-to-post/travel
- Buffer, YouTube: https://buffer.com/resources/best-time-to-post-on-youtube/
- Buffer, TikTok: https://buffer.com/resources/best-time-to-post-on-tiktok/
- Buffer, Facebook: https://buffer.com/resources/best-time-to-post-on-facebook/
- Buffer, Instagram: https://buffer.com/resources/when-is-the-best-time-to-post-on-instagram/
- Buffer, Threads: https://buffer.com/resources/the-best-time-to-post-on-threads/
- Sprout Social: https://sproutsocial.com/insights/best-times-to-post-on-social-media/
- TikTok Newsroom, How TikTok recommends videos: https://newsroom.tiktok.com/how-tiktok-recommends-videos-for-you
- YouTube Shorts algorithm, in YouTube's words: https://outlierkit.com/resources/youtube-shorts-algorithm/
- YouTube, Shorts algorithm Q&A with the Director of Shorts Product Management: https://www.youtube.com/watch?v=n3jsYK_-aRU
- Mosseri's Reels ranking signals (summary): https://hanamisocial.com/en/blog/instagram-reels-algorithm-2026/
- Seongon, TikTok (VN): https://seongon.com/blog/tiktok/khung-gio-dang-tiktok.html
- Seongon, Facebook (VN): https://seongon.com/blog/facebook/khung-gio-vang-dang-bai-facebook.html
