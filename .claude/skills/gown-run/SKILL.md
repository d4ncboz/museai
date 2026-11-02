---
name: gown-run
description: Make a short vertical "gown run" fashion reel through museai - one gorgeous copper-haired woman, always seen from behind, in a dramatic flowing gown (crimson hooded cape, ivory chiffon train, emerald medieval velvet, gold goddess chiffon, ao dai, hanfu, lehenga, ...) running and wandering through a famous beautiful place (castle ruin, cliffs, dunes, lavender, Santorini, fjords, Ha Long Bay ...), fabric billowing in the wind, bright real phone-footage look, 7 hard cuts in 15 s on a catchy sung-hook track. Built from the user's reference reel (red cape at a Scottish castle ruin). Picks from a 100-idea bank (25 gowns x 50 places) and keeps a history so no video repeats a gown + place. Use for "gown run", "girl in a dress running to the scenery", "red cape video", "dress reel", "video like the red cape / castle one", "next gown video", or a dress + place video.
---

# gown-run

Paths are relative to this folder (`.claude/skills/gown-run/`); run `../muse-video` scripts (`music.py`, `qa.py`, `deliver.sh`) from the main checkout. Server, retries, QA and delivery come from `../muse-video/SKILL.md` (Server, "Format skills" shared steps 3-7). Name everything `gown-<slug>`; the work folder is `~/Movies/museai/gown-<slug>/`.

## The template (measured on the user's reference reel, 9:16, 15.0 s, 2026-10-31)
A red-haired woman in a crimson hooded velvet cape over a red chiffon gown at a roofless Scottish tower-house ruin on an overcast day. 7 hard cuts (4.2, 5.8, 7.1, 8.4, 10.0, 11.1 s), music only, no text.

| # | s | shot |
|---|---|---|
| 1 | 4.2 | **follow-run**: low tracking shot from behind, she runs across the meadow toward the castle, cape billowing back toward the lens |
| 2 | 1.6 | **reveal**: wide, the landmark towers over the frame, she is tiny at the bottom |
| 3 | 1.3 | **touch**: medium from behind/side, her hand rests on the old stone, she looks up |
| 4 | 1.3 | **hair**: medium from behind, she walks away, hair styling (half-up with a gold circlet) catches the light |
| 5 | 1.6 | **swirl**: she half-turns, a gust throws the cape into a red arc |
| 6 | 1.1 | **wide 2**: small figure among the ruin and grass |
| 7 | 3.9 | **hero frame**: static wide, she stands in a broken window gap of the ruin wall, wind in the cape |

Why it works: one saturated gown colour against the green of a bright day, real fabric physics (heavy, slow billowing), monumental place vs. small figure, and her face is NEVER shown (no face drift between shots, keeps the mystery). `prompt/gown.txt` (appended to every shot by `scripts/shot`) holds these rules; change them there, never in one video's prompt.

## Idea bank + history (no duplicates)
- `ideas.json` / `ideas.md`: 100 ideas built by `scripts/gen_ideas.py` from 25 gowns (colour, fabric, how it moves, hair styling) and 50 real places (ground, landmark, texture to touch, wide view, hero frame, light, colours that pop there). Each gown 4 times, each place twice, never the same pair, and the gown colour must pop against the place. gr-001 is the reference (crimson cape at Ardvreck Castle). Every idea carries the 7 shot briefs and the cut lengths. To widen: add gowns/places at the END of the lists in `gen_ideas.py`, raise `N`, rerun.
- History: `~/.config/museai/gown-run-history.json`, one entry per DELIVERED video (id, gown, colour, place, music style, briefs, video path, date).
```bash
python3 scripts/ideas.py next [--gown hanfu] [--colour red] [--place Iceland] [--n 3]   # fresh ideas
python3 scripts/ideas.py show gr-042
python3 scripts/ideas.py check --gown "..." --colour red --place "..."   # the user's own idea
python3 scripts/ideas.py list ; python3 scripts/ideas.py stats
```
`next` skips used ideas and anything with the same gown or place as the last 5 videos, the same colour as the last 2, or the same music style as the last 3. `check` exits 1 DUPLICATE (same gown + place) or 2 SIMILAR: tell the user what it matches and propose the `next` idea instead. A custom idea → write the 7 briefs in the same shape as a bank idea, render, then `record custom`.

## Steps
1. **Pick**: `python3 scripts/ideas.py next > idea.json` (or the user's filters / idea). Also run `../shot-history` for the place so the views differ from earlier reels there. Show the user title + 7 shots in one line each; render after a yes (renders cost muse time).
2. **Write the shots**: `shots[k]` is the brief of shot k. Every brief starts with a `Place:` line that names the real landmark's exact shape and count ("ONE small roofless tower house ... the only building: never several towers"); a vague "castle ruin" made muse draw a different castle in each shot. Bank ideas carry it from `DETAIL` in `gen_ideas.py`; for a place without an entry, look the landmark up, write it, and add it to `DETAIL`. Keep the light bright (sun through white clouds, blue sky patches); never overcast, misty, dusk or moody. Then the beat, concrete for the place (which side the light comes from, the exact spot of the hero frame). Keep the gown text word-for-word identical in all 7 briefs (same gown in every shot).
3. **Render** all 7 at once, each in its own background call:
   ```bash
   scripts/shot "<brief of shot 1>" ~/Movies/museai/gown-<slug>/s1.mp4
   ```
   6 s per shot, 9:16. For a stronger same-woman look, render shot 1 first and pass a frame of her as `IMAGE=` to the others (muse-video "Intro shot + cut" lesson).
4. **Music**: a new track for every video, never a track or chorus from an earlier one (user, 2026-11-02). The idea carries a style from the 10 in `MUSIC` (`gen_ideas.py`: celtic-pop, folk-stomp, dream-pop, tropical-house, ...), rotated over the bank, and `next` skips a style used in the last 3 videos, so posts in a row sound different. Every style is catchy with a sung hook from the first beat (a moody instrumental made gr-001 v1 forgettable). Swap the style's regional instruments for the place's own (tin whistle for Scotland, bouzouki for Greece, dan tranh for Vietnam). Write a new 4-line `[chorus]` about this place and this gown colour, and render two random seeds:
   ```bash
   L=$'[chorus]\nRun to the highlands, red in the wind\nOver the water where the stories begin\nOh-oh-oh, carry me home\nCastle of stone, I am never alone\n'   # gr-001's; write a new one
   STYLE=$(jq -r .music_style idea.json); BPM=$(jq -r .bpm idea.json)
   for s in $RANDOM $RANDOM; do uv run --no-project ../muse-video/scripts/music.py --style "$STYLE" --lyrics "$L" --bpm $BPM --body-beats 26 --seed $s --engine ace --out ~/Movies/museai/gown-<slug>/track$s.m4a & done; wait
   ```
   Compose one video per track (`-m<seed>`) and let the user pick. Another style on request: `next --music disco`, or pass any `--style`; record what was used with `record ... --music <name>`. Never take the music from the reference reel (someone else's track); to use it, post with the platform's "use audio".
5. **Check each clip**: contact sheet (`ffmpeg -i s1.mp4 -vf "fps=2,scale=180:-1,tile=6x2" -frames:v 1 s1.jpg`) and `python3 ../muse-video/scripts/qa.py s1.mp4 --travel 0 s1sheet.jpg`. Reject: her face toward the lens, a second person, gown colour/cut changing, fabric melting or passing through her body, warped landmark, text. Pick the best window of each clip (`clip@start`, length = the cut).
6. **Compose**:
   ```bash
   python3 scripts/compose.py --idea idea.json --music track.m4a --out gown-<slug>.mp4 s1.mp4@0.8 s2.mp4 ... s7.mp4
   ```
   Cuts from the idea (`--cuts` overrides), bright grade (a shot under mean luma 115 gets a gamma lift, light saturation, no vignette), clips' wind under the music, 0.6 s fade out on the hero frame, -14 LUFS. Then qa + sheet on the result (shared step 6). Mean luma of the result must be ≥ 110 (`ffmpeg -i out.mp4 -vf fps=2,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=- -an -f null - 2>/dev/null | awk -F= '/YAVG/{s+=$2;n++}END{print s/n}'`); `smooth` FAIL on the planned cuts and `noise` FAIL on the music's highs are expected.
7. **Deliver**: cover from shot 7 or the swirl (`../travel-thumbnail`, hook like "she ran to <place>"), captions via `../social-captions`, then shared step 7 (`deliver.sh`). **Record before `FINAL=1`** (it trashes the work folder):
   ```bash
   python3 scripts/ideas.py record gr-042 --video ~/Desktop/gown-<slug>.mp4 [--shots shots.json]
   ```
   `--shots` = the briefs actually rendered (JSON list) when they differ from the bank's. Also record the place's shots in `../shot-history`. Record only delivered videos.

## Lessons
- **gr-001 v1 → v2 (2026-11, accepted v2-m7)**: v1 read dark and fake (final luma 63: "overcast moody" light in the brief + a cinematic grade with vignette) and muse drew a different multi-tower castle in each shot. v2: `prompt/gown.txt` asks for an unedited phone clip on a bright day (main #165/#171), briefs open with the landmark's exact shape, compose lifts dim shots and grades bright (luma 112), and the music became a sung celtic-pop hook at 100 bpm. Left: in one shot the hood went up while the others had it down; say "hood down" in the gown text when the gown has a hood.
- **gr-002 (2026-11, accepted m4182)**: lavender fairy dress at the Cliffs of Moher, folk-stomp music, luma 118 (only the swirl shot needed a lift). Muse put a conical roof on O'Brien's Tower in one shot: when a tower's top matters, name it ("flat battlemented top, no roof, no cone, no spire"). The cover tool puts its text in the middle third, so pick a frame where she is in the lower third and the landmark sits clear of the text.
