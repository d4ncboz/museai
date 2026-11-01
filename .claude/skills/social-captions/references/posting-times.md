# Posting times per platform (researched 2026-10-29, revised 2026-11-01)

The dashboard's "Ready to post" schedule (`src/museai/api/routes/posting.py` `TIMES`, `AUDIENCE`) gives
each video a slot (day + slot 1 or 2, two a day per channel) and each platform its own time for that
slot. Times are set in the audience's local time and shown in GMT+7.

## Whose clock
- **Chinese** (Vietnamese captions, Vietnamese learners): Vietnam, GMT+7. Slot 1 is the left column of
  the table (midday), slot 2 the right column (evening).
- **Travel** and the other English formats (dream, healing, nostalgia, gown, product): English viewers.
  Slot 1 uses the evening column in London time (Europe's evening, US East lunch). Slot 2 uses the evening
  column in New York time. Both are the audience's day before the calendar day, so they land on the
  calendar day in GMT+7, at about 02-05 h and 06-10 h. Schedule them in each platform's scheduler.

Until 2026-11-01 every channel used GMT+7 times (11:30 / 18:00). Travel reels went out at 05:30 / 12:00
in London and 00:30 / 07:00 in New York, while their English-speaking audience was asleep or at work.

| Audience-local | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| YouTube Shorts | 12:00 · 20:00 | 12:00 · 20:00 | 12:00 · 19:00 | 12:00 · 19:00 | 12:00 · 17:00 | 11:00 · 19:00 | 11:00 · 19:00 |
| TikTok | 11:00 · 20:00 | 12:00 · 21:30 | 12:00 · 21:30 | 13:00 · 21:30 | 12:00 · 19:00 | 11:30 · 17:00 | 09:00 · 19:00 |
| Facebook Reels | 12:00 · 21:00 | 08:00 · 20:00 | 08:00 · 20:30 | 09:00 · 20:30 | 08:00 · 20:30 | 11:30 · 22:00 | 10:00 · 20:30 |
| Instagram Reels | 12:00 · 19:00 | 15:00 · 19:00 | 12:00 · 18:00 | 09:00 · 20:00 | 12:00 · 21:00 | 12:00 · 21:00 | 12:00 · 21:00 |
| X | 09:00 · 14:00 | 09:00 · 13:00 | 10:00 · 14:00 | 09:00 · 13:00 | 09:00 · 13:00 | 10:00 · 13:00 | 10:00 · 13:00 |
| Threads | 09:00 · 12:00 | 09:00 · 12:00 | 09:00 · 12:00 | 09:00 · 12:00 | 09:00 · 12:00 | 10:00 · 13:00 | 11:00 · 14:00 |

The slot's day and its free / taken / passed state follow YouTube's time. X and Threads peak in the
morning, so they may be due earlier than YouTube on the same slot.

## Why each row
- **YouTube Shorts** (Buffer, 1.8M videos, 2026): evenings 18-21 h, Friday 16-18 h, Saturday 11 h.
- **TikTok** (Buffer, 7.1M posts, 2026): evenings 18-23 h, Sunday 9 h peak, Thursday 13 h, Saturday 17 h.
  Vietnamese guides say 11-13 h and 19-22 h.
- **Facebook Reels** (Buffer, 14M posts, 2026): weekday mornings 7-9 h, Monday and Saturday late
  evening. Vietnamese guides for Reels say 20-22 h and 11:30-13 h.
- **Instagram Reels** (Buffer, 9.6M posts, 2026): 18-23 h, Wednesday noon, Thursday 8-9 h.
- **X** (Buffer, 8.7M posts): weekday mornings 9-11 h, early afternoon. Evenings and Saturday are weakest.
- **Threads** (Buffer, 2.5M posts): weekday mornings 6-11 h, Wednesday noon. Evenings are weakest.

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
