---
name: healing-video
description: Make a short vertical "healing" slow-living video through museai - calm 1-2 s shots of a cosy country home (a girl baking or making tea in the kitchen, seen from behind or as hands, beautiful corners of the house, a garden of flowers, a cat, dog or bird resting, rain on the window, a river, birdsong, the view from an open window), soft muted grade, a small serif text line, gentle instrumental music over the real ambience. Two concepts from the user's reference reels - "postcard" (8 shots under one line like "the way I want to live:") and "ode" (one sentence split over 6 shots, each shot showing the subject act: "a love letter to the wind that / lifts the curtains / ..."). Picks from a 1000-idea bank and keeps a history so no video repeats an earlier one. Has rotating styles (classic kitchen/home, garden montage "if a boring life looks like this", pov-ritual "POV : All you need is flowers and a cup of tea"): run `scripts/ideas.py style` to pick the one not used lately. Use for "healing video", "slow living video", "cottagecore", "cosy home video", "the way I want to live", "love letter to the rain/wind", "video like the cottage one", or "next healing video".
---

# healing-video

Paths are relative to this folder (`.claude/skills/healing-video/`). Server, retries, QA and delivery come from `../muse-video/SKILL.md` (Server, "Format skills" shared steps 3-7). Name everything `healing-<slug>`; the work folder is `~/Movies/museai/healing-<slug>/`.

## Styles: rotate so content never repeats (user 2026-11-12)
Every healing video belongs to a style; mix them. `python3 scripts/ideas.py style` prints the style used longest ago (history `style` field or `style:<name>` caption; videos without one count as `classic`). Pick that style unless the user names one; never the same style twice in a row.
| style | concepts | bank | look |
|---|---|---|---|
| classic | postcard, ode, story | `ideas.json` (hv-*) | indoor kitchen/home, muted, serif caption, `prompt/healing.txt` |
| harvest-asmr | hands-only montage | `scripts/harvest_ideas.py`, `styles/harvest-asmr.md` | hands picking crops, ~1 s, no text |
| garden | montage | `ideas-garden.json` (gm-*, `scripts/gen_garden.py`) | outdoor harvest garden, vivid sun, thin sans caption, `prompt/garden.txt` |
| pov-ritual | ritual | `ideas-ritual.json` (pr-*, `scripts/gen_ritual.py`) | one ritual told in 12 quick shots, garden → village → home → animal visitor, bold "POV :" caption, `prompt/ritual.txt` |
Next idea of a style: `python3 scripts/ideas.py next --style garden --season now`. Record with `--style` implied by the bank idea.

### garden montage (reference 5, "If a boring life looks like this", 9:16, 10.0 s, measured 2026-11-12)
- 10 hard cuts of ~1.0 s, ONE caption on every shot, thin white sans (Helvetica Neue Light), ~3.4 % of width, upper third (33 % down), soft shadow. The caption is a contrast hook ("If a boring life looks like this", "Tell me this isn't enough"); `CAPTIONS` in `gen_garden.py`, never reuse one from the last 3 videos.
- Subject: a real country home outdoors in strong sun, vivid but natural colour. Formula: 1 girl in a patterned dress holding a fresh pick (shot 1 = sound you can see: a soft rustle as the stem is gently lifted, never a sharp snap) → sky/field → harvest basket top-down with an animal wandering in → garden arch/path → fruit platter on flowers → animal beats (wide, then close) → flower meadow → house window with flowers → sunset through trees. Slots 2-9 are shuffled per idea so two videos never share an order.
- Sound: ambience plus the shot's own sound; music = the reference's own track at `~/.config/museai/music/ref5-boring-life-music.m4a` (user 2026-11-12: "using this music exactly for this kind of video"), `compose.py --music` as is, 10 s. It is someone else's recording: a post can be muted or claimed; keep the original piano option (step 4) as fallback. A second saved track for this style: `~/.config/museai/music/ref6-healing-style2-music.m4a` (25.6 s, from the harvest reference; used for hv gm-0005 Normandy). Alternate the two tracks between garden videos. ref6 is only -29.6 LUFS, so the 1.0 s action sounds (-22) drown it: always add `--music-lufs -20` with it (the Normandy video had it inaudible).
- Render: `HV_STYLE=garden DURATION=4 scripts/shot "<brief>" sN.mp4` per shot in a `render-queue` jobs file; compose: `python3 scripts/compose.py --idea idea.json --music ~/.config/museai/music/ref5-boring-life-music.m4a --out healing-<slug>.mp4 s1.mp4@1.0 ...` (concept `montage`: 1.0 s per shot stretched to the 22 s minimum, sans caption; see "Length and pours").
- Different from classic: outdoors not kitchen, saturated sun not muted, 1.0 s not 1.2-2 s, caption on top not centre, harvest and animals not baking.

### pov-ritual (reference 7, "POV : All you need is flowers and a cup of tea", 9:16, 9.2 s, measured 2026-11-13)
- 12 shots of ~0.75 s (reference: hard cuts at 0.9, 1.77, 2.67, 3.53, 4.43, 4.87, 5.47, 6.33, 7.2, 7.67, 8.1 s). compose uses 0.15 s dissolves for this concept: the user finds hard cuts too strong, and a 0.4 s blend would eat half of a 0.75 s shot.
- Caption: ONE two-line white bold serif (Times New Roman Bold, 4.2 % of width), left-aligned at 15 % from the left, 18 % down, soft shadow: `POV : All you need is` / `<A> and <B>`, A = what she gathers outside, B = what she makes inside.
- Story in a FIXED order (one small ritual, not a shuffled montage): 1 waist-down walk in the garden with a can or basket → 2 close-up of A growing → 3 A gathered in her hands → 4 wide of the village (where we are) → 5 inside, from behind, she sets A on the table → 6 opens a cupboard → 7 lifts out the vessel → 8 a drawer of B's ingredients → 9 the B action (pour, slice, stir) → 10 an animal at the open door → 11 the animal walks in (the small funny surprise) → 12 the finished table, she enjoys it. Her face is never shown; one outfit in every shot.
- Look: warm low sun, honey stone, rust and green outside; bright cream rooms with dark wood, rattan and blue-and-white china inside.
- Music: the reference's own track `~/.config/museai/music/ref7-pov-ritual-music.m4a` (9.2 s, -13.6 LUFS, already loud: no `--music-lufs`). Someone else's recording: a post can be muted or claimed; fall back to the step 4 piano.
- Render: `HV_STYLE=ritual DURATION=4 scripts/shot "<brief>" sN.mp4` per shot in a `render-queue` jobs file; compose: `python3 scripts/compose.py --idea idea.json --music ~/.config/museai/music/ref7-pov-ritual-music.m4a --out healing-<slug>.mp4 s1.mp4@1.0 ...` (concept `ritual` sets the caption and the dissolve; shots stretch to the 22 s minimum, see "Length and pours").

## The two classic concepts (measured on the user's reference reels, both 9:16, ~9.8 s)
| | postcard (reference 1) | ode (reference 2) |
|---|---|---|
| shots | 8 shots, ~1.2 s each, soft 0.4 s dissolves (cuts 1.5, 2.8, 3.9, 5.1, 6.3, 7.5, 8.7 s) | 6 shots, ~1.6 s each, soft 0.4 s dissolves (2.1, 3.7, 5.3, 6.6, 8.3 s) |
| subject | a Welsh hill farmhouse on an overcast day: garden table with teapot and flowers, open casement windows onto green hills, copper pans and a kettle in the kitchen, potted petunias by the stone door, candles on the sill | sunny Edwardian rooms: a sheer curtain billowing over a bed, dappled light on a sofa, a lampshade fringe swaying, leaves outside a bay window, a book's pages turning |
| text | ONE small white serif line, centred, the same on every shot ("the way I want to live:") | one phrase per shot, the sentence runs on ("a love letter to the wind that / ... / and turns the pages"), each phrase is what that shot shows |
| camera | handheld, almost still, tiny drift | handheld, almost still; the subject (wind) does the moving |
| sound | soft music over the place's ambience, -18 LUFS | the same, -14 LUFS |

What makes both "healing": nothing hurries, every shot has ONE gentle living motion (steam, breeze, rain, flame, petals, pages), muted warm colours, lived-in real homes, no faces to the camera, no talking. `prompt/healing.txt` (appended to every shot by `scripts/shot`) holds these rules; change them there, never in one video's prompt.

## Length and pours (user 2026-11-16, poffertjes: "too short, at least 20-30 s; the pouring doesn't look good")
- **Every video lasts 22-30 s.** `compose.py` stretches the shots to `--min-total` (default 22 s) and stops when a clip
  is shorter than its window. Plan 10-12 shots of ~2 s (the style's shot count is the minimum, not the plan), render
  them `DURATION=6` so a 2-3 s window starting at @1.0 fits, and pick each window where the motion is calm.
- **No close-up pours of thick liquids** (batter, honey, cream, thick sauce): muse draws them as a fat, broken ribbon
  that floats or splits. Show the moment before (jug tilted, first drop) or after (filled pan), or the pour from 1 m
  away in soft light; thin liquids (tea, water, milk into tea) are fine. Never open a video on a pour of batter.
  Check every liquid shot on the contact sheet frame by frame before compose; re-render or drop it when the stream
  breaks, thickens or hangs in the air.

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
1. **Pick**: `python3 scripts/ideas.py next --season now > idea.json` (or the user's idea / filters). The idea carries a `hook` format (see "Hook formats"): reorder and rewrite its shots to fit that format. Show the user the title, the hook, the shot list in one line each and the caption/lines; render after a yes (renders cost muse time). Human away → `webex ask`.
2. **Write the shots**: each `shots[k]` of the idea is the brief of one shot. Make it concrete for that home and moment (real objects, which way the light falls, the one thing that moves) but keep the subject. Every postcard idea in the bank opens "Through an open old window ...": replace that first shot with an opener from the rotation (see Looks). Ode: shot k must SHOW phrase k (the curtain lifts on "lifts the curtains"). Rewrite ode phrases in fresh words when the same subject was used before (`ideas.py list`), keeping one sentence that runs over the shots.
3. **Render** through one queue, one shot at a time (muse-video "Server": never every shot at once): write `jobs.txt` with one line per shot and run it in ONE background call:
   ```bash
   scripts/shot "<brief of shot 1>" ~/Movies/museai/healing-<slug>/s1.mp4     # one such line per shot in jobs.txt
   ../muse-video/scripts/render-queue ~/Movies/museai/healing-<slug>/jobs.txt
   ```
   6 s per shot (`DURATION=`), 9:16. `prompt/healing.txt` asks for ambience only (no music), the girl's look (long chestnut hair, never facing the camera; outfit random per video, `ideas.py next` puts it in her shots, never always the white/cream sweater) and real gentle motion.
4. **Music**: soft, gentle solo piano from ACE-Step that makes the viewer feel peaceful inside: a slow simple melody of long held notes over soft open chords, the same quiet level all the way through, never dramatic (no crescendo, no build, no bright running arpeggios), nothing above ~4 kHz. Render 2-3 seeds; `scripts/music` keeps only a take that passes `scripts/calm.py` (at most 3.0 onsets/s, centroid median at most 780 Hz, loudest 3 s at most 6 dB over the median) and exits 3 otherwise: render the next seed. Never deliver a take that failed it.
   ```bash
   n=<idea number>; for k in 1 2 3; do scripts/music "<season> piano lullaby, tender" ~/Movies/museai/healing-<slug>/p$k.m4a 24 $((n * 10 + k)); done   # ~5 min each, one at a time
   ffmpeg -i p37.m4a -lavfi "showspectrumpic=s=600x150:legend=0:fscale=log:stop=8000" p37.png
   ```
   `scripts/music` names the moving line in its tags ("solo piano" alone gave a melody-less drone) and asks for felt piano, low and middle register, sparse, pianissimo, no high notes. It starts at the body, then softens: pitch down 16 % (`asetrate=44100*0.84`), two 2.2 kHz low-passes, -20 LUFS. That brings ACE's spectral centroid from ~870 Hz to ~560 Hz (reference 3: 530 Hz). Check a take with `ffmpeg -i p.m4a -af aspectralstats=measure=centroid,ametadata=print:key=lavfi.aspectralstats.1.centroid -f null -` (median 500-600 Hz). Seeds come from the idea number: the same tags and seed give the SAME track (hv-0005's seed 37 was hv-0001's music again), so never reuse a seed list. Reject seeds that smear into a drone (hv-0001: seed 23) or go silent before the end. `REF=ref.wav REF_STRENGTH=0.3` (audio2audio guided by a reference) is there but gave a smeared wash with no notes at 0.3; don't use it for delivery. `loops.py make` (Apple Loops) is the fallback; the user found those loops not soft enough. Never take the music from a reference reel: it is someone else's track (a claim or mute on upload); to use it, post with the platform's "use audio" instead.
5. **Check each clip**: contact sheet (`ffmpeg -i s1.mp4 -vf "fps=2,scale=180:-1,tile=6x2" -frames:v 1 s1.jpg`) and `python3 ../muse-video/scripts/qa.py s1.mp4 --travel 0 s1sheet.jpg`. Reject: text in frame, a face looking into the lens, warped hands or tableware, doubled or deformed animals, time-lapse sky, frozen-photo look. Pick the calmest 1.2-1.6 s of each clip (`clip@start`).
6. **Compose**:
   ```bash
   python3 scripts/compose.py --idea idea.json --music track.m4a --out healing-<slug>.mp4 s1.mp4 s2.mp4@2.0 ... [--shot 3] [--foley 1.0] [--music-in 0.8]
   ```
   Soft 0.4 s dissolves between shots (compose default; `--dissolve 0` only for a deliberate hard cut), soft grade, Georgia text slightly below centre with a soft shadow (postcard: one caption; ode: one phrase per shot), a REAL recorded ambience bed under the music, chosen from the idea's sound (`--bed rain|water|crickets|clips|<file>`, `--ambience 0.45`: under the music, like the references; muse's own rain is flat hiss, so it is only the fallback; drop better recordings in `~/.config/museai/ambience/<name>.wav`), each shot's own action sound kept in sync on top (see Hook), no fade-in (frame 0 is the action), fade out 0.5 s, -16 LUFS. `--shot 3` (or 4) makes a slower 20-30 s version: same shots, longer windows. `--dissolve 0.5` joins the shots with soft cross-dissolves instead of hard cuts (reference 4). Then qa + sheet on the result (shared step 6).
7. **Deliver**: cover with `python3 scripts/cover.py --at healing-<slug>.mp4@auto --eyebrow "<place> · <season>" --title "<hook>" --out thumbs/healing-<slug>_9x16.jpg` (soft italic serif centred on the brightest sharp frame (user 2026-11-12: thumbnail text in the centre of the screen), in one of four styles that rotate from video to video (`--style auto`, the default: `scrim` dark band + cream pill, `card` cream card + brown italic, `frame` thin cream border + label between rules, `caps` dimmed frame + spaced capitals; the one used longest ago in `~/.config/museai/cover-history.json`, and both covers of one video share it; user 2026-11-12: mix the thumbnail style), a soft dark scrim behind the text so it reads on any frame, the video's own line stays in the frame; NOT the travel-thumbnail shock style). The title is a **hook**, not the caption (user 2026-11-04: covers must catch Instagram / YouTube viewers yet suit a healing account): a calm invitation, feeling or small surprise, 2-5 words, lower case, no exclamation marks, no "you won't believe". Pick one no cover in the last 10 used (the folders on the Desktop); examples: "slow down with me", "come bake with me", "imagine your morning here", "nobody rushes here", "the slowest apple pie", "30 seconds of calm", "you deserve a slow day", "stay a while", "this is my kind of rich", "a quiet kitchen fixes everything", "wake up with the sun", "listen to the wind", "let it rain", "good morning, mist", "the birds woke me today". The eyebrow names the place and season ("Scottish Highlands · autumn"). Captions: `../social-captions` (`captions.py check` must PASS; YouTube description ends with `#Shorts`), opening with the video's line and naming the idea's real animal. Then shared step 7 (`FINAL=1 THUMB_DIR=thumbs CAPTIONS_FILE=captions.json ../muse-video/scripts/deliver.sh healing-<slug>.mp4 <work dir> healing-<slug>`, preview first). **Record before `FINAL=1`** (it trashes the work folder):
   ```bash
   python3 scripts/ideas.py record hv-0042 --video ~/Desktop/healing-<slug>.mp4 --hook <format used> [--shots shots.json]
   ```
   `--shots` = the briefs actually rendered (JSON list) when they differ from the bank's. Record only delivered videos.

## Story mode (user 2026-11-10, hv-0310 "Grandma's Cinnamon Cookies", 4:25, 16:9)
A longer narrated variant: she cooks while a voice tells a meaningful life story. Name files `healing-<slug>`; render 16:9 (`SIZE=16:9 DURATION=10` in `scripts/shot` jobs), ~36 shots for ~4.5-5 min.
- **Story**: a real-life story with a lesson the viewer takes away (reconnect with someone you love, don't carry anger, say it before it's too late), told in first person. The hook is the first sentence and a promise ("My grandma had one rule in this kitchen. Never bake when you're mad."). Arc: hook → place and who she is → the recipe step by step, each step carrying a memory → the quiet conflict → the turn (a found letter, a call) → the lesson, said plainly in the last two lines.
- **English**: natural, casual, native-speaker spoken English anyone can follow: short sentences, contractions, everyday words ("Okay, butter first", "Way more cinnamon than you think"), no poetic or literary words. 1-2 sentences per beat (~15 words), ~600 words in all.
- **One shot per beat**, the shot SHOWS what the line says (egg crack on "egg", the cat on "Biscuit"). Cooking steps in the kitchen, memories as cutaways (stool, garden bench, sink, fells). Beat order and shot briefs live in `story.json` (`beats: [{vo, shot, clip}]`).
- **Voice**: Kokoro `af_heart --speed 0.92` through `../place-story/scripts/vo.py story.json` (writes `vo/bN.wav`; first run downloads the model, can take several minutes: run in the background).
- **Render**: jobs file with a retry per shot (`for t in 1 2 3 4; do <shot>; [ -f sN.mp4 ] && break; sleep 45; done`), `render-queue -j 3` with 3 ready muse accounts (the user asked for speed; 1 at a time took ~10 min/shot). `internal_error` = failed submit, retry.
- **Music**: ACE piano as step 4, `secs` = story length (~280 s). It takes 15-25 min and 2-3 seeds may be needed: start it as soon as the voice length is known and compose the rest meanwhile.
- **Compose**: `python3 scripts/story169.py story.json --music p1.m4a --out healing-<slug>.mp4` (`--music none` for a silent-music cut; `--dry` prints timing). Per beat: clip graded + lifted, small serif subtitles hugging the bottom edge (38 px, at most 2 lines of ~84 chars, slim dark band + outline: readable on bright frames yet little of the scene; user 2026-11-12, twice: first too faint, then too big), timed to the voice, 0.6 s dissolves, clip foley at -31 LUFS under the voice (-18), limited and ducked under the voice like the piano (per beat `"foley_db": -15` for a clip whose people talk), -16 LUFS overall. lnorm.py writes AAC whatever the extension: stems are `.m4a`.
- **Story hook (user 2026-11-12)**: beat 1 is a curiosity hook that makes a stranger keep watching: a small confession or a promise ("I killed my first tomato plant. And what happened next changed how I wait for everything."), never a calm scene-setter or a greeting. Its shot matches the line and starts mid-action. Welcome and recipe intro come in beat 2.
- **No AI-looking acting (user 2026-11-12)**: never ask muse for crying, tears or big sad faces (the dead-plant shot looked fake): a sad beat is a quiet shot from behind, shoulders lowered, eyes on the thing, "perfectly calm, no crying". Two people talking face to face also looks fake (stiff mouths, mirrored heads): show a conversation as hands passing an object, two people side by side seen from behind looking at the garden, or a wide shot at a table with both looking at the bowl; the voice-over carries the words.
- **Shots must make sense (user 2026-11-12)**: when she does a task her head is bowed and her eyes are on the object (the potato she peels, the pig she drops the coin into, the seedling she plants); write "seen from the side, head bowed, eyes on X" in the brief, never "seen from behind" for a close task (muse then looks at the window). Food keeps the colour of the recipe in every shot (orange sweet potato porridge, red tomato soup; never pale or white), and a handed-over bowl must show its contents. Check the contact sheet for gaze, colour and props before composing; re-render at `DURATION=6` (10 s clips stall more).
- **Look rules for every shot** (`prompt/healing.txt`): the same girl (hair, hands; outfit varies per video), beautiful young hands, clean tidy kitchen. Judge the contact sheet for hand/face warping and clutter; re-render any shot that fails.
- **Deliver**: 16:9 + 9:16 covers (`THUMB_DIR` needs both for a horizontal video; `deliver.sh` exits silently when one is missing), captions without `#Shorts` (4 min horizontal is not a Short; `captions.py` only WARNs).

## More styles
- `styles/harvest-asmr.md` (user reference 2, 2026-11-12): hands-only garden harvest montage, ~1 s per crop shot, no text, real picking sound. Ideas: `scripts/harvest_ideas.py next`. Record with `--caption style:harvest-asmr`; never two videos of one style in a row.

## Hook: hold viewers past 5 s (insights 2026-11-05)
The user's insights: many viewers swipe away at ~2 s, others stay 6 s+, and the ones that hold are soft, gentle music over the REAL sound of a real action (a cat's meow, birdsong, a pie being cut, tea being poured). So every video is built for the first 2 s:
- **Shot 1 = a sound you can see**: a close-up of one action with a crisp sound that the viewer hears as it happens, started MID-action (the tea is already pouring, the knife is already in the crust, the cat is already meowing at her). Never an empty room, a landscape or a slow window reveal first. Pick from: pouring (tea, milk, honey, water over fruit), cutting / cracking (pie crust, bread, an egg into a bowl), sizzling (butter, pancakes), an animal sound (cat meow / purr, hens, birds at a feeder, a dog lapping water), kneading / slapping dough, rain on the window with sun.
- **Shot 2 or 3 = a small surprise or reward** (the cat jumps onto the table, steam bursts out as the lid lifts, the finished pie): gives a reason to stay past 5 s.
- Every brief names the sound of its action ("the soft glug of tea pouring into the cup"), so muse renders it in sync; `prompt/healing.txt` asks for close-miked action sound.
- Pick each clip window (`clip@start`) where the sound happens, not just where the picture is calm, and keep shot 1 at 1.5-2 s.
- `compose.py` does the rest: frame 0 is already the action (no fade from black), each shot keeps its OWN sound in sync (`--foley 1.0`: -22 LUFS, shot 1 at -16 LUFS), the real ambience bed stays under it, and the piano only fades in after `--music-in 0.8` s, so the first thing heard is the action. Use `--bed clips` only when the clips' own ambience is good; otherwise let the idea's bed (rain/water) play under the foley.
- Check before delivery: the momentary loudness in the first second (`ffmpeg -i out.mp4 -af ebur128=metadata=1,ametadata=print:key=lavfi.r128.M -f null -`) is within ~6 LU of the rest, and the action sound is audible over the piano in shots 1-3. A shot whose own sound is silent or hiss is re-rendered or moved away from the opening.

## Hook formats: rotate the opening structure (studied 2026-11-16)
The user asked for more catchy hooks and videos that never feel like old ones. Two large slow-living accounts (a home cook and gardener, 161K followers; a home and garden diarist, 1.4M) were studied frame by frame on 10 reels, from 133 to 58.9M views. Only the patterns are used here. Never copy their footage, music, caption text, or one specific creation: build each format from our own bank idea.
- **Repetition kills reach.** One account posted the same concept (a bowl made of dried orange slices) 3 times: 18.5M, then 1.3M, then 133 views. A hit is never re-made. Its format can come back, but only with a new subject, place and season.
- **What the hits share:** (1) the most striking frame comes first: a finished result, a giant or odd object, or a change you can see; (2) one clear payoff at the end (the last pass of a pattern, the room in full bloom, the first bite); (3) one subject followed from start to finish, not a mood montage; (4) the season's own moment (citrus in winter, blossom in spring, a summer table).
- `python3 scripts/ideas.py hook` prints the format used longest ago; `next` writes it into the idea (`hook`, `hook_rule`). Use it unless the user names a format. Never use the same format twice in a row, and record it: `record ... --hook <name>`.

| hook | first 2 s | rest | caption line pattern (write our own) |
|---|---|---|---|
| sound-first | close-up of one action whose sound you hear (see Hook above) | the home and its moments | "the way I want to live:" |
| result-first | the finished, striking result, held 1-1.5 s | how it was made, step by step; last shot: the result in its place in the home | "made this from <plain thing>" |
| same-frame | one locked-off framing (a corner, a table, a sill) | the same framing as time passes: bare branch to blossom, empty table to laid table, dough to loaf, morning to dusk. Render shot 1, extract its first frame, then render the rest with `IMAGE=first.png` so the framing holds | "<N> days in <M> seconds" |
| one-take | the process already moving (pouring, piping, folding) | the same process at 2-3 angles; the payoff only in the last 1.5 s | "wait for the end" style, but calm: "almost there" |
| twist | a familiar thing in an unexpected shape or size | how it was made, then it in use | "a <thing> that is really <thing>" |
| with-me | her in the place, arms full of the harvest or the bake | one item per ~1 s shot, each with a tiny lower-case label naming it | "<task> with me" |

- Every format still keeps the healing rules: one gentle motion per shot, soft music over real sound, no face to the lens, no hurry. A format never adds shock, fast zooms or loud text.
- Caption lines are a promise or a small question (time compressed, an invitation, "what <place> gives in one morning"). Write a new one per video; never reuse a line from the last 10 (`ideas.py list`).

## Looks (reference 3, 2026-10-31)
The user wants views "more beautiful and healing". Reference 3 is one handheld phone shot: a hand in a knit sleeve opens a white casement window onto a golden-hour garden, then wide sunlit hills with grazing animals. `prompt/healing.txt` asks for real phone footage in the true light of the hour (see Real look below). In briefs:
- **Vary the opener and the style.** The window reveal ("her hand in a cream knit sleeve slowly pushes open the casement window, and the view opens onto ...") opened hv-0001, hv-0005 and the first cut of hv-0014, and the user asked for different styles, "not this open window anymore". Pick an opener that none of the last 3 videos used (look at the first brief of each in `~/.config/museai/healing-history.json`). Every opener is a sound you can see (see Hook):
  - pouring in close-up (tea, milk, honey, water over fruit at the sink);
  - cutting or cracking (a knife through a pie crust or warm bread, an egg into a bowl);
  - sizzling in the pan (butter, pancakes, onions);
  - the animal making its sound (a cat meowing up at her, hens clucking, birds at a feeder, a dog lapping water);
  - hands kneading or slapping dough on a floured board, top-down.
  A still room, a wide view or a sleeping animal comes later in the video, never first.
  Also rotate the look between golden hour (reference 3) and bright midday sun (reference 4), and between `--dissolve 0.3` and `--dissolve 0.5`.
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
- **Something is happening in every shot**: her hands work (kneading, pouring, picking, wiping), she walks through the sun, an animal plays or eats, laundry flaps, water splashes. A static plate or empty window is at most one shot per video. Cuts `--shot 2.0`. Music stays the default soft felt piano even on sunny videos: the hv-0002 `MOOD=sunny` take (7.2 onsets/s) was "too dramatic", the soft take (2.25/s) was right. `MOOD=sunny` refuses to run without `SUNNY_OK=1` (only when the user asks for a brighter track). `scripts/music` refuses a take that fails `calm.py` (exit 3; `BUSY_OK=1` overrides, never for delivery); render the next seed.
- `compose.py` grade: natural saturation, a touch warm, fine moving grain (hides muse's plastic smoothness), auto exposure lift.
- Write "Static locked-off shot" for a still camera. "Phone on a tripod" put a phone on a tripod into 2 of 6 hv-0017 shots; `shot` refuses it.
- Judge the contact sheet before compose: any shot that looks like a render (glow, halos, clutter, clones, warped hands) is re-rendered, not kept.

## Sunny kitchen (reference 4, 2026-11-01)
The user's fourth reference (21.6 s, 9:16) is a bright modern home on a sunny midday: a white kitchen with an arched window onto a garden, a young woman in pink washing vegetables at a sink under the window, water running over fruit, an overhead view of her sorting fruit next to baskets of eggs, then the dining room under amber pendant lamps. Measured:
- 5 shots of 3.5-6 s, joined by ~0.5 s cross-dissolves, not hard cuts → `compose.py --shot 4 --dissolve 0.5`.
- Real phone footage of an ordinary task, done all the way through (open the window, wash, sort). The camera is steady; she is seen from the side or above, never facing the lens. No text on the video.
- Light: clear midday sun, white and pale-wood surfaces, green plants on every sill. Bright, not golden.
- Music: one clear piano melody in the middle register (melody notes ~600-750 Hz, chords 150-500 Hz), a note every 0.35-0.5 s, F/C major, ~72 bpm, birdsong under it, -16 LUFS overall. Spectral centroid ~1100 Hz: brighter than the hv-0005 soft chain (560 Hz). Render it with `MOOD=sunny SUNNY_OK=1 scripts/music ...` (only when the user asks) (no pitch drop, 4.5 kHz cut, -16 LUFS). Take 3 seeds and keep the calmest: the reference holds each note (1.9 onsets/s). Of the first three takes (seeds 401-403), 402 came closest (2.4/s, held notes); 401 (3.4/s) and 403 (4.9/s, centroid 1640 Hz) were too busy. Reject anything above ~3 onsets/s (`librosa.onset.onset_detect` in the ACE venv).
- Its own track is saved at `~/.config/museai/music/ref4-sunny-kitchen-piano.m4a` (`compose.py --music` takes it as is). It is someone else's recording: a video posted with it can be muted or claimed. For a post, prefer an ACE soft take (`MOOD=sunny SUNNY_OK=1` only when the user asks for a brighter track), or post without music and add this track in the app with "use audio".

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
- 2026-11-04: the user said some delivered videos had dramatic music; healing music must make viewers feel peaceful inside. Delivered Healing 01/02 measured 3.4-3.5 onsets/s and a 860-1020 Hz centroid (busy, bright). The fixes: calmer tags (50 bpm, long held notes left to ring, constant quiet dynamics, no crescendo or build-up), `scripts/calm.py` gates every take (onsets, centroid, swell), and `MOOD=sunny` needs `SUNNY_OK=1`.
- 2026-11-05: at 2.5 onsets/s every seed of hv-0026, hv-0042 and hv-0047 failed (2.79-4.25/s), though 2.8-2.9 takes still sound held and quiet; the dramatic takes the user disliked measured 3.4+. The limit is 3.0.
