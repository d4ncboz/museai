---
name: scenic-drop-reel
description: Make a short vertical travel reel of any country, region, city or single place from one of 20 templates picked at random - countdown drops, pin-and-flow, numbered top lists, coordinates intros, POV arrivals, golden-hour dissolves, FPV ramps, day-in-a-place and more - with aerial shots rendered through muse (muse-video), cut on the beat of an AI track generated for that template (catchy, with sung lyrics when ACE-Step is installed), and assembled with ffmpeg. Use when the user asks for a "travel reel", "drop reel", "countdown reel", "scenic reel", "beat-cut travel video", "video like the Switzerland/Italy one", or a destination montage of a place. Default for every travel or place video request (e.g. "generate for <place>", a place photo), except places in China (chinese-scenery-style), unless the user asks for one continuous documentary shot or a calm cinematic scenery episode (scenery-director). Use zoominview instead when the user wants a person reacting before the view, muse-video travel mode for one continuous documentary shot. Takes the shared brief (muse-video "Format skills"); files are named reel-<slug>.
---

# scenic-drop-reel

Paths are relative to this folder (`.claude/skills/scenic-drop-reel/`). Rendering rules, server, retries, the brief, music engine, shot history and delivery come from `../muse-video/SKILL.md` ("Format skills" shared steps, "Music", travel mode); this skill adds the reel templates. Name everything `reel-<slug>`.

## Templates (`templates.json`)
20 templates; each fixes intro (countdown, pin pill 📍, big word, POV line, black title card, coordinates typewriter, plain title, none), beat pattern per shot, transitions, camera moves, light, grade, on-screen text and music (BPM, tags, lyrics with `{place}`). `python3 scripts/pick.py --list` shows them with the scopes/settings they fit. Country-only templates (`countdown-drop`, `top-numbered`, …) are skipped for a single place.

**Scenery styles** (`templates.json` `sceneries`, user rule 2026-10-28: same music and moves on every reel got boring): `--setting` picks one of that landscape's music styles (snow → icy nordic folk, coast → ukulele pop, city → city pop, …; the template keeps its lyrics, FPV and `local-flavour` keep their own music) and alternates the template's signature move/transition with the setting's own (snow: glides, rises, orbits with dissolves and dips; city: whips and flashes). **Country sound** (user rule 2026-11-02, Fuji reel: generic dreamy pop sounded like nowhere): with `--country` in `local_sounds`, every template's music opens with that country's instruments (Japan: koto, shamisen, soft taiko). Always pass `--country` for a place abroad. Always pass the right `--setting`; add a style there, not in one reel, when a place needs a new sound.

**Use a random one for every new request** unless the user names a template or style. `pick.py` chooses among those that fit and skips the last 5 used (`~/.config/scenic-drop-reel/history.json`).

### Hook + calm pace (user rules, 2026-10-28)
- **The first 2 s decide whether viewers stay** (user rule 2026-10-29): shot 1 is the wow view (the iconic landmark, wildlife, the most dramatic light) from frame 0. Card intros (countdown, black-title, coords) no longer open on black: `compose.py` lays them over shot 1 on a dark scrim, for at most 4 beats (`pick.py` `HOOK_BEATS`). The music slice starts on the sung hook with the beat already going (`music.py` scores the first 3 s for voice + punch). Never open on a quiet establishing shot or a slow riser with nothing to look at.
- **Bold hook text gives the view context**: pass `--title` with a curiosity line (≤ ~40 characters) instead of the bare place name on `title`, `bigword`, `pov` and `black-title` templates: "The most surreal beach on Earth", "Wait until you see this water…", "Is this the bluest ice on Earth?". It must be true of the place. Never a format label ("Golden Hour reel", "Top 5 in X" alone, "15 seconds in …").
- **10-18 s and a seamless loop**: short reels get watched to the end and replayed. `pick.py` keeps every plan at 10-18 s (`MAX_REEL_S`, holds ≤ 4 s) and ends it with a reprise shot (`"reprise": 1`, nothing to render): `compose.py` replays clip 1's frames just before the hook's window, so the last frame flows straight into the first and the music ends on a beat with only a declick. Render shot 1 at its planned `duration` (it holds the reprise too); `warning: … too short for a seamless loop` → render shot 1 longer.
- **Never dizzy**: slow, level drone moves (`prompt/drone.txt`), no shot held under 1.6 s (2.4 s when the music is under 100 BPM; `pick.py` doubles the beat pattern), whips/zooms 0.4-0.5 s (`compose.py` `XF`). Svalbard Zoom Tunnel at 0.97 s per shot with 0.3 s zooms felt too fast to the user.
- **Bright, real colour** (user rule 2026-10-31): the Zhangjiajie reel came back at mean luma 65-78 / 255 (golden hour + "high contrast, postcard look" + vignette) and was rejected as too dark and fake. `prompt/drone.txt` now asks for bright, well-exposed real DJI footage with open shadows and natural colours; `golden` / `sunrise` keep the sun well above the horizon; `compose.py` lifts any shot under mean luma `BRIGHT` (110) with a gamma curve and prints a `note:` (night and blue hour excepted). Many `note:` lines → re-render in brighter light rather than lifting further.
- **Green, fantastic nature** (user rule 2026-10-31): the Zhangjiajie reel in `warm-film` turned the forests olive. For mountain, nature, island and lake settings `pick.py` swaps warm-film, teal-orange and moody for `vivid`. `prompt/drone.txt` asks for lush emerald vegetation glowing in the sun. Put the green in every brief ("pillar tops covered in dense vivid emerald-green pines") and use sunny light, not golden hour.
- **Every signature landmark the place is known for** (user rule 2026-10-31: "where's the view with the elevator?"): list the 3-5 must-sees a traveller expects (Zhangjiajie: Avatar Hallelujah pillar, Bailong glass elevator, Tianmen arch, Golden Whip Stream) and give each one a shot before adding generic views.
- **Pace follows view and music**: wide panoramas and detailed scenes hold longer than a simple subject; calm songs hold longer than dance tracks. Use `@start` / `--length` to give a big view more time when the plan is too even.

### Why the cuts feel smooth (measured on the Switzerland reference, keep for every template)
1. *Slow, even motion*: picture change per frame (ffmpeg `signalstats` YDIF) stays 3-9 and flat inside a shot. No speed-up, output at muse's native 24 fps (every frame once, no 24→30 judder); `compose.py` picks each shot's steadiest window near the template's `target` (`@auto`).
2. *Same composition*: subject centred, horizon in the upper third in every shot → the eye does not jump at the cut.
3. *Same light and grade* across shots (template `light` / `grade`; `day-in` changes light on purpose, morning → night).
4. Transitions follow the camera: a `whip` slides the way the outgoing shot moves, `rise` follows an upward move, `zoom` follows a push-in. Every cut or transition is centred on a beat.

## Steps
0. **Earlier shots**: shared step 1 (`../shot-history/scripts/shots.py check`).
1. **Pick**: `python3 scripts/pick.py --place "Positano" --scope place --setting coast --country italy > plan.json`
   - `--scope` = what the user named (country | region | city | place); `--setting` coast island mountain lake city oldtown nature desert snow; `--country` picks the local instruments for `local-flavour`; `--id` forces a template.
   - The plan lists per shot: beats, render `duration`, camera `move`, `light`, transition; plus `seconds`, `intro`, `text`, `music`, `fast`.
   - **Length is random** within 10-18 s: slow holds 12-18 s, mid and one-beat bursts 10-16/18 s; the shot count follows (at least 3 rendered shots + the reprise). A template's `"length": [min, max]` overrides the range; `--length 20` or `--n 6` forces it only when the user asks.
2. **Plan the shots** (`len(plan.shots)`): real, recognisable subjects of the place, each a different subject type, alternating wide/close, the most striking, instantly recognisable view FIRST (the hook), the second-best before the reprise. Write the hook text now (`--title`, see above). For a single place, shoot it from different angles/details (`one-place-angles`). For `number`/`label`/`time` text templates also write the per-shot labels.
3. **Render all shots at once**, each in its own background call:
   ```bash
   DURATION=<shot.duration> LIGHT="<shot.light>" scripts/shot "PLACE: Positano, Amalfi Coast, Italy: pastel houses stacked down the cliff to the beach. DRONE: <shot.move>, village centred." ~/Movies/museai/reel-<slug>/s1.mp4
   ```
   Add `FAST=1` when `plan.fast` is true (FPV templates). 9:16, `shot.duration` s (6-10, long enough for a held window), `prompt/drone.txt` with `{LIGHT}`/`{PACE}` filled in. Wait with `pgrep -f "bash scripts/shot"`. Upstream 502/503 → retry later.
4. **Music** (in parallel with the renders):
   ```bash
   uv run --no-project ../muse-video/scripts/music.py --plan plan.json --out ~/Movies/museai/reel-<slug>/track.m4a
   ```
   Writes `track.m4a` exactly as long as the reel and `track.beats.json` (beat grid, drop). Card intros (countdown, black-title, coords) get a short filtered riser under the card on shot 1 that drops as the card clears.
5. **Check each shot**: shared step 5 (`qa.py sN.mp4 --travel 0 sheetN.jpg`, judge `smooth` + sheet). Re-render only a shot with no clean window, a fake landmark or wrong weather; treeless places need the NO-trees line of shared step 2 in every brief.
6. **Compose**:
   ```bash
   uv run --no-project --python 3.12 --with pillow --with fonttools python scripts/compose.py \
     --plan plan.json --place "Positano" [--title "Is this the prettiest cliff town?"] [--flag 🇮🇹] \
     [--labels "A|B|…"] [--coords "40.63° N  14.48° E"] --music track.m4a --out reel-<slug>.mp4 s1.mp4 s2.mp4@2.0 s3.mp4 …
   ```
   One clip per rendered shot; the reprise needs none. `--plan` cuts each shot on its planned beats (the template's pattern only when no plan is passed). `clip@2.0` forces a window start; default `@auto` (for shot 1 it picks a window long enough for the reprise in front of it). Warning `moves fast even at its calmest` → re-render slower. Prints cut times, transitions and the windows used. Without a beat file pass `--bpm` (and `--drop`).
7. **Verify**: contact sheet (`ffmpeg -i reel-<slug>.mp4 -vf "fps=2,scale=180:-1,tile=8x4" -frames:v 1 sheet.png`): frame 0 already shows the view with readable hook text, every shot sunny/sharp/no muse text, transitions on beats, reel length ≈ music length (10-18 s), last frame continues into the first (`ffmpeg -sseof -0.05 -i reel.mp4 -frames:v 1 last.png` vs the first frame).
8. **Deliver**: shared step 7 (thumbnails: `thumbnail` style `travel` on the raw shots in plan order, `--title "<PLACE>" --hook "<shock fact> 😱" --sub "<Country> <flag>"`, `--at` the stakes/scale frame and `--circle` on its person or boat, per its "Travel: make it a shock", `CAPTIONS_FILE=captions.json`, shot-history record before `FINAL=1`). The YouTube title is a scannable curiosity question or claim under 50 characters ("Is this the bluest ice on Earth? 🧊"), then a line naming the place and the places shown. Without captions the reel lands on the dashboard's "Ready to post" queue empty (reel-it and reel-switzerland, 2026-10-28). Compose to `reel-<slug>.mp4`, not `reel.mp4`: Ilulissat landed on the Desktop as a bare `reel.mp4` (2026-10-29).

## Music
Engine, ACE install, tempo and singer rules: `../muse-video/SKILL.md` "Music". Here: `music.py --plan plan.json` takes the template's BPM, tags and lyrics (`{place}`); card intros get a filtered riser that drops as the card clears.
- **Catchy but low** (user rule 2026-10-31): about 100 BPM and a low, warm voice. Leave flutes, whistles, falsetto and bright synth leads out of the tags (write what you want, never "no X": `music.py` drops negated phrases).
- `assets/music-default.m4a` (+ `.beats.json`, 100 BPM, drop 3.233 s) is the Italy track, for quick tests. The reference reel's own audio stays out of the repo; a user-supplied track goes in with `--music file --bpm N --drop T`.

## Maintaining this skill
Same rules as `../muse-video/SKILL.md` "Maintaining this skill": record lessons proven by a render (prompt wording that held a camera move, transitions that looked wrong, shots muse cannot do); add or tune templates in `templates.json`, not in single reels.
