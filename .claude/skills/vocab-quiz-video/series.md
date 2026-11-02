# Vocab quiz series — plan, design system, checks, analytics

## 1. Series plan

The end-card teaser must name an episode in this table that will really be made.

| # | Language | Level | Topic | Next teaser | Status | File |
|---|---|---|---|---|---|---|
| 1 | German | A1 | Travel | A1 Food | v2 made; v3 to render | `videos/german-a1-travel-v2.mp4` |
| 2 | German | A1 | Food | | planned | |

## 2. Design system

**Same in every episode and language:** everything in SKILL.md → "Episode format": 9:16 1080x1920, ~46.5 s, hook, 6 × 7 s words, `n/6` progress, circle countdown 3-2-1 with ticks, answer said twice with "Listen & repeat", score CTA + teaser, card and text sizes, safe zone, no music for now, all text by ffmpeg.

**Per episode:** level, topic, words (picked by muse.ai from the official list), scenery, next teaser.

**Per language:** the keys in `languages/<language>.md`: word list, answer form and colors, grammar check, pronunciation aid, font, text direction, TTS code, country for scenery.

**One format per episode, never mixed.** This series is English → target language (active recall). Possible later series: target language → English (recognition), image → target language (no English clue).

## 3. Checks before posting

**Automatic** (`scripts/check_video.sh`):
- 1080x1920, 30 fps, ~46.5 s.
- 3 ticks per word, 1 s apart.
- Speech-to-text of each answer, both times.
- Frame sheet: hook, countdown, answer, progress `n/6`, end card; no AI-made text; object visible.

**By the user:**
- [ ] Listen to every word: native-like, grammar marker (article) spoken, same loudness.
- [ ] Upload private/draft to **TikTok** and **YouTube Shorts**; no text under buttons or description.
- [ ] Spot-check 2 words against the official word list.
- [ ] Teaser names a planned episode (table above).

## 4. Analytics

Compare on each platform's analytics, not views alone. Change one major thing between compared episodes; compare similar difficulty on the same platform. Shorter is not automatically better.

| Metric | Where | Tells you |
|---|---|---|
| Viewed vs. swiped away | YouTube Shorts | Hook works? |
| Retention, first 3 s | both | Opening holds attention? |
| Average view duration | both | Pace right? |
| Completion rate | both | Viewers reach 6/6? |
| Rewatches | TikTok | Quiz invites replay? |
| Comments per 1,000 views | both | Score CTA works? |
| Follows per 1,000 views | both | Viewers want the next episode? |

Log 7 days after posting:

| Episode | Platform | Views | Avg. view duration | Completion % | Comments/1k | Follows/1k | Changed vs. previous |
|---|---|---|---|---|---|---|---|

Open question for the channel: **learning new words** (keep listen & repeat, slower) or **testing known words** (faster, game-style)? Let this data decide.
