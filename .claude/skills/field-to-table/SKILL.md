---
name: field-to-table
description: Make a 10-15 minute horizontal 16:9 healing film through museai in the slow "field to table" style learnt from the big countryside channels, with our healing channel's girl ELLIE and Pip the cat in her English country cottage - she walks into the wood, hedgerow, meadow or kitchen garden with a basket, gathers dinner, cooks it and eats it at dusk by the window. No narration: real close-miked sound, soft piano and guitar, small cream chapter cards, fast human-edit cutting (two cuts per take, wide then punch-in, 0.4 s dissolves) and a 20-25 s cold open of the best moments with a hook line. Plus a ~15 s 9:16 hook short cut from the same clips, and 16:9 + 9:16 thumbnails. Picks from a 1000-idea cottage bank (and a 1000-idea Chinese countryside bank for the A-Qiao variant) with a history so no subject, setting or thread repeats too soon. Use for "field to table video", "slow countryside cooking video", "video like li ziqi's channel", "ingredient from harvest to meal", "10-15 minute healing video", "long healing cooking video", "rural craft video", or the next one of these.
---

# field-to-table

Paths are relative to this folder. It is a long-form mode of `../healing-longform/` and reuses its scripts:
`plan.py` (refs -> stills -> clips, idempotent) and `longform.py` (compose). Server, render queue, quota and
delivery come from `../muse-video/SKILL.md`. The woman is ELLIE (`../character-bank/`, the healing channel's girl:
braid over her LEFT shoulder) with Pip the cat, and the look is `../healing-longform/prompt/look.txt` (phone-camera,
real not AI): leave `look` out of story.json. `AQIAO` + `prompt/look.txt` is only the Chinese-countryside variant,
used when the user asks for it.
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

Learn the style, never the content: the user wants our own channel's girl and world, not a Chinese farmhouse
(2026-11-17, v1 with A-Qiao rejected). Never copy a real creator: our own woman, cat, titles. No "The life of X"
titles (another channel's series name).

## Pace and hook (2026-11-17 feedback: v1 "too slow, looks AI, weak hook")

- **Cut like a human editor.** Each clip beat has `cuts: [[0.3, 4.6], [5.0, 4.4, 1.32, x, y]]`: the wide part of the
  take, then a 1.32x punch-in of its second half centred on the hands (x, y), like a second camera. Stills 3.5-5 s.
  Story `xf: 0.4`. ~60 clips + ~12 stills = ~10.5 min, an average shot of ~4 s instead of 9.5 s.
- **Cold open.** Story `teaser`: 7-8 shots of 2.4-3.6 s from the best moments (the pour, the sizzle, the bubbling
  dish, her walking into the mist, the cat, her sitting down to eat) with one hook line that promises the payoff
  ("I walked into the woods with an empty basket. This is what we had for dinner."), then the title card.
- **Simple real actions** an ordinary person films: a boot in leaves, twisting a mushroom out of moss, butter
  foaming, a ladle pour. One action per shot; never a pose.

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

1. **Pick an idea.** `python3 scripts/ideas.py next --season now` (cottage bank; `--bank countryside` for the
   A-Qiao variant). Turn its `chapters` into 5 chapters and ~70 beats (~60 clips, ~12 stills). Copy
   `stories/forest-supper.json` as the template (`stories/gen-forest-supper.py` wrote it: edit a copy of the
   generator, it fills `cuts`, `teaser` and `short`); `cast: ["ELLIE"]` when she is in frame. Check the length with
   `longform.py --dry` (aim 600-750 s).
2. **Plan + render**, detached, from the work folder (`H=../healing-longform/scripts`):
   ```bash
   python3 $H/plan.py jobs story.json
   Q=../muse-video/scripts/render-queue
   $Q -j 3 jobs-refs.txt && $Q -j 3 jobs-stills.txt && $Q -j 2 jobs-clips.txt
   ```
   Look at the refs sheet before stills, and a stills sheet before clips (ELLIE's braid over the LEFT shoulder,
   outfit of that time, nobody else, no door frames, containers full). Delete a bad `stills/sN.png`, fix the
   beat, re-run its job.
3. **Music** (background, local ACE-Step, not muse quota): two or three 300 s tracks on different seeds,
   joined with `scripts/music_chain.sh` so a 12-15 min film never hears a loop seam:
   `TAGS="soft solo felt piano with gentle fingerpicked acoustic guitar, slow, warm, calm, no drums, no vocals"
   ../healing-video/scripts/music "<season> english countryside cottage" mN.m4a 300 <seed>`
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
- 2026-11-17 (forest-supper): a prop ref drags the shot to where the ref was shot (the basket ref on a worktop put
  the forest basket indoors): outdoors, leave the prop out and describe it with the ground it stands on. The
  opening empty wide still grew ELLIE's face: write "Wide empty landscape ..., no woman and no person anywhere".
