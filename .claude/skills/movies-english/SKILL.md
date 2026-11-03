---
name: movies-english
description: Make "Movies English" reels - 15-30 s vertical AI rom-com micro-movies in a late-1990s Hollywood film look with a gorgeous recurring cast (Viv & Jamie, Sienna & Theo, Maya & Lucas), a few short witty lines, a twist ending, and one English key phrase per video taught with yellow-highlighted English captions, Vietnamese under them and a phrase card at the end. Holds a library of 1000 ready scripts, the cast bible, the build/render/finish pipeline through museai/muse-video, and the social growth plan. Use for "movies english", "english through movies", "learn English reel", "make video ME-0042", "next movies english video", "rom-com English lesson", or videos in the style of the user's EmmaRobins / Aspen ski / Christmas pyjama reference reels.
---

# Movies English

Paths are relative to this folder (`.claude/skills/movies-english/`). Rendering, server, retries and
delivery reuse `../muse-video/` (read its SKILL.md: Server, Generate one clip, Deliver). This skill keeps
only what is specific to the format.

| file | what it holds |
|---|---|
| `references/script-format.md` | the reference-reel measurements, the script JSON shape, the writing rules |
| `references/growth.md` | platforms, posting plan, engagement and monetisation |
| `series/cast.json` | the six recurring characters: identity (face), wardrobe sets, voice, comic engine |
| `prompt/look.txt` | late-1990s rom-com film look + 9:16 composition, appended to every shot prompt |
| `library/batch_NN.json` | 1000 scripts, `ME-0001`..`ME-1000` (00: 1, 01: 99, 02-10: 100 each) |
| `scripts/check.py` | library lint: counts, unique ids and phrases, phrase in a line, line length, timing |
| `scripts/build.py` | `ME-NNNN WORK` → still requests, shot prompts, `render.sh` |
| `scripts/stills.sh` | renders every still (two takes each) through `/v1/images/generations` |
| `scripts/finish.py` | Whisper trims, hard-cut assembly, hook, bilingual captions, phrase card |
| `posted.json` | ids already delivered (next video = the lowest id not in it, unless the user names one) |

## Make one video
`WORK=~/Movies/museai/me-NNNN`.
1. `python3 scripts/build.py ME-NNNN $WORK`, then `scripts/stills.sh $WORK` (background, 5-15 min).
2. Look at each still pair; copy the better take to `$WORK/stills/<name>.png`. Reject plastic skin,
   a famous-looking face, wrong wardrobe, text in the frame, a speaker facing away. Close-ups of one
   person share one still per episode: that is what keeps the face the same across cuts.
3. `$WORK/render.sh` in the background: every shot renders in parallel, one muse call each, through
   `../muse-video/scripts/muse-video` (quality block appended). Check each clip with
   `../muse-video/scripts/check_clip.sh`; re-render a failing shot once with `RETAKE=1`.
4. `uv run --no-project --python 3.12 --with faster-whisper --with pillow python scripts/finish.py $WORK $WORK/final.mp4`
   (optional `MUSIC=bed.m4a`, `HANDLE="@yourhandle"`). `MISHEARD` → re-render that shot.
5. Look at frames at every cue and the card: captions inside the lower band, no face covered,
   Vietnamese diacritics correct. Preview with `SendUserFile` (render).
6. On the user's OK: captions per platform (`../social-captions/`, Vietnamese, `cta_vi` as the
   question), thumbnails (`../thumbnail/`), `FINAL=1 ../muse-video/scripts/deliver.sh`, add the id to
   `posted.json`.

## Writing more scripts
Follow `references/script-format.md`; new ids continue after the last batch; `python3 scripts/check.py`
must pass (no phrase reused). Keep the comedy visual and the words few: the reference reels speak
2-5 lines of 2-7 words.

## Maintaining this skill
Same flow as muse-video "Maintaining this skill". Encode a lesson from a render or a user correction
as a check in `check.py` / `finish.py` or a line in `look.txt` / cast.json, not as more prose.
