---
name: field-to-table
description: Make a 10-15 minute horizontal 16:9 healing film through museai in the slow Chinese countryside "field to table" genre - one young woman (A-Qiao, character bank) and her dog spend a whole quiet day turning one thing from the hills, field, stream or tree into food or a handmade thing (gather, wash, dry, roast, pound, steam, press, dye, weave), then enjoy it at dusk. No narration, no dialogue: real close-miked sound, soft guzheng and bamboo flute, small cream chapter cards. Plus a ~15 s 9:16 hook short cut from the same clips, and 16:9 + 9:16 thumbnails. Picks from a 1000-idea bank (103 subjects x 12 settings x 12 threads) with a history so no subject, setting or thread repeats too soon. Use for "field to table video", "slow countryside cooking video", "video like li ziqi's channel", "ingredient from harvest to meal", "10-15 minute healing video", "long healing cooking video", "rural craft video", or the next one of these.
---

# field-to-table

Paths are relative to this folder. It is a long-form mode of `../healing-longform/` and reuses its scripts:
`plan.py` (refs -> stills -> clips, idempotent) and `longform.py` (compose). Server, render queue, quota and
delivery come from `../muse-video/SKILL.md`; the woman is `AQIAO` in `../character-bank/` (hero + full kept).
Work folder `~/Movies/museai/healing-<slug>/`. PIL scripts (`longform.py`, `short.py`, `cover.py`) run with
`~/.local/share/ace-step/venv/bin/python` (it has Pillow; the project venv does not).

## The genre (studied 2026-11 from the big Chinese countryside channels)

What holds viewers for 12-15 minutes with no words:
- **One subject, its whole life.** One ingredient or material followed from where it grows to what it becomes:
  chestnut burrs on the slope -> washed in the stream -> sun-dried -> sand-roasted -> pounded into cakes -> eaten
  at dusk. The viewer's question is "what will she make of it?", answered three or four times.
- **Process is the plot.** Each stage is a small satisfying transformation: a burr opening under a shoe, syrup
  hitting hot chestnuts, a cake tapped out of a wooden mould, a lid lifted in a cloud of steam. One per shot.
- **Seasons and places, not people.** Wide breathing shots of mist, hills, bamboo, rain - about one in six beats.
  Nobody but her (and the dog) is ever seen. No faces to camera, no talking, no music video poses.
- **Sound is half the film.** Leaves under cloth shoes, water, fire crackling, a spatula in the wok, chopsticks on
  a bowl. The clips' own sound is the bed; music sits far underneath.
- **A meal at the end.** Everything made today on one table at dusk, a plain warm bulb, the dog waiting. It is
  the reward the viewer waited for: hold it, never rush it.
- **Restraint.** Small cream chapter cards only; no subtitles, no stickers, no zooms, no hard sell.
- Variants that work the same way: crafts (indigo dye, paper, a bamboo basket, a quilt), preserves (rice wine,
  chilli paste, soy sauce), and festival days (zongzi, mooncakes, new year goods). The bank holds all four.

Never copy a real creator: original woman (A-Qiao), original dog (Doudou), our own titles. No "The life of X"
titles (another channel's series name).

## Rules that keep it from looking AI

From `../healing-longform/` lessons plus these:
- Locked-off camera in every clip (`plan.py` adds the CAMERA sentence); motion is inside the frame.
- Close-ups start with "Close-up" / "Top-down close-up" (no place ref, else muse widens the frame).
- Hands-only shots say "her hands" (plan.py frames them: no face). Name sleeves.
- No knives, no cutting: things are already cut, or split by hand, pounded, pressed, poured.
- No live animals handled, no killing; meat only already prepared. No other people.
- Bait words are rejected by `scripts/shot` (glow, cozy, cinematic, candle, sparkle, knife, ...): write "red-hot
  charcoal", "ripples", "a plain warm bulb".
- Refs: `plan.py ref` adds "nobody in the frame" (the look file describes her; without it she appeared in the
  kitchen and clay-pot refs).
- Food continuity: every shot names what the container holds and its state (raw / roasted / peeled).

## Steps

1. **Pick an idea.** `python3 scripts/ideas.py next --season now` (or `--kind craft|preserve|festival`). Turn
   its `chapters` into 5 chapters and 65-80 beats (12-14 % stills: wides and finished-food still life; the rest
   clips). Copy `stories/chestnut-day.json` as the template; add `"look": "field-to-table/prompt/look.txt"`,
   `cast: ["AQIAO"]` when she is in frame, `hold` 9-9.5 s per beat (11 s on chapter openers, 12 s on the last).
   75 beats x 9.5 s = ~12 min.
2. **Plan + render**, detached, from the work folder (`H=../healing-longform/scripts`):
   ```bash
   python3 $H/plan.py jobs story.json
   Q=../muse-video/scripts/render-queue
   $Q -j 3 jobs-refs.txt && $Q -j 3 jobs-stills.txt && $Q -j 2 jobs-clips.txt
   ```
   Look at the refs sheet before stills, and a stills sheet before clips (her braid over the RIGHT shoulder,
   outfit of that time, nobody else, no door frames, containers full). Delete a bad `stills/sN.png`, fix the
   beat, re-run its job.
3. **Music** (background, local ACE-Step, not muse quota): two or three 300 s tracks on different seeds,
   joined with `scripts/music_chain.sh` so a 12-15 min film never hears a loop seam:
   `TAGS="soft solo guzheng ... no vocals" ../healing-video/scripts/music "<season> chinese countryside" mN.m4a 300 <seed>`
   (exit 3 = calm gate rejected the take: next seed).
4. **Quota.** 60 clips is more than a day of muse video quota when other queues run. Don't loop on retries:
   `plan.py status story.json` lists missing clips; a missing clip composes as its still pushed in. Compose and
   deliver when the queue ends; re-run the clip queue after the quota resets and recompose (segments are cached).
5. **QA every clip** (`../muse-video/scripts/qa.py`, frame sheet): reject faces to camera, morphing hands, a second
   person, food that changes state wrongly, a moving camera. Re-render (delete `sN.mp4`, re-run its job) only a
   broken shot; trim a bad ending with the beat's `start`/`hold` instead.
6. **Compose** the long film:
   `python $H/longform.py story.json --music music.m4a --out healing-<slug>.mp4 --dry` (aim 600-900 s), then
   without `--dry`.
7. **Short** (9:16, ~15 s, from clips; a missing clip uses its still pushed in): fill `short` in story.json (5 shots `[beat, start, secs, x]`,
   strongest motion first, the meal last, hook text from the idea) and
   `python scripts/short.py story.json --music music.m4a --out healing-<slug>-short.mp4`.
8. **Thumbnails**: `../healing-video/scripts/cover.py --size 16:9 --at sN.mp4@auto --eyebrow "<eyebrow>"
   --title "<2-5 word hook>" --out thumbs/healing-<slug>_16x9.jpg`, and `--size 9:16` from the short. A still works too: make a 2 s mp4 of it with ffmpeg `-loop 1` first.
9. **Deliver** to `~/Desktop/field-to-table/<slug>/`: the 16:9 film, the 9:16 short, both thumbnails, and
   `story.json`. Copy the story to `stories/<slug>.json`, then `scripts/ideas.py record <id> --video <path>
   --slug <slug>`.

## Lessons

- 2026-11-17 (chestnut-day): AQIAO hero take 2 kept (take 1 slightly glossy); her braid comes out over the RIGHT
  shoulder, so the card and look say so.
- 2026-11-17 (chestnut-day): empty landscape wides (no cast) drift and grow a walking woman even with "Nobody is in
  the frame": say in `move` that only the mist/leaves move and no one walks in. Clips that drift or pop a prop in
  after ~5 s: keep them, cut the beat's `hold` to 5.5-6 s.
- 2026-11-17: frame-sheet QA must sample by time (`-ss 0.3/3.3/6.6/9.7`), not frame numbers: clips are 24 fps.
- 2026-11-17: food look drifts between stills (cakes pale-yellow in the kitchen, browned at the table): name the colour
  and "not browned" in every later beat with that food.
- 2026-11-17: shared muse accounts gave 9 clips in 2 h, then `upstream_timeout` after 1800 s with progress 0: the
  video quota was gone. Compose with still fallbacks, deliver, recompose after the reset.
