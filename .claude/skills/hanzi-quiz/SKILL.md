---
name: hanzi-quiz
description: Make a ~57 s vertical (9:16) "guess the Chinese word" vocabulary quiz short through museai - 6 themed words (travel, food, family...), each a photo/clip scene + the meaning + three hanzi choices A/B/C, a draining 4-second countdown ring with ticks, then the answer card (big simplified hanzi, tone-coloured pinyin, meaning, a memory trick) read aloud in Standard Mandarin, a score row that fills as you go, and a comment-your-score outro that loops into the first frame. The first 3 s stack three hooks (boss-word scene punch-in, a challenge sticker, the hardest word shown huge with "?") so viewers stay instead of scrolling. Use for "Chinese word quiz", "vocab quiz video", "guess the word video", "HSK quiz short", "đố từ vựng tiếng Trung", "video like the German A1 quiz", or any language-vocabulary quiz short. Grammar lessons with a teacher go to teaching-video.
---

# hanzi-quiz

A vocabulary quiz short modelled on the "German A1 · Travel" quiz format (English cue, 5-4-3-2-1, answer
card, "How many did you get? /6"), rebuilt to hold attention harder. Paths are relative to this skill
folder (`.claude/skills/hanzi-quiz/`). Rendering motion clips, music and delivery reuse `../muse-video/`.
Never print `data/api_key` or `data/accounts.json`.

**Honesty rule**: never say a video, file or check exists or passed unless the command that makes it ran
and its output says so. When a step was skipped or failed, say which and why.

## What the reference did, and what this format changes
| reference (German A1, 59 s) | hanzi-quiz | why |
|---|---|---|
| opens on a dark "GERMAN · A1 Travel" title for 2 s | **3 hooks in the first 3 s**, all visible by 0.5 s (below) | a title card is the #1 reason people swipe |
| English word, then 5 s of countdown over a photo | meaning **+ three hanzi choices A/B/C**, 4 s ring that drains and turns red, ticks double in the last second | recall of hanzi from nothing is too hard for beginners; a choice lets every viewer play and commit to an answer (comment bait) |
| answer: article + respelling | big hanzi, **tone-coloured pinyin** (1 red, 2 orange, 3 green, 4 blue, neutral grey), meaning, **memory trick** (火 fire + 车 vehicle = train), slow + natural Mandarin read | the viewer leaves having learned something, not just guessed |
| same rhythm for 6 words | **rehook stickers** ("Harder now", "Most people miss this", "BOSS WORD") and a **score row** 0/6 → 6/6 | pattern changes every few words; the score is an open loop to the end |
| ends on a blurred frame + "Follow for more" | outro over the boss scene, "How many did you get?", comment CTA, last frame fades to the hook's first scene | comment prompt drives the algorithm; the seamless loop counts replays |

### The 3-second hook stack (fixed in `compose.py`, gated by `qa.py`)
1. **Visual pattern break (0.0 s)**: the boss word's scene (last, hardest word) with a fast punch-in
   and a short white flash. Never black, never a fade-in.
2. **Challenge text (on frame 0)**: `hook.text` as a tilted accent sticker, e.g. "Bet you can't get 6/6".
3. **Open loop (frame 0, teaser by 0.5 s)**: the boss hanzi huge with "?" + `hook.boss_teaser` ("Can you read this?")
   + the empty 0/6 score row. The answer only comes at word 6, so the viewer has a reason to stay.
- Sound: bass hit + whoosh at 0.0, `hook.say` from 0.25 s ("Can you guess all six? The last one is hard."),
  pops on each sticker. No silence > 0.4 s in the first 3 s.
- Rules for the hook copy (`quiz.py check` enforces the first three): ≤ 7 words; no greeting, "today",
  "lesson" or title; **no invented statistics** ("only 3 % get this" is a claim we can't back - use a
  dare instead: "Bet you can't get 6/6", "#6 is a trap"); speak to the viewer ("you"); keep the boss
  promise true (put the hardest word last).

## Quiz file
Copy `quizzes/travel-hsk1.json` and edit. Fields: `topic` (slug), `lang` (`en` | `vi`: UI strings and
hook/outro voice), `level`, `series`, `accent` (hex), `hook` {`text`, `say`, `boss_teaser`}, `outro`
{`text`, `say`, `cta`}, `rehooks` (up to 4, shown on words 2, 4, N-1; word N always shows "BOSS WORD"),
`words` (5-8; 6 is the default length, 57 s):
```json
{"hanzi": "火车", "pinyin": "huǒchē", "meaning": "train",
 "trick": "火 fire + 车 vehicle = fire-cart",
 "decoys": [["汽车", "qìchē"], ["飞机", "fēijī"]],
 "scene": "A red high-speed train gliding past a green valley on a sunny morning, low side angle, real photo."}
```
- One theme per quiz (travel, food, family, shopping, weather, body, school...); words go easy → hard,
  hardest last (it is the boss word the hook teases).
- **Decoys** are real words from the same theme that a learner could confuse (shared character, same
  category: 汽车 / 飞机 for 火车). Never nonsense, never two right answers.
- **Trick**: the characters' parts + a 3-6 word image, ≤ 48 chars; in the quiz language.
- **Scene**: what the word looks like in real life, no text in the frame (muse draws garbled letters).
  A passport, ticket or menu: say "no readable text". The subject sits in the middle; the top fifth
  stays calm (the score row and ring sit there).
- Simplified characters, tone-marked pinyin (neutral tone toneless: 行李 xíngli).
- **Second language** (bilingual audience, e.g. English + Vietnamese): set `"sub": "vi"` and add
  `meaning_vi`, `trick_vi` per word, `hook.text_vi`, `hook.boss_teaser_vi`, `outro.text_vi`,
  `outro.cta_vi` and `rehooks_vi` (same count as `rehooks`). Every English line then gets a smaller
  Vietnamese line under it (light blue on cards), the answer reads "train · tàu hỏa", and the cue adds
  "Tiếng Trung là gì?". Voice stays in `lang`. `quiz.py check` fails on a missing `_vi` field.

## Pipeline
Work in `~/Movies/museai/quiz-<topic>/` (`scenes/`, `voice/`). Deps per script are in its docstring
(`uv run --no-project --python 3.12 --with ...`).

1. **Content gate**: `scripts/quiz.py check quizzes/<topic>.json` → `RESULT ok` (word count, simplified
   hanzi, pinyin matches the hanzi via pypinyin, 2 real decoys, trick, scene, hook rules). Fix every FAIL.
2. **Scenes** (needs the museai server): `scripts/quiz.py scenes quizzes/<topic>.json <work>/scenes`
   → `01.png` ... one 1080x1920 photo per word (`--only N` redoes one; delete the file first). Look at
   all of them: no text, the subject reads at phone size, no two scenes look alike. Optional motion:
   render a clip per word from its still (`IMAGE=scenes/NN.png SIZE=9:16 DURATION=10 OUT_NAME=NN.mp4
   ../muse-video/scripts/muse-video -f prompt.txt <work>/scenes/`, one slow camera move, independent
   clips in parallel); `compose.py` uses `NN.mp4` over `NN.png` when both exist. Clips must be ≥ 9 s
   (the boss clip also plays under the hook and outro).
3. **Voice**: `scripts/voice.py quizzes/<topic>.json <work>/voice` → hook, outro and each word slow
   (-20 %) + natural (zh-CN-XiaoxiaoNeural, Standard Mandarin; en-US-AriaNeural / vi-VN-HoaiMyNeural for
   the hook and outro). `hook.wav` must be ≤ 2.7 s (it starts at 0.25 s and the hook ends at 3.0 s):
   shorten `hook.say` if not.
4. **Music** (optional, recommended): an instrumental bed, never sung (lyrics fight the Mandarin read):
   `uv run --no-project ../muse-video/scripts/music.py --engine musicgen --style "playful pizzicato quiz
   bed, light percussion, bright" --bpm 110 --intro-beats 0 --body-beats 110 --out <work>/track.m4a`.
   MusicGen weights are CC-BY-NC: personal posts only; say so when the user monetises.
5. **Compose**: `MUSIC=<work>/track.m4a scripts/compose.py quizzes/<topic>.json <work>
   <work>/quiz-<topic>.mp4` (drop `MUSIC=` without a track). Layout keeps clear of the platform UI: nothing
   above y 200, below y 1480, or right of x 960 between y 900-1480.
6. **QA**: `scripts/qa.py quizzes/<topic>.json <work>/quiz-<topic>.mp4` → `RESULT PASS` (format, -14 LUFS,
   hook: bright frame 0 with text + motion + sound by 0.3 s + no silence in 0-3 s, a visible change at
   least every 3.5 s, loop seam). Then a frame sheet at 0, 0.5, 1, 2.9 s and at one reveal
   (`ffmpeg -ss T -i out.mp4 -frames:v 1 ...`): read every card yourself - hanzi correct, pinyin colours
   per syllable, no text cut off, nothing under the right-side buttons.
7. **Deliver**: preview (`SendUserFile`, display render). Only after the user accepts:
   - captions: `<work>/captions.json` per `../social-captions/SKILL.md` (CTA = comment your score;
     Vietnamese first when `sub` is `vi`), `captions.py check` → PASS.
   - cover: `../thumbnail/scripts/thumb.py chinese <work>/thumbs <work>/scenes/01.mp4 --name quiz-<topic>
     --at 4 --zh "<first hanzi>?" --title "<quiz in the viewer's language, uppercase>" --sub "<6/6 dare>"
     --badge "<level> · QUIZ"` (a clean scene clip, not the composed video: its frames carry cards).
   - `FINAL=1 CAPTIONS_FILE=<work>/captions.json THUMB_DIR=<work>/thumbs ../muse-video/scripts/deliver.sh
     <work>/quiz-<topic>.mp4 <work> quiz-<topic>` (deletes the work folder after copying to the Desktop).

## Series ideas (keep a playlist)
Travel · Food · Family · Shopping · Weather · Colours · Body · Feelings · Numbers trap (一 vs 衣 vs 医) ·
Tone trap (mǎi buy vs mài sell): a "tone trap" quiz uses decoys that differ only in tone - the hardest
and most commented format. Part 2 promises in `outro.cta` only when part 2 is planned.

## Known limits
- PNG scenes move only by a slow push-in; muse clips look livelier but cost ~6 renders of account time.
- The answer position (A/B/C) is fixed per word by a hash of the hanzi, so re-composes stay identical;
  check that the six answers are not all on one letter (change a decoy order if they are).
- Edge TTS needs network; phrases are cached in `voice/.cache`.

## Files
- `quizzes/*.json` - quiz content (worked example: `travel-hsk1.json`)
- `scripts/quiz.py` - `check` content gate, `scenes` one muse photo per word
- `scripts/voice.py` - hook / word / outro voice lines
- `scripts/compose.py` - frames (hook stack, cards, ring, score row), SFX, music duck, mix
- `scripts/qa.py` - final gate (format, loudness, hook, pace, loop)
