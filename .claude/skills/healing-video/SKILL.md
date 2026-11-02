---
name: healing-video
description: Make a short vertical "healing" slow-living video through museai - calm 1-2 s shots of a cosy country home (a girl baking or making tea in the kitchen, seen from behind or as hands, beautiful corners of the house, a garden of flowers, a cat, dog or bird resting, rain on the window, a river, birdsong, the view from an open window), soft muted grade, a small serif text line, gentle instrumental music over the real ambience. Two concepts from the user's reference reels - "postcard" (8 shots under one line like "the way I want to live:") and "ode" (one sentence split over 6 shots, each shot showing the subject act: "a love letter to the wind that / lifts the curtains / ..."). Picks from a 1000-idea bank and keeps a history so no video repeats an earlier one. Use for "healing video", "slow living video", "cottagecore", "cosy home video", "the way I want to live", "love letter to the rain/wind", "video like the cottage one", or "next healing video".
---

# healing-video

Paths are relative to this folder (`.claude/skills/healing-video/`). Server, retries, QA and delivery come from `../muse-video/SKILL.md` (Server, "Format skills" shared steps 3-7). Name everything `healing-<slug>`; the work folder is `~/Movies/museai/healing-<slug>/`.

## The two concepts (measured on the user's reference reels, both 9:16, ~9.8 s)
| | postcard (reference 1) | ode (reference 2) |
|---|---|---|
| shots | 8 hard cuts, ~1.2 s each (cuts 1.5, 2.8, 3.9, 5.1, 6.3, 7.5, 8.7 s) | 6 hard cuts, ~1.6 s each (2.1, 3.7, 5.3, 6.6, 8.3 s) |
| subject | a Welsh hill farmhouse on an overcast day: garden table with teapot and flowers, open casement windows onto green hills, copper pans and a kettle in the kitchen, potted petunias by the stone door, candles on the sill | sunny Edwardian rooms: a sheer curtain billowing over a bed, dappled light on a sofa, a lampshade fringe swaying, leaves outside a bay window, a book's pages turning |
| text | ONE small white serif line, centred, the same on every shot ("the way I want to live:") | one phrase per shot, the sentence runs on ("a love letter to the wind that / ... / and turns the pages"), each phrase is what that shot shows |
| camera | handheld, almost still, tiny drift | handheld, almost still; the subject (wind) does the moving |
| sound | soft music over the place's ambience, -18 LUFS | the same, -14 LUFS |

What makes both "healing": nothing hurries, every shot has ONE gentle living motion (steam, breeze, rain, flame, petals, pages), muted warm colours, lived-in real homes, no faces to the camera, no talking. `prompt/healing.txt` (appended to every shot by `scripts/shot`) holds these rules; change them there, never in one video's prompt.

## Idea bank + history (no duplicates)
- `ideas.json` / `ideas.md`: 1000 ideas (667 postcards, 333 odes) built by `scripts/gen_ideas.py` from 51 real homes (Welsh farmhouse, Cotswolds, Kyoto machiya, Sa Pa stilt house, Norwegian fjord cabin, Moroccan riad, ...), seasons (rainy/dry season for tropical homes, no snow where it never snows, treeless homes get "NO trees"), local kitchen tasks, animals, sounds, flowers and 40 caption lines. No two ideas share home + season + task. To widen the bank, add homes, tasks, ode subjects or captions at the END of the lists in `gen_ideas.py` and rerun it.
- History: `~/.config/museai/healing-history.json`, one entry per DELIVERED video.
```bash
python3 scripts/ideas.py next [--season now] [--home Kyoto] [--animal cat] [--no-animal] [--n 3]   # fresh ideas
python3 scripts/ideas.py show hv-0042
python3 scripts/ideas.py check --home "..." --season autumn --task "..."   # a custom idea from the user
python3 scripts/ideas.py list ; python3 scripts/ideas.py stats
```
`next` skips used ideas and anything with the same home or task as the last 10 videos, or the same animal or caption as the last 3. `check` exits 1 DUPLICATE (same home + season + task, or same home + task + animal) or 2 SIMILAR (home or task in the last 10): tell the user what it matches and propose the `next` idea instead before rendering.
- The user's own idea ("a girl making kimchi in the rain") → `check` it, then write the shot list in the same shape as a bank idea and record it with `record custom`.

## Steps
1. **Pick**: `python3 scripts/ideas.py next --season now > idea.json` (or the user's idea / filters). Show the user the title, the shot list in one line each and the caption/lines; render after a yes (renders cost muse time). Human away → `webex ask`.
2. **Write the shots**: each `shots[k]` of the idea is the brief of one shot. Make it concrete for that home and moment (real objects, which way the light falls, the one thing that moves) but keep the subject. Every postcard idea in the bank opens "Through an open old window ...": replace that first shot with an opener from the rotation (see Looks). Ode: shot k must SHOW phrase k (the curtain lifts on "lifts the curtains"). Rewrite ode phrases in fresh words when the same subject was used before (`ideas.py list`), keeping one sentence that runs over the shots.
3. **Render** every shot at once, each in its own background call (independent shots render in parallel on all free accounts):
   ```bash
   scripts/shot "<brief of shot 1>" ~/Movies/museai/healing-<slug>/s1.mp4
   ```
   6 s per shot (`DURATION=`), 9:16. `prompt/healing.txt` asks for ambience only (no music), the girl's fixed look (long chestnut hair, cream knit cardigan, linen apron, never facing the camera) and real gentle motion.
4. **Music**: soft solo piano from ACE-Step, like reference 3 (broken-chord arpeggios with a simple melody on top, notes moving every 0.3-0.8 s, nothing above ~4 kHz): render 2-3 seeds and keep the one whose spectrogram shows separate note onsets, not a smear.
   ```bash
   n=<idea number>; for k in 1 2 3; do scripts/music "<season> piano lullaby, tender" ~/Movies/museai/healing-<slug>/p$k.m4a 24 $((n * 10 + k)); done   # ~5 min each, one at a time
   ffmpeg -i p37.m4a -lavfi "showspectrumpic=s=600x150:legend=0:fscale=log:stop=8000" p37.png
   ```
   `scripts/music` names the moving line in its tags ("solo piano" alone gave a melody-less drone) and asks for felt piano, low and middle register, sparse, pianissimo, no high notes. It starts at the body, then softens: pitch down 16 % (`asetrate=44100*0.84`), two 2.2 kHz low-passes, -20 LUFS. That brings ACE's spectral centroid from ~870 Hz to ~560 Hz (reference 3: 530 Hz). Check a take with `ffmpeg -i p.m4a -af aspectralstats=measure=centroid,ametadata=print:key=lavfi.aspectralstats.1.centroid -f null -` (median 500-600 Hz). Seeds come from the idea number: the same tags and seed give the SAME track (hv-0005's seed 37 was hv-0001's music again), so never reuse a seed list. Reject seeds that smear into a drone (hv-0001: seed 23) or go silent before the end. `REF=ref.wav REF_STRENGTH=0.3` (audio2audio guided by a reference) is there but gave a smeared wash with no notes at 0.3; don't use it for delivery. `loops.py make` (Apple Loops) is the fallback; the user found those loops not soft enough. Never take the music from a reference reel: it is someone else's track (a claim or mute on upload); to use it, post with the platform's "use audio" instead.
5. **Check each clip**: contact sheet (`ffmpeg -i s1.mp4 -vf "fps=2,scale=180:-1,tile=6x2" -frames:v 1 s1.jpg`) and `python3 ../muse-video/scripts/qa.py s1.mp4 --travel 0 s1sheet.jpg`. Reject: text in frame, a face looking into the lens, warped hands or tableware, doubled or deformed animals, time-lapse sky, frozen-photo look. Pick the calmest 1.2-1.6 s of each clip (`clip@start`).
6. **Compose**:
   ```bash
   python3 scripts/compose.py --idea idea.json --music track.m4a --out healing-<slug>.mp4 s1.mp4 s2.mp4@2.0 ... [--shot 3]
   ```
   Hard cuts like the references, soft grade, Georgia text slightly below centre with a soft shadow (postcard: one caption; ode: one phrase per shot), a REAL recorded ambience bed under the music, chosen from the idea's sound (`--bed rain|water|crickets|clips|<file>`, `--ambience 0.45`: under the music, like the references; muse's own rain is flat hiss, so it is only the fallback; drop better recordings in `~/.config/museai/ambience/<name>.wav`), fade in 0.3 s / out 0.5 s, -16 LUFS. `--shot 3` (or 4) makes a slower 20-30 s version: same shots, longer windows. `--dissolve 0.5` joins the shots with soft cross-dissolves instead of hard cuts (reference 4). Then qa + sheet on the result (shared step 6).
7. **Deliver**: cover with `python3 scripts/cover.py --at s7.mp4@2.0 --title "<caption>" --sub "<season day in place>" --out thumbs/healing-<slug>_9x16.jpg` (soft italic serif on the calmest, brightest frame; NOT the travel-thumbnail shock style). Captions: `../social-captions` (`captions.py check` must PASS; YouTube description ends with `#Shorts`), opening with the video's line and naming the idea's real animal. Then shared step 7 (`FINAL=1 THUMB_DIR=thumbs CAPTIONS_FILE=captions.json ../muse-video/scripts/deliver.sh healing-<slug>.mp4 <work dir> healing-<slug>`, preview first). **Record before `FINAL=1`** (it trashes the work folder):
   ```bash
   python3 scripts/ideas.py record hv-0042 --video ~/Desktop/healing-<slug>.mp4 [--shots shots.json]
   ```
   `--shots` = the briefs actually rendered (JSON list) when they differ from the bank's. Record only delivered videos.

## Looks (reference 3, 2026-10-31)
The user wants views "more beautiful and healing". Reference 3 is one handheld phone shot: a hand in a knit sleeve opens a white casement window onto a golden-hour garden, then wide sunlit hills with grazing animals. `prompt/healing.txt` asks for real phone footage in the true light of the hour (see Real look below). In briefs:
- **Vary the opener and the style.** The window reveal ("her hand in a cream knit sleeve slowly pushes open the casement window, and the view opens onto ...") opened hv-0001, hv-0005 and the first cut of hv-0014, and the user asked for different styles, "not this open window anymore". Pick an opener that none of the last 3 videos used (look at the first brief of each in `~/.config/museai/healing-history.json`):
  - a still room in sunlight (reference 4: the kitchen, then her at the sink);
  - hands at work in close-up (pouring, kneading, picking);
  - the animal asleep in a patch of sun;
  - an outdoor wide view with a living motion (sea, terraces, laundry on a line, a path through the garden);
  - a top-down table (ingredients, a basket of eggs, tea being poured).
  Also rotate the look between golden hour (reference 3) and bright midday sun (reference 4), and between hard cuts and `--dissolve 0.5`.
- Name the light in every brief ("late summer evening, golden hour", "warm beam of low sunlight across the worktop, dust motes").
- Never write a camera move into a landscape or animal brief ("slow drift", "push forward"): muse overdoes it (20-30 % of the frame width per second). Write "The camera is held perfectly still, only the X moves." muse still drifts 5-10 %/s, which matches reference 3 (up to 12 %/s), so qa `motion` FAIL at that level is fine here.
- 2 s per shot (`--shot 2.0`) for this calmer look.
- Name only things that really move by themselves as the motion: steam, a flame, dust in a sunbeam, a curtain, leaves outside, water, an animal. Never ask flowers in a vase, tableware or furniture to move: muse animates them anyway (hv-0005: the bouquet flew into the vase). Write "the flowers and the furniture stay exactly where they are; only the dust motes and the curtain move" (never "tripod" or "phone on": muse draws the tripod and phone into the shot, hv-0017).

## Real look (hv-0017, 2026-11-02)
The user: "the video look AI". hv-0017 (Tyrol dumplings, rainy afternoon) had every AI tell: saturated orange HDR glow, a candle, a lamp and dahlias in every frame, a wall of flowers outside each window, five identical dumplings in a row, the dog's fur a waxy blob in the dim light, and a slow push-in on 2 shots that were meant to hold still. Real footage is plainer than muse's idea of "cosy". Rules:
- `scripts/shot` refuses a brief with bait words (cosy, magical, dreamy, cinematic, glow, candle, lamp light, fairy lights ...): they make muse stack props and orange light. Name the plain light instead ("grey daylight from the window", "midday sun on the worktop"). `BRIEF_OK=1` only when the user asks for a candle.
- Few things per frame: the hands, the work, two or three objects. No vase, candle and lamp together; no flowers unless the shot is about them.
- Handmade food is uneven ("lumpy, slightly different sizes"); never "a row of" anything.
- Animals in bright daylight only (sun patch, garden): in dim light muse melts the fur.
- **Bright and lively, not dim.** The muted grey-rain redo of hv-0017 was "too dark, too tired and boring". Every video is a sunny day: sun streaming into a white, airy room, blue sky outside (reference 4). A rainy or winter idea becomes "sun breaking through after the rain" or "bright snowy morning", never a dim interior. `compose.py` lifts any clip darker than mean luma 135 (gamma up to 1.6), but render bright; a lift can't fix a murky shot.
- **Something is happening in every shot**: her hands work (kneading, pouring, picking, wiping), she walks through the sun, an animal plays or eats, laundry flaps, water splashes. A static plate or empty window is at most one shot per video. Music for sunny videos: `MOOD=sunny`; cuts `--shot 2.0`.
- `compose.py` grade: natural saturation, a touch warm, fine moving grain (hides muse's plastic smoothness), auto exposure lift.
- Write "Static locked-off shot" for a still camera. "Phone on a tripod" put a phone on a tripod into 2 of 6 hv-0017 shots; `shot` refuses it.
- Judge the contact sheet before compose: any shot that looks like a render (glow, halos, clutter, clones, warped hands) is re-rendered, not kept.

## Sunny kitchen (reference 4, 2026-11-01)
The user's fourth reference (21.6 s, 9:16) is a bright modern home on a sunny midday: a white kitchen with an arched window onto a garden, a young woman in pink washing vegetables at a sink under the window, water running over fruit, an overhead view of her sorting fruit next to baskets of eggs, then the dining room under amber pendant lamps. Measured:
- 5 shots of 3.5-6 s, joined by ~0.5 s cross-dissolves, not hard cuts → `compose.py --shot 4 --dissolve 0.5`.
- Real phone footage of an ordinary task, done all the way through (open the window, wash, sort). The camera is steady; she is seen from the side or above, never facing the lens. No text on the video.
- Light: clear midday sun, white and pale-wood surfaces, green plants on every sill. Bright, not golden.
- Music: one clear piano melody in the middle register (melody notes ~600-750 Hz, chords 150-500 Hz), a note every 0.35-0.5 s, F/C major, ~72 bpm, birdsong under it, -16 LUFS overall. Spectral centroid ~1100 Hz: brighter than the hv-0005 soft chain (560 Hz). Render it with `MOOD=sunny scripts/music ...` (no pitch drop, 4.5 kHz cut, -16 LUFS). Take 3 seeds and keep the calmest: the reference holds each note (1.9 onsets/s). Of the first three takes (seeds 401-403), 402 came closest (2.4/s, held notes); 401 (3.4/s) and 403 (4.9/s, centroid 1640 Hz) were too busy. Reject anything above ~3 onsets/s (`librosa.onset.onset_detect` in the ACE venv).
- Its own track is saved at `~/.config/museai/music/ref4-sunny-kitchen-piano.m4a` (`compose.py --music` takes it as is). It is someone else's recording: a video posted with it can be muted or claimed. For a post, prefer an ACE `MOOD=sunny` take, or post without music and add this track in the app with "use audio".

## Lessons
- hv-0001 (2026-10-31): the user heard the sound as "laggy". There were three causes. First, the music opened on ACE's quiet intro, so it got 11 dB louder 0.9 s into the video. Second, each shot's ambience was hard-cut, so the rain level jumped up to 10 dB every 1.2 s. Third, single-pass loudnorm pumped the level. The fixes:
  - `scripts/music` starts the track where its main section begins (`lnorm.py --body-start`).
  - `compose.py` brings each clip's ambience to -30 LUFS and cross-fades it into one continuous bed.
  - Both scripts set the level with two-pass linear `lnorm.py`.
  - Check by printing the loudness every 0.1 s (`astats` RMS): no gap at the start, no jump at any cut.
- hv-0001 (2026-10-31): the user said the rain did not sound natural. muse's clip rain is close to white noise (spectral flatness 0.6-0.67, no droplets), and denoising it made it worse. `compose.py` now lays a real recording under the music instead: iMovie's royalty-free "Hard Rain", low-passed so it sounds like rain heard through an open window, looped with 1 s cross-fades, at -30 LUFS. qa `noise` then reads about -60 dB above 7 kHz. That energy is the rain droplets, not hiss, so accept it for a rain bed.
- hv-0001 (2026-10-31), second round: the user said the rain still did not sound like a person filmed it, and the music was "not healing". Spectrograms explained both. The references are led by a melody (notes moving every 0.3-0.8 s) and have almost nothing above 2.5 kHz. Ours was a static drone, and rain hiss filled 1-8 kHz. The fixes:
  - Music comes from `loops.py`.
  - The rain bed is band-limited to 200-3200 Hz, narrowed to almost mono, given short room reflections, and mixed lower at `--ambience 0.45`.
  - Before showing a mix, compare its spectrogram with a reference's (`showspectrumpic`).
- hv-0001 (2026-10-31), third round: the user said the Apple Loops music was "not healing", asked for soft, gentle piano, and asked for more beautiful views (reference 3). The fixes:
  - ACE got tags that name the moving line; take the best of several seeds by spectrogram (see step 4).
  - audio2audio from the reference was tried and rejected.
  - Briefs moved to golden hour, with the window-reveal opener (see Looks).
- hv-0005 (2026-11-01): the user said the piano was "too high, too strong, not healing" and the flower shot "not natural, the video should be real". The raw ACE piano measured ~870 Hz spectral centroid against reference 3's 530 Hz. The fixes:
  - Softer tags plus the pitch-down and low-pass chain at -20 LUFS (step 4); measure the centroid before showing a mix.
  - The flower brief had asked the bouquet to stir; the re-render named only dust motes and the curtain as motion (see Looks).
- hv-0014 (2026-11-01): the user asked for different healing styles and "not this open window anymore". The window-reveal shot was dropped from the cut, which now opens on the sunlit kitchen. Openers now rotate (see Looks).
