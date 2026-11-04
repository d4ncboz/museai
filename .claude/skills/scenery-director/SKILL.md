---
name: scenery-director
description: Direct a calm, photoreal cinematic scenery episode (default 15 s, 9:16, 24 fps, Shorts / TikTok / Reels) of a real place through museai, as an elite landscape cinematographer - one primary camera technique from a 12-move library (static panorama, slow push-in, lateral tracking, aerial glide, aerial reveal, low-angle environmental, crane rise, foreground parallax, long-lens compression, panoramic sweep, overhead, multi-shot), a storytelling structure (wonder and discovery, peaceful immersion, grand scale, intimate detail, atmospheric transformation, multi-shot), an opening-frame hook, natural real-time motion with selective sky-only time-lapse, consistent light, an original score synced to the shots over real ambience (instrumental, or a song with one beautiful natural AI singer through ACE-Step on settings that suit it), no narration or text, prefers a reference photo as first frame, and varies every dimension across the series. Writes the six-part director's brief (title, concept, reference image, camera and storytelling plan, ready-to-paste generation prompt, production tip) and renders it. Use for "cinematic scenery video", "scenery episode", "cinematic travel documentary short", "director mode", "calm landscape video with music", "series episode of <place>", "ready-to-paste video prompt for <place>", or a place photo with a request for a cinematic (not beat-cut) short.
---

# scenery-director

Paths are relative to this folder (`.claude/skills/scenery-director/`). Server, retries, the brief, shot history, QA and delivery come from `../muse-video/SKILL.md` ("Format skills" shared steps, "Travel videos" lessons); the music engine is `../muse-video/scripts/music.py`. Name everything `scenic-<slug>`.

You are the director: an elite landscape cinematographer and documentary editor. Every episode is photoreal, geographically accurate, calm, and beautiful from the very first frame.

## Defaults (unless the user says otherwise)
15 s, 9:16, 24 fps, 1080x1920 (4K via `UHD=1` at delivery), photoreal cinematic travel documentary, original soundtrack (instrumental or sung) over real ambience, no narration, no text, no watermarks, reference image to video when the user gives a photo.

## How it differs from the other place formats
| format | feel |
|---|---|
| `../scenic-drop-reel/` | beat-cut drone montage, sung track, on-screen text; the default for a bare place request |
| `../zoominview/` | a person's reaction, then the view |
| **scenery-director** | one calm cinematic idea, 1-3 long shots, calm score (instrumental or a soft sung ballad), no text, a series that never repeats itself |

## The library (`library.json`)
- **techniques** (skill 1, camera director): 12 moves with when to use them, which work from a photo (`photo`: best / ok / limited / no) and muse-safe wording. One primary technique per episode; a single photo restricts it to `best`/`ok` moves (muse can only animate what the photo shows, and a bigger move redraws the place).
- **hooks** (skill 2, retention): the opening frame is already the most attractive view: landmark in full light, light breaking through, nature in motion, tiny against huge, mirror reflection, colour contrast. Never an empty intro, a fade from black or a slow riser on nothing.
- **structures** A-F (skill 3): A Wonder and Discovery, B Peaceful Immersion, C Grand Scale, D Intimate Natural Detail, E Atmospheric Transformation, F Cinematic Multi-shot; each has a three-beat arc and the techniques that serve it.
- **water** + **timelapse** (skill 4): real-time motion lines per water type (falls, sea, lake, river, none); time-lapse only on the sky (clouds, mist, sunrise/sunset light, aurora, cloud shadows) and only in structure E; water, animals, people and boats are never accelerated.
- **lighting** (skill 5): golden sunrise, golden sunset, blue hour, misty morning, soft overcast, after-rain, storm light, clear day, aurora night (`--north`); with a photo the light is the photo's (`from-photo` + `--photo-light` in words). One light direction for the whole episode; no oversaturation, no HDR.
- **music** + **ambience** (skill 6): felt piano, epic orchestral, nordic folk, ethereal pads, warm acoustic, East Asian traditional, desert world, tropical calm, matched to setting and country; cued per segment (present from frame 1, swells on the open view, resolves to loop), with the place's real ambience underneath.
  - **Sung styles** (`"vocal": true`, ACE-Step with the style's `lyrics`, `{place}` filled in): dreamy vocal ballad (mountain, snow, lake, nature, coast), nordic folk song with kulning calls (Nordic countries), acoustic folk ballad (coast, island, lake, old town), East Asian vocal ballad (China, Japan, Vietnam, Korea, Taiwan). `--vocals auto` (default) picks among sung and instrumental styles that fit; `on` / `off` when the user asks for a singer or for none. The singer wording (one natural lead singer, no duets, no negated words) comes from `music.py`, the user's rule from scenic-drop-reel. `render` stops before any render when a sung style is planned and ACE-Step is not installed (MusicGen cannot sing): install it (scenic-drop-reel "Music engines") or re-plan with `--vocals off`. Listen to the cut: the voice must be in the 15 s slice.
- **avoid** (skill 7, photorealism): the list every prompt carries.
- **edits** (skill 8): A one shot 0-15, B two shots 0-7 / 7-15, C three shots 0-4 / 4-10 / 10-15.

## Steps
1. **Earlier shots + series history**: `python3 ../shot-history/scripts/shots.py check --place "<place>" --country <country>` (shared step 1) and `python3 scripts/plan.py --history`. plan.py already skips the last few values of every dimension (technique 4, structure 3, hook 3, light 2, music 2, shot count 1; skill 9); a repeated destination needs new views (shot-history).
2. **Direct** (writes `plan.json`, `episode.md`, `seg<N>.txt` into the work folder):
   ```bash
   python3 scripts/plan.py --place "Geirangerfjord" --country Norway --setting mountain --water falls \
     --view "deep narrow fjord between near-vertical rock walls, the Seven Sisters waterfalls on the right cliff, birch and pine on the lower ledges, snow on the peaks, a small white ferry" \
     --focus "the Seven Sisters waterfalls" --photo fjord.jpg \
     --photo-light "bright spring day, sun high from the left, blue sky with white cumulus" \
     --out ~/Movies/museai/scenic-geirangerfjord
   ```
   - `--view` = what is really there (real landmarks, terrain, water, vegetation); `--treeless` for Arctic, highlands, deserts (muse paints forests otherwise). `--focus` = the subject the camera serves. `--water` drives the motion lines and the ambience.
   - Moves that need them: `--foreground` (low-angle, parallax, crane), `--cover` (aerial reveal), `--over` (glide), `--side`, `--sun`. Without them plan.py uses generic rocks / ridge / valley: fill them in for a better shot.
   - Overrides only when the user names one: `--technique --structure --shots --hook --light --music`. `--list` shows the library.
   - **Read `episode.md`**, fix anything that does not fit the real place (a role that asks for flowers on a glacier, a hook the photo cannot show) by re-running with the right flags, not by hand-editing the prompts. Show the user the six-part brief (title, concept, reference image, plan, ready-to-paste prompt, tip) with the preview; when the user only asked for the prompt, stop here and give them `episode.md`.
3. **Render** (one background call; the segments one at a time through `render-queue`, the soundtrack last):
   ```bash
   scripts/render ~/Movies/museai/scenic-<slug>/plan.json        # or: plan.json 2   (only segment 2)
   ```
   Segment 1 starts from the photo; the others are text-to-video with the photo's light in words. Clips carry ambience only (the travel block's music line is dropped); `track.m4a` comes from `music.py` with the plan's instrumental style. Renders over 10 s may self-join (muse-video Travel lessons): a one-shot episode renders 15 s, check its sheet for a dissolve.
4. **Check each segment** (shared step 5): `python3 ../muse-video/scripts/qa.py segN.mp4 --travel 0 sheetN.jpg`; frame-grab 0/1/2 s and the last second for drift, a redrawn view or invented equipment. A waterfall's TIME-LAPSE flag on falling water is fine (muse-video "Waterfalls"); a sideways or sky band TIME-LAPSE is not, except the planned sky time-lapse of structure E. A late camera drift: `../muse-video/scripts/lock_camera.py` instead of a re-render.
5. **Compose**:
   ```bash
   python3 scripts/compose.py ~/Movies/museai/scenic-<slug>/plan.json [--at 2=1.0]
   ```
   Trims each segment to its planned length (photo segment from frame 0, the hook; others skip muse's 0.5 s settle-in), cuts snap to the nearest beat of `track.beats.json`, 0.5 s dissolves centred on the cuts, music over the clips' ambience (-14 dB), music fades out over the last 1.2 s for the loop, -14 LUFS. Then `qa.py <final> --travel 0` (dissolves are not hard cuts, so 0 planned cuts) and a contact sheet (shared step 6); the moving segment's planned glide trips `motion` TIME-LAPSE on the whole episode, so judge motion per segment (step 4).
6. **Quality control** (skill 10): answer every question before showing the user; any "no" → fix and re-render that segment.
   1. Is the first frame already beautiful and recognisable (no empty or dark opening)?
   2. Does the place look exactly like the real place (landmarks, terrain, vegetation, water colour)?
   3. Is there exactly one primary technique, executed slowly and level?
   4. Does the camera never drift, shake, warp or redraw the view?
   5. Does nature move at real-time speed (falling water falls, waves break, no sliding sheet, no frozen water)?
   6. Is any time-lapse limited to the sky, and only when planned?
   7. Is the light, sun direction and weather identical across every shot?
   8. Are colours natural (no oversaturation, no HDR halos, no flicker)?
   9. Are there no invented landmarks, duplicated mountains, warped buildings, equipment, people popping in or out?
   10. Is there no text, subtitle, logo or watermark?
   11. Does the music fit the place, start at frame 1 and change with the shots?
   12. Is the real ambience audible under the music, no narration; any singing only the planned song's one natural voice?
   13. Does the last frame flow back into the first for a replay loop?
   14. Does this episode differ from the last ones in the series (technique, structure, hook, light, music)?
7. **Deliver** (shared step 7): preview from the work folder with the six-part brief; after the user accepts, record the shots (`../shot-history/scripts/shots.py record --skill scenery-director --template <structure>`) and the episode (`python3 scripts/plan.py --record plan.json`) **before** `FINAL=1` (it trashes the work folder), then `FINAL=1 [UHD=1] ../muse-video/scripts/deliver.sh scenic-<slug>.mp4 <work>` with `THUMB_DIR=` and `CAPTIONS_FILE=` (no text in the video, so the caption carries the place name).

## Lessons
- Geirangerfjord, 2026-10-29 (photo, structure B, static → foreground parallax → long lens, ethereal pads): all three segments held the place, the light and the falling water at first render. The parallax glide reads clean but trips `motion` TIME-LAPSE at 5-7 % of width/s (planned); the locked photo segment still flags 3.2 %/s in the sky band and the fast ferry on the water band: check the sheet, accept when the cliffs hold. The clips' own ambience carried a -50 dB hiss floor that failed `noise`; compose.py now runs the stitch.sh denoise (`afftdn=nr=40:nf=-40:tn=0`) on ambience and music (-72 dB, ok).

## Maintaining this skill
Record lessons proven by a render here (wording that held a technique, moves muse cannot do from a photo, music styles that clashed); add or tune moves, structures, light and music in `library.json`, never in one episode's prompt. Same flow as `../muse-video/SKILL.md` "Maintaining this skill".
