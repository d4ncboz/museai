# Posting times per platform and content (researched 2026-10-29, revised 2026-11-04)

The dashboard's "Ready to post" schedule (`src/museai/api/routes/posting.py` `TIMES`, `AUDIENCE`) gives
each video a slot (day + slot 1 or 2, two a day per channel) and each platform its own time for that
slot. Each channel has its own table, because learning, travel, dream and healing videos are watched at
different moments by different audiences. Times are set in the audience's local time and shown in GMT+7.
Each channel's queue fills its free slots back to back; a slot whose video is posted on every platform
(or deleted) stays booked in `data/posts.json` and `data/post-history.jsonl`, so the next video takes
the slot after it.

## Whose clock
- **Chinese** (Vietnamese captions, Vietnamese learners): Vietnam, GMT+7, both slots. Slot 1 is the
  lunch break (user rule 2026-11-03: every platform, YouTube included), slot 2 the study hour after dinner.
- **Travel** and the other English formats (nostalgia, gown, product): English viewers. Slot 1 is in
  London time, slot 2 in New York time. Evening times fall on the audience's day before the calendar day
  (01-04 h and 06-10 h in GMT+7); the X and Threads mornings fall on the calendar day itself (16-23 h in
  GMT+7). Schedule them in each platform's scheduler.
- **Dream** (dream-life reels, their own account): US viewers, two slots a day in New York time. Slot 1,
  the US evening: the platform's best evening hour plus one, because about half of US viewers live west
  of New York (Central -1 h, Pacific -3 h; `dream-life/scripts/post_time.py` weights the zones by
  population), capped at 21-22 h; 08-10 h the next day in GMT+7. Slot 2, the US morning commute: the
  platforms' 6-9 h peaks, later on weekends; 18-23 h the same day in GMT+7.
- **Healing** (healing-video, its own account): a bedtime wind-down (ASMR / relaxation content peaks
  21-24 h), one slot a day, an hour after the dream evening; 08-10 h in GMT+7.

## Chinese lessons (GMT+7, slot 1 · slot 2)
| | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| YouTube Shorts | 11:30 · 20:00 | 11:30 · 20:00 | 11:30 · 20:00 | 11:30 · 20:00 | 11:30 · 19:00 | 11:00 · 19:00 | 11:00 · 20:00 |
| TikTok | 11:45 · 20:45 | 11:45 · 20:45 | 11:45 · 20:45 | 11:45 · 18:45 | 11:45 · 19:45 | 08:45 · 19:45 | 08:45 · 19:45 |
| Facebook Reels | 11:30 · 20:00 | 11:30 · 20:00 | 11:30 · 20:00 | 11:30 · 20:30 | 11:30 · 20:00 | 09:00 · 20:00 | 09:00 · 19:30 |
| Instagram Reels | 12:00 · 20:00 | 12:00 · 20:00 | 12:00 · 19:00 | 09:00 · 20:00 | 12:00 · 21:00 | 11:00 · 21:00 | 11:00 · 21:00 |
| X | 09:00 · 12:00 | 09:00 · 12:00 | 10:00 · 12:00 | 09:00 · 12:00 | 09:00 · 12:00 | 09:00 · 12:00 | 09:00 · 12:00 |
| Threads | 09:00 · 12:00 | 09:00 · 11:00 | 09:00 · 12:00 | 09:00 · 11:00 | 09:00 · 11:00 | 09:00 · 11:00 | 11:00 · 13:00 |

## Travel (slot 1 London · slot 2 New York, both local, audience weekday)
| | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| YouTube Shorts | 19:00 · 20:00 | 19:00 · 20:00 | 19:00 · 19:00 | 19:00 · 19:00 | 18:00 · 18:00 | 19:00 · 19:00 | 19:00 · 19:00 |
| TikTok | 17:45 · 18:45 | 17:45 · 18:45 | 17:45 · 19:45 | 18:45 · 18:45 | 17:45 · 17:45 | 17:00 · 16:45 | 17:45 · 18:45 |
| Facebook Reels | 19:00 · 21:00 | 19:00 · 19:00 | 18:00 · 18:00 | 19:00 · 20:00 | 18:00 · 18:00 | 21:00 · 22:00 | 20:00 · 20:00 |
| Instagram Reels | 19:00 · 19:00 | 19:00 · 19:00 | 18:00 · 18:00 | 19:00 · 20:00 | 21:00 · 21:00 | 21:00 · 21:00 | 21:00 · 21:00 |
| X | 09:00 · 09:00 | 09:00 · 09:00 | 10:00 · 10:00 | 09:00 · 09:00 | 09:00 · 09:00 | 09:00 · 09:00 | 09:00 · 09:00 |
| Threads | 12:00 · 11:00 | 10:00 · 11:00 | 12:00 · 11:00 | 09:00 · 11:00 | 10:00 · 11:00 | 10:00 · 11:00 | 11:00 · 11:00 |

## Dream life (New York, slot 1 evening · slot 2 morning)
| | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| YouTube Shorts | 21:00 · 07:00 | 21:00 · 07:00 | 20:00 · 07:00 | 20:00 · 07:00 | 19:00 · 07:00 | 20:00 · 09:00 | 20:00 · 09:00 |
| TikTok | 19:45 · 06:45 | 19:45 · 05:45 | 20:45 · 05:45 | 19:45 · 05:45 | 18:45 · 06:45 | 17:45 · 08:45 | 19:45 · 08:45 |
| Facebook Reels | 21:00 · 08:00 | 20:00 · 08:00 | 20:00 · 08:00 | 21:00 · 09:00 | 20:00 · 08:00 | 22:00 · 09:00 | 21:00 · 10:00 |
| Instagram Reels | 20:00 · 07:00 | 20:00 · 07:00 | 19:00 · 08:00 | 21:00 · 08:00 | 21:00 · 06:00 | 21:00 · 09:00 | 21:00 · 09:00 |
| X | 21:00 · 09:00 | 21:00 · 09:00 | 21:00 · 10:00 | 21:00 · 09:00 | 21:00 · 09:00 | 21:00 · 09:00 | 21:00 · 09:00 |
| Threads | 12:00 · 09:00 | 12:00 · 10:00 | 12:00 · 09:00 | 12:00 · 09:00 | 12:00 · 10:00 | 12:00 · 10:00 | 12:00 · 11:00 |

## Healing (New York, one slot)
| | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| YouTube Shorts | 21:00 | 21:00 | 21:00 | 21:00 | 20:00 | 21:00 | 21:00 |
| TikTok | 21:45 | 21:45 | 21:45 | 21:45 | 21:45 | 20:45 | 20:45 |
| Facebook Reels | 21:00 | 21:00 | 21:00 | 21:00 | 21:00 | 22:00 | 21:00 |
| Instagram Reels | 21:00 | 21:00 | 21:00 | 21:00 | 22:00 | 22:00 | 22:00 |
| X | 21:00 | 21:00 | 21:00 | 21:00 | 21:00 | 21:00 | 21:00 |
| Threads | 12:00 | 12:00 | 12:00 | 12:00 | 12:00 | 12:00 | 12:00 |

The slot's day and its free / taken / passed state follow YouTube's time.

## Why (per platform, 2026 data)
- **YouTube Shorts** (Buffer, 1.8M videos, July 2026, Shorts split out): peak 18-23 h; worst 12-17 h,
  Friday aside (16, 18, 19 h are its top three). Best per weekday: Mon 20, Tue 20, Wed 19, Thu 19, Fri 16/18,
  Sat 19 (and 11), Sun 19. SocialPilot (7M posts): weekend mornings 9-11 h. The Chinese lunch slot is a
  user rule, placed at 11:30 to go out before the 12-17 h dip. Shorts product lead Todd Sherman: time of
  day is "not a factor to optimize for"; a Short is seeded to a small audience and resurfaces for days.
- **TikTok** (Buffer, 7.1M posts, Sept 2026; Sprout, ~2B engagements): engagement peaks 18-23 h most
  days; Buffer's top hours Mon 13, Tue 6/22, Wed 22, Thu 13/22, Fri 18, Sat 17, Sun 9. Vietnam (TAKI
  Academy / IMH, 100K videos; Seongon): daily 6-9, 11:30-13:30 and 18-22 h, Thursday 19 h the week's
  peak, 13-17 h on weekdays worst. TikTok's Creator Academy says to post up to two hours before the
  audience's peak; the first test batch decides the push, so TikTok posts 15 minutes before the hour.
- **Facebook Reels** (Buffer, 14M posts; Metricool; PostFast via TAKI): feed posts peak in the
  morning, but Reels earn most 17-22 h (PostFast: +45 % views at 17-19 h; Sprout: 12-20 h); Vietnamese
  Reels 11:30-13 h and 20-22 h, Tuesday and Thursday evenings strongest. Saturday is the weakest day for
  the feed but Reels do fine late Saturday (Buffer 22 h, Metricool "Sat 00:00").
- **Instagram Reels** (Buffer, 9.6M posts, Sept 2026; Adobe Express, 20,247 Reels): evenings 18-23 h,
  Wednesday noon and Thursday 8-9 h; Friday to Sunday peak later (21-22 h). Adobe: the hour matters far
  more than the weekday (best vs worst hour: 109 % vs 17.6 % of average views). Mosseri: the top ranking
  signals are watch time, likes per reach and sends per reach; post 30-60 minutes before the audience
  comes online, Trial Reels test with non-followers first.
- **X** (Buffer, 8.7M posts; Metricool, 2M+): mornings 9-11 h, Wednesday best, evenings 18-23 h
  weakest for text; Metricool finds 21 h best for video. The open-sourced ranker decays a post within
  hours (about a 6 h half-life), so X posts when the audience is live: the morning for Chinese and
  travel, 21 h for the dream and healing reels (video, evening audience).
- **Threads** (Buffer, 2.5M posts; Hootsuite, 1M): a daytime, midweek platform: noon and 9-11 h best,
  Wednesday and Thursday best days, weekends and 18-23 h worst. Threads never mirrors the reel evenings.
- **Niche** (CommentGrid's review of Buffer / Sprout / Hootsuite / Later / Adobe; IMH by industry):
  education 9-11 h and 12-14 h micro-learning (lunch); travel 16-18 h plus Sunday 20 h (trip planning);
  aesthetic / entertainment 19-23 h; ASMR and wind-down 21-24 h. UK evenings run later than US ones
  and UK Saturday is weakest; US Eastern peaks 17-23 h.

## How much the hour matters (checked 2026-11-01)
The hour is a small lever. A video with almost no views usually has another cause:
- **YouTube Shorts:** each Short goes to a seed audience, and reach grows if viewers watch rather than
  swipe away. Posting more per day unlocks nothing. Since 2026-10-01, original Shorts rank higher and
  re-uploads get less reach (OutlierKit's summary of YouTube's statements).
- **TikTok:** the newsroom post lists country setting and language as low-weight signals; completion
  counts most. An account set up in Vietnam that posts English travel reels sends a weak, mismatched
  signal. Keep the English channels' accounts, app language and region consistent with English viewers.
- **Instagram / Facebook Reels:** watch time, likes per reach and sends per reach rank; Meta's Facebook
  Reels ranking has no recency term, so the hour works only through early engagement.
- **Channel mix:** one account that posts lessons, travel, dream and healing videos confuses interest
  matching. Keep each account to one kind of video.
- **Hook and loop:** the first 1-2 s decide whether viewers stay. A replay loop raises completion.
- **API visibility:** auto-posts from an unaudited TikTok app or Google project are private
  (publishers/tiktok.py, youtube.py). Check that each post is public.

After two or three weeks, read each platform's own analytics for when the account's viewers are online
(`dream-life/scripts/post_time.py --insights` turns Instagram's "most active times" into a table), and
change `TIMES` if they differ.

## Sources
- Buffer, YouTube (1.8M videos): https://buffer.com/resources/best-time-to-post-on-youtube/
- Buffer, TikTok (7.1M posts): https://buffer.com/resources/best-time-to-post-on-tiktok/
- Buffer, Facebook (14M posts): https://buffer.com/resources/best-time-to-post-on-facebook/
- Buffer, Instagram (9.6M posts): https://buffer.com/resources/when-is-the-best-time-to-post-on-instagram/
- Buffer, X (8.7M posts): https://buffer.com/resources/best-time-to-post-on-twitter-x/
- Buffer, Threads (2.5M posts): https://buffer.com/resources/the-best-time-to-post-on-threads/
- Sprout Social 2026 (~2B engagements, 307K profiles): https://sproutsocial.com/insights/best-times-to-post-on-social-media/
- Hootsuite (1M posts, 118 countries): https://blog.hootsuite.com/best-time-to-post-on-social-media/
- Metricool 2026: https://metricool.com/best-time-to-post-social-networks/
- SocialPilot (7M posts, 50K accounts): https://www.socialpilot.co/insights/best-times-to-post-on-social-media
- Adobe Express, Instagram Reels (20,247 Reels): https://www.adobe.com/express/learn/blog/best-times-to-post-instagram-reels
- Influencer Marketing Hub, TikTok by industry and country: https://influencermarketinghub.com/best-times-to-post-on-tiktok/
- CommentGrid, best time by niche: https://commentgrid.com/blog/best-time-to-post-on-tiktok-and-instagram
- TAKI Academy, TikTok golden hours 2026 (VN): https://taki.vn/gio-vang-dang-tiktok-2026-bang-chuan-7-ngay-trong-tuan/
- TAKI Academy, Facebook golden hours 2026 (VN): https://taki.vn/gio-vang-dang-facebook-2026-bang-khung-gio-moi-nhat/
- Seongon, TikTok (VN): https://seongon.com/blog/tiktok/khung-gio-dang-tiktok.html
- Seongon, Facebook (VN): https://seongon.com/blog/facebook/khung-gio-vang-dang-bai-facebook.html
- TikTok Creator Academy, video performance: https://www.tiktok.com/creator-academy/article/analytics-tool-video-performance
- TikTok Newsroom, How TikTok recommends videos: https://newsroom.tiktok.com/how-tiktok-recommends-videos-for-you
- YouTube Shorts algorithm, in YouTube's words: https://outlierkit.com/resources/youtube-shorts-algorithm/
- Instagram ranking explained (Mosseri): https://about.instagram.com/blog/announcements/instagram-ranking-explained
- Meta Transparency Center, Facebook Reels ranking: https://transparency.meta.com/features/explaining-ranking/fb-reels/
- Meta Transparency Center, Threads feed: https://transparency.meta.com/features/explaining-ranking/ig-threads-feed
- X ranker source: https://github.com/twitter/the-algorithm
