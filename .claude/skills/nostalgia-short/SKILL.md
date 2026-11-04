---
name: nostalgia-short
description: Make a 30-45 s vertical nostalgia short of everyday life in an earlier decade ("1985. Just a normal Tuesday.") for Douyin, TikTok, Facebook and Reels - 10-16 calm 2-3.5 s period shots from morning to night (percolator and radio, paperboy on a bike, main street, typewriter, diner counter, full-service gas, kids on bikes at dusk, dinner at six, console TV, porch light), one short English + 中文 line per shot, hook first, a question last ("would you go back?"), warm 35 mm film grade with grain, an original instrumental ACE track or an ambience-only export for a licensed in-app song. Use for "nostalgia video", "last century lifestyle", "the 80s/90s/70s life", "怀旧", "video hoài niệm", "a day in 1985", "would you go back", or when the user wants everyday-life-in-the-past content that is NOT a drama with dialogue (that is american-everyday-stories). Files are named nostalgia-<slug>.
---

# nostalgia-short

Paths are relative to this folder (`.claude/skills/nostalgia-short/`). Server, retries, thumbnails, captions and delivery come from `../muse-video/SKILL.md` ("Format skills", shared steps 3-7). Name everything `nostalgia-<slug>`; the work folder is `~/Movies/museai/nostalgia-<slug>/`.

## Why this format (user, 2026-10-30)
The 16:9 Larkmont drama episodes (`../american-everyday-stories/`) lost viewers: they clicked and stopped watching. A short that is all mood and recognition keeps them: no story to follow, no dialogue, every shot a "we had that" moment.
- **30-45 s, never longer** (user rule). 13 shots x 2.3 s = 30 s; x 3.4 s = 44 s. `plan.py check` enforces it.
- **Hook in the first frame**: shot 1 carries the big line ("1985. Just a normal Tuesday."), upper middle.
- **One recognisable everyday thing per shot**, morning → night, so the video reads as one day.
- **End on a question** ("would you go back? / 你愿意回到那时候吗？"): comments push the reach.
- **Period facts must be true**: 1985 gas was about $1.20 a gallon, so the gas shot says "someone filled the tank for you", not "89 cents" (muse drew 89 cents on the pump anyway; the line does not repeat it).

## Music and copyright
Never pitch-shift, speed up, re-voice or otherwise alter someone else's song to slip past copyright detection, even when the user suggests it: it is still infringement, and Douyin/Facebook fingerprinting mutes or removes it anyway. Offer instead:
1. the original ACE instrumental (step 3), safe to post as is;
2. the ambience-only export (`compose.py` without `--music`), and the user picks the song from the platform's licensed in-app music library when posting.

## Steps
1. **Plan**: copy `plans/1985-tuesday.json` (the delivered 2026-10-30 video) and write a new day for the era or place the user asks for: `slug`, `era` (decade, season, place), `music`, and `shots` (`id`, `brief`, `en`, `zh`, optional `start`). Each brief names real period objects, the light, and the ONE action that happens. `python3 scripts/plan.py check plan.json [--shot 3.4]` must say OK. Show the user the hook, the shot list (one line each) and the closing line; render after a yes.
2. **Render** (one background call, one shot at a time through `render-queue`): `python3 scripts/plan.py render plan.json ~/Movies/museai/nostalgia-<slug>` (9:16, 6 s, `prompt/look.txt` appended, the `era` line first; `RETAKE=1` with ids to redo some). Logs end in `SAVED ...` per clip.
3. **Music** after the shots: `uv run --no-project ../muse-video/scripts/music.py --style "<plan music>, instrumental" --bpm 80 --body-beats <seconds x 1.4> --out ~/Movies/museai/nostalgia-<slug>/track.m4a`. The track must be at least as long as the video (+2 s).
4. **Check each clip**: mid-frame grid (`ffmpeg -ss 1.5 -i clip -frames:v 1`) at 1.5 s and 4 s for every clip. Reject: text, faces into the lens, warped hands, modern objects, a recognisable cartoon or show on a TV. A problem late in a clip is fine when the window (start + shot length) ends before it; set `start` in the plan.
5. **Compose**: `uv run --no-project --python 3.12 --with pillow python scripts/compose.py plan.json <work> nostalgia-<slug>.mp4 --music <work>/track.m4a [--shot 3.4]`, and without `--music` to `nostalgia-<slug>-nomusic.mp4` when the user wants the in-app song. It prints frames and MB: frames must equal seconds x 30.
6. **Deliver**: preview from the work folder, then shared step 7. Thumbnail: `../thumbnail/scripts/thumb.py travel <work>/thumb <work>/clips/<id>.mp4 --at <clip>@2.0 --title "1985" --hook "Just a normal Tuesday" --sub "Small-town America 🇺🇸"`; pick a frame without big brand logos. `FINAL=1` trashes the work folder: copy the plan and track elsewhere first if a longer or no-music version may follow.

## Lessons
- 2026-10-30, nostalgia-1985: a text PNG given to ffmpeg as one frame made `overlay=shortest=1` cut every shot to one frame (a 2-frame video that still reported 29.9 s). `compose.py` loops each PNG; check the printed frame count, not the duration.
- 2026-10-30, nostalgia-1985: moving film grain at crf 18 made a 30 s short 271 MB; `compose.py` now encodes with `-tune grain`, max 12 Mbit/s (~45 MB).
- 2026-10-30, nostalgia-1985: muse put a Peanuts-like cartoon on the console TV after 3 s; `prompt/look.txt` now asks for colour bars, static or a blurred news set on every screen.
