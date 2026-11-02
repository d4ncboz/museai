# Dream-life account kit (Instagram, Facebook, YouTube), 2026-11

One account per platform for dream-life reels only. Mixing them with travel or lessons confuses the
platforms' interest matching (social-captions/references/posting-times.md, "Channel mix"). The account is
AI-made and says so openly. Hiding it costs reach, and labelling costs nothing (see "AI disclosure").

## Name and handle
Check that the handle is free on all three platforms before you pick it. The same handle everywhere makes
the account easy to find.

| Option | Handle | Why |
|---|---|---|
| **Dream Jobs** (recommended) | `@dreamjobs.ai` / `@dreamjobsai` | The series in one word: every reel is a magical little job (star fisher, butterfly tailor). `.ai` says AI up front. |
| Soft Dream Life | `@softdreamlife` | Matches the cottagecore / soft-life search terms. |
| Tiny Magic Jobs | `@tinymagicjobs` | Funnier, fits the animal-jobs and rainbow-laundry ideas. |

Display name (searchable, shown above the bio): `Dream Jobs ✨ AI daydreams`.

## Bios
**Instagram** (150 characters max):
```
✨ magical little jobs from a dreamy life
🌙 AI-made daydreams · a new one every day
💌 comment the dream job you want next
```

**Facebook Page** (Intro, 101 characters max):
```
Magical little jobs from a dreamy life. AI-made daydreams, a new one every day. ✨
```
Category: *Digital creator*. "About" can repeat the YouTube description.

**YouTube** (channel description):
```
Welcome to Dream Jobs ✨

Every Short is a magical little job from a dreamy life: fishing for fallen stars, bottling sunlight
honey, sewing gowns from butterflies, drying rainbows on a washing line.

All videos are made with AI (images, motion and music) and edited by hand. No real people appear.

New dream every day. Tell me in the comments which dream job you want to see next.
```
YouTube handle = the Instagram handle. Channel keywords: `dream job, cozy, cottagecore, fairytale,
magical, soft life, daydream, AI art, aesthetic`.

## Profile picture and banner
- **Profile picture:** the recurring heroine from behind or in soft profile, holding a glowing star net,
  lavender sky. Make it with `scripts/shot lavender` (one still from a shot) and crop to a circle that
  reads at 110 px: one subject, no text.
- **YouTube banner** (2560 x 1440, keep everything in the centre 1546 x 423): a wide pastel meadow at
  golden hour with three small vignettes of past jobs (star net, honey jars, butterfly gown) and the line
  `a new dream job every day`.
- **Facebook cover** (1640 x 624 desktop, the centre 1200 x 624 on phones): the same art.

## Profile setup
- **Instagram:** switch to a professional account, type *Creator* (Insights, scheduling, Trial Reels).
  Turn on the **AI-generated profile label** in the account settings.
  Pin the 3 strongest reels once posted (start: butterfly tailor, animal jobs, star fisher).
- **Highlights:** `Dream jobs` (all reels), `How it's made` (the brief → shot → reel, which answers "is
  this real?"), `Vote next` (poll stories for the next job).
- **Facebook:** a Page, not a profile. Link Instagram in Accounts Center so a reel can be shared to both,
  but post the original file on each (no watermark from another app).
- **YouTube:** a brand channel. Upload defaults: category *Film & Animation*, not made for kids, altered
  content = Yes. One playlist per look (Pastel, Lavender) and one *All dream jobs*.

## AI disclosure (checked 2026-11-02)
- **Instagram:** label every reel (Advanced settings > *Add AI label*). Meta requires a label on
  photorealistic video made with AI. Since 2026-08-31, profiles that feature an AI-generated person should
  turn on the AI-generated profile label: labelled profiles keep their reach, while unlabelled ones that
  Instagram detects can stop being recommended.
- **Facebook:** the same label, from the same toggle when sharing from Instagram, or *AI info* in the
  reel composer.
- **YouTube:** the rule asks for disclosure only of *realistic* content, and a person fishing stars is
  clearly unrealistic. The heroine looks photoreal, though, so tick *altered or synthetic content* anyway:
  it costs nothing, and it protects the channel. YouTube does not monetize mass-produced, repetitive
  videos. Every dream reel has its own idea, shots and music, so keep it that way: never re-upload one
  reel with small changes.
- Say it in the bio too ("AI-made"). Viewers who learn it in the comments feel tricked, and that is
  the comment thread that spreads.

## Content pillars
1. **Dream jobs** (core, about 80 %): one magical job per reel, from the idea bank (`scripts/ideas.py
   next`), alternating Pastel and Lavender.
2. **Which would you pick?** (about 10 %): two jobs in one reel, with the hook in the caption ("star fisher or
   butterfly tailor?") so viewers comment.
3. **Seasonal dreams** (about 10 %): first snow, autumn harvest, spring blossom, timed a week before the
   season peaks.

Every caption ends with one question (which job next, which would you take). Comments and sends are what
Instagram ranks on, and sends count most for reaching people who don't follow you.

## When to post: the calculation
`python3 scripts/post_time.py` (run from the dream-life skill folder) calculates it. The dashboard's
**Dream** tab uses the same table (`posting.py` `TIMES["dream"]`).

1. **Whose evening:** the audience is US viewers. Their clocks are weighted by population: Eastern 47 %,
   Central 29 %, Mountain 7 %, Pacific 17 %.
2. **The first two hours decide reach:** a Reel or Short goes to a small seed audience first and spreads
   only if those viewers watch. So a posting time is scored by how much of its first two hours falls in
   each zone's peak:
   `score(h) = Σ zone share × average peak value over h, h+1 (in that zone's local time)`.
   The peak value is 1.0 at the platform's best hour that weekday (Buffer's 2026 studies of millions of
   posts), 0.7 for 18-23 h, and 0.25 otherwise.
3. **Pick the highest score**, ties to the earlier hour. TikTok posts 15 minutes early.

Result (New York time → your time, GMT+7, next morning):

| | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
|---|---|---|---|---|---|---|---|
| Instagram | 21:00 | 21:00 | 21:00 | 20:00 | 21:00 | 21:00 | 21:00 |
| Facebook | 20:00 | 20:00 | 20:00 | 20:00 | 21:00 | 20:00 | 21:00 |
| YouTube Shorts | 20:00 | 20:00 | 21:00 | 21:00 | 21:00 | 21:00 | 21:00 |

New York 21:00 = **09:00 next day in Vietnam** (08:00 from mid-March, when the US moves to summer time;
the dashboard converts the time itself). Schedule each post in the platform's own scheduler the night
before. After 14 days and about 100 followers, export Instagram Insights > *Most active times* into
`--insights` and use the account's own peaks instead of the study averages.

## How often: the new-account plan
`python3 scripts/post_time.py --plan <first day> --ready <finished videos> --per-week <videos made a week>`

- **One reel a day while a finished video is waiting, never two a day.** Each post is one more test on a
  seed audience, so a new account finds out which hooks work fastest. A second reel the same day competes
  with the first. YouTube's Shorts lead said posting more per day unlocks nothing.
- When the stock runs out, the rhythm settles at the production rate. Below 3 a week, a new account stays
  unknown to the platforms: 3-5 a week is the floor for growth on Instagram and YouTube.
- With 5 videos ready and 5 made each week, the first 15 days are daily, then about 5 a week:
  25 posts in 30 days.
- **Instagram Trial Reels** for experiments (a new look, a two-jobs reel): they go to non-followers only,
  and share to the profile only if they do well, so a weak test never reaches followers' feeds.

## First 30 days
| Days | Do |
|---|---|
| 0 | Set up all three profiles, AI labels, banner and highlights. Post 3 stories (intro, how it's made, poll for the first job). |
| 1-15 | One reel a day at the table's time on all three platforms. Reply to every comment in the first hour (the 09:00 GMT+7 slot is your morning). Pin the best 3. |
| 7, 14 | Review each reel: 3-second hold, average watch %, sends per reach, follows. Make more of the top 2 hooks; drop the bottom 2. |
| 15-30 | 5 a week. One Trial Reel a week testing a new idea type. Collab invite to one cozy/cottagecore account (Instagram Collab post: the reel shows on both profiles). |
| 30 | Swap the study times for Insights' *Most active times*. Keep the cadence that held reach per post; if reach per post fell more than 30 % while the cadence went up, go back down. |

## What not to do
- Don't cross-post the TikTok download (its watermark loses reach on Instagram and Facebook).
- Don't use more than 5 hashtags (Instagram's cap since 2025-12). Use topic tags: `#cottagecore #dreamjob
  #cozyvibes #fairytale #aiart`.
- Don't buy followers or use follow/unfollow bots: a new account's first audience decides who the
  platform shows it to next.
- Don't post the same reel twice. Instagram and Facebook stop recommending accounts that mostly repost.

## Sources
- Mosseri on Reels ranking (watch time, likes per reach, sends per reach) and Trial Reels: https://www.instagram.com/reel/DFDVhsivBGa/ ; https://highstyle.ai/insights/instagram-reels-algorithm-2026
- Posting cadence, what Instagram has said: https://www.taskant.com/how-many-times-a-day-should-you-post-on-instagram/
- Instagram AI labels and the AI-generated profile label (2026-08-31): https://iimagined.ai/blog/instagram-ai-label-rules-2026
- YouTube altered or synthetic content: https://blog.youtube/news-and-events/disclosing-ai-generated-content/ ; https://support.google.com/youtube/answer/14328491
- YouTube Shorts seed audience and cadence: https://outlierkit.com/resources/youtube-shorts-algorithm/ ; https://fliki.ai/blog/youtube-shorts-algorithm-explained
- Instagram 2026 changes (5 hashtags, repost exclusion): https://www.outfame.com/blog/instagram-algorithm-updates-2026-what-changed
- Best hours per platform: social-captions/references/posting-times.md (Buffer 2026)
