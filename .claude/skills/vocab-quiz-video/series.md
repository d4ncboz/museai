# Vocab quiz series — plan, design system, checks, analytics

## 1. Series plan

The end-card teaser must name an episode in this table that will really be made. Series restarted 2026-11-02: the two test renders of German A1 Travel were dropped. Every made episode goes into `log.md`.

| # | Language | Level | Topic | Next teaser | Status |
|---|---|---|---|---|---|
| 1 | German | A1 | Travel | A1 Food | made, not posted |
| 2 | German | A1 | Food | A1 City | made, not posted |
| 3 | German | A1 | City | A1 Home | made, not posted |
| 4 | German | A1 | Home | A1 Furniture | made, not posted |
| 5 | German | A1 | Furniture | A1 Drinks | made, not posted |
| 6 | German | A1 | Drinks | A1 Clothes | made, not posted |
| 7 | German | A1 | Clothes | A1 Family | made, not posted |
| 8 | German | A1 | Family | A1 Everyday Things | made, not posted |
| 9 | German | A1 | Everyday Things | A1 Groceries | made, not posted |
| 10 | German | A1 | Groceries | A1 Nature | made, not posted |
| 11 | German | A1 | Nature | A1 Getting Around | made, not posted |
| 12 | German | A1 | Getting Around | A1 Body | made, not posted |
| 13 | German | A1 | Body | A1 Kitchen | made, not posted |
| 14 | German | A1 | Kitchen | A1 Jobs | made, not posted |
| 15 | German | A1 | Jobs | | planned |

## 2. Design system

**Same in every episode and language:** everything in SKILL.md → "Episode format": 9:16 1080x1920, ~36 s fast cut (episodes 1-14: ~50 s baseline), 1.5 s hook and 4.5 s end with English narrator, 6 × 5 s words, `n/6` progress, circle countdown 2-1 with ticks, reveal chime, answer said once with "Listen & repeat" pause, recap + one score CTA + teaser, gender-colored articles, IPA only, one color grade, card and text sizes, safe zone, one video without background music (music added on TikTok), all text by ffmpeg.

**Per episode:** level, topic, words (picked by Claude from the official list, given to muse.ai in the prompt), scenery, next teaser.

**Per language:** the keys in `languages/<language>.md`: word list, answer form and colors, grammar check, pronunciation aid, font, text direction, TTS code, country for scenery.

**One format per episode, never mixed.** This series is English → target language (active recall). Possible later series: target language → English (recognition), image → target language (no English clue).

## 3. Before posting

No automatic checks after the render (the prompt gate is the quality step). **By the user:**
- [ ] Add music on TikTok: calm instrumental, no vocals, low enough that every word stays clear.
- [ ] Listen to every word: native-like, grammar marker (article) spoken, same loudness. Best: a fluent speaker checks stress, vowels and final consonants (review 2026-11-04 flagged Flugzeug, Fahrrad, Straße).
- [ ] Watch it on a phone at real size, sound low and muted: every text readable, nothing under the platform buttons.
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

### A/B test: fast cut vs. baseline (from the 2026-11-04 review)

Same words, new cut: episodes 1 (Travel) and 2 (Food) are re-rendered in the fast format as `german-a1-travel-fast.mp4` and `german-a1-food-fast.mp4`. Post each pair under similar conditions and compare: first-3-s hold, average % viewed, completion, comments/1k, follows/1k. Do not judge from a few hundred views. Retention alone does not show learning; ask a few learners which words they remember.

| Pair | Variant | Platform | Views | 3 s hold % | Avg % viewed | Completion % | Comments/1k |
|---|---|---|---|---|---|---|---|

Open question for the channel: **learning new words** (keep listen & repeat, slower) or **testing known words** (faster, game-style)? Let this data decide.
