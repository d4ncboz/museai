---
name: teaching-video
description: Make a ~2-minute language-teaching video (a grammar point, pattern or phrase taught by one on-camera teacher) through museai, exported twice from one voice track - vertical 9:16 1080x1920 and horizontal 16:9 1920x1080, each composed for its own frame. Built for Mandarin taught to Vietnamese speakers - natural-sounding Northern Vietnamese narration (not robotic TTS), Standard Mandarin (Putonghua) examples, simplified hanzi + tone-marked pinyin + Vietnamese on clean cards, hook -> explain -> 3 examples -> fix a common mistake -> timed challenge -> recap. Use for "teaching video", "grammar lesson video", "dạy tiếng Trung", "bài học ngữ pháp", "lesson video in two formats", "Chinese grammar for Vietnamese", or any lesson/tutorial video with a teacher, examples and on-screen text. EVERYDAY CHINESE dialogue episodes stay in muse-video. Takes the shared brief (muse-video "Format skills", subject = the topic).
---

# teaching-video

One teacher, one voice track, two exports: `<topic>_vertical_9x16.mp4` and `<topic>_horizontal_16x9.mp4`.
Paths are relative to this skill folder (`.claude/skills/teaching-video/`). Rendering, seam handling,
stitching, Mandarin pronunciation and delivery reuse `../muse-video/` (read its SKILL.md rules on
rendering, `CONTINUE_FROM` and delivery; this skill only overrides what is listed here).
Never print `data/api_key` or `data/accounts.json`. This skill lives in this repo only.

**Honesty rule**: never say a video, file or check exists or passed unless the command that makes it
ran and its output says so. When a step was skipped or failed, say which and why.

## Why it sounds human, not AI
The voice is made first and the picture follows it (`scripts/voice.py synth`), never the other way round.
- **Voices**: `vi-VN-HoaiMyNeural` (Northern Vietnamese) + `zh-CN-XiaoxiaoNeural` (Standard Mandarin, Beijing
  Putonghua). Only `zh-CN-<Name>Neural` passes the guard; regional voices (liaoning, shaanxi, zh-TW, zh-HK)
  are refused. Both are female and sit ~0.5 semitone apart, so the language switch sounds like one person.
- **muse's own voice is never kept**: it reads Chinese inside Vietnamese as Hán-Việt or with wrong tones
  (muse-video, 2026-10-28). Every phrase is dubbed onto muse's lip onsets (`voice.py dub`).
- **Natural delivery**: whole phrases, never word-by-word; everyday talking pace, not a slow lesson voice
  (RATE_VI +25 %, RATE_ZH_SLOW -15 % for the learner read, RATE_ZH +5 % for natural reads and words inside
  Vietnamese; +10 % / -30 % was heard as too slow, 2026-10-28); short gaps;
  never pitch-shifted or time-stretched; "!" read as "." (the TTS shouts it); varied, jittered gaps
  (short inside a sentence, longer between ideas); a soft breath before a phrase that follows silence
  (`BREATH=0` drops it if it sounds like hiss); one EQ / de-ess chain and the same loudness for both voices;
  room tone under everything (digital silence between phrases is the clearest TTS tell); short room
  reflections; -16 LUFS.
- **Every Mandarin line gets a slow read with a silent repeat pause, then a natural-speed read** where it
  matters (examples), so learners hear both.

## Lesson file
Copy `lessons/bi-so-sanh.json` (比 comparisons, worked example) and edit. Fields: `topic` (file-name slug),
`title_vi`, `grammar`, `level`, `situation`, `accent` (hex colour of the target grammar), `teacher.cast`,
`teacher.set` (no writing anywhere in the set), and `beats`:
```json
{"section": "demo",
 "say": [{"vi": "Đi mua sắm, muốn so giá, bạn nói:"},
         {"zh": "这个比那个便宜。", "slow": true, "repeat": 1.5},
         {"vi": "Nói tự nhiên:"}, {"zh": "这个比那个便宜。", "repeat": 2.0},
         {"vi": "Cái này rẻ hơn cái kia."}],
 "card": {"type": "example", "label": "Ví dụ 1 · Mua sắm", "zh": "这个[比]那个便宜。",
          "py": "Zhège [bǐ] nàge piányi.", "vi": "Cái này rẻ hơn cái kia."}}
```
- `say`: `vi` / `zh` phrases in order; `slow` = learner pace; `repeat` = seconds of silent "repeat after me";
  `{"pause": 3.0, "countdown": true}` = the challenge pause.
- `card`: `example` (zh, py, vi; `mark` wrong|right; `py_ok` to accept a rare reading), `pattern` (`text`),
  `challenge` (`vi`, `hint`); `null` keeps the previous card, `false` clears it. `[...]` marks the target
  grammar in the accent colour (red on a `wrong` card); spans in `zh` and `py` must match.
- Viral rules (user rule 2026-10-29): the first 1-2 s is the hook itself, never "Xin chào các bạn" or the
  lesson name: open on the real-life problem or the mistake ("Bạn vẫn nói 我很喜欢吃 sai chỗ này?") with
  its card already on screen. Pick patterns tied to urgent everyday situations (ordering food, Wi-Fi,
  chargers, haggling, directions). Cards keep hanzi + tone-marked pinyin + Vietnamese side by side. The
  challenge is the comment quiz: the reinforce line asks viewers to write their answer in the comments
  ("Comment câu trả lời của bạn bên dưới xem đúng không nhé!") and echoes the hook's question, so a
  replay starts on the problem the viewer just solved. For a short cut-down (Shorts under 60 s), a
  stroke-order card of the key character loops well: end on the character the video opened with.
- Structure (fixed, checked): hook 0-8 s (common mistake or question), explain 8-30 s (Vietnamese vs Chinese
  pattern), demo 30-80 s (exactly 3 example cards, real situations), fix 80-100 s (one wrong + one right card),
  challenge 100-113 s (task, real >= 3 s pause, answer card), reinforce 113-120 s (pattern recap + invite).
- Writing for the voice: short sentences with commas at breath points (no sentence > 28 syllables without
  one); at most 4 language switches per beat; a word quoted inside Vietnamese is its own `zh` item
  (`{"vi": "Nhớ là chữ"}, {"zh": "比"}, {"vi": "đã mang nghĩa..."}`), never written inside the `vi` text.

## Pipeline
Work in `work/<topic>/` (scratchpad or repo-ignored dir); `9x16/` and `16x9/` folders under it.
Commands assume the uv `--with` lists in each script's docstring.

1. **Content gate**: `lesson.py check lessons/<topic>.json` must print `RESULT ok` (section order, 3 demo
   examples, wrong + right, challenge pause, simplified characters, pinyin vs characters with tone marks,
   no "!"). Fix every FAIL; read every WARN.
2. **Voice**: `voice.py synth lessons/<topic>.json work/<topic>/voice` -> phrase wavs, `master.wav`,
   `timeline.json`. It prints section ends vs targets and fails outside 110-128 s. Listen to `master.wav`
   before rendering anything (`SendUserFile` it when the user is around): it is the whole lesson's sound.
   Adjust text, `repeat` or rates and re-synth until it is right; phrases are cached.
3. **Teacher still** (same face in both formats): `scripts/still.sh lessons/<topic>.json work/<topic>/still`
   -> two 16:9 candidates; pick the most real one (hands, eyes, empty right side, no text) and run
   `scripts/still.sh lessons/<topic>.json work/<topic>/still <pick.png>` -> `first_16x9.png` +
   `first_9x16.png` (teacher crop, Real-ESRGAN upscaled). Only the reference still is cropped.
4. **Clip prompts per format**: `lesson.py clips lessons/<topic>.json work/<topic>/voice/timeline.json
   work/<topic>/9x16 --format 9x16` and the same with `16x9`. Each clip <= 9 s of speech + pauses, cut at
   breath groups, with this format's FRAMING (9:16: teacher centred, lower 45 % still; 16:9: teacher in the
   left third, right 55 % empty wall) and `prompt/teacher.txt` (lips only on lines, closed in pauses,
   locked camera, no text anywhere).
5. **Render** each format as its own chain, one chain after the other (muse-video "Server": one
   render at a time, never the two chains side by side):
   `QUALITY=0 SIZE=9:16 DURATION=10 IMAGE=still/first_9x16.png OUT_NAME=clip01.mp4 ../muse-video/scripts/muse-video -f 9x16/clip01.txt 9x16/`
   then every next clip with `CONTINUE_FROM=<previous clip>` instead of `IMAGE`. `QUALITY=0` because the
   prompt already carries the teacher style (muse-video's dialogue block would add captions rules).
   Check each clip before chaining (`../muse-video/scripts/check_clip.sh`, muse-video step 4): one
   person, no cut, no text, lips closed in SILENT spans. Re-render a failing clip once.
6. **Join**: trim each clip ~0.4 s after its last syllable, `ease_seams.py`, `stitch.sh teacher.mp4 ...`
   (muse-video steps 5-7).
7. **Dub**: `voice.py dub 9x16/teacher.mp4 voice/timeline.json 9x16/dubbed.mp4` -> also
   `9x16/dubbed.timeline.json`. Each breath group starts on muse's nearest lip onset; `LATE` lines mean the
   voice ran past the lips (re-render that clip, or force starts with `ONSETS=file.json`). muse's audio is
   dropped.
8. **Compose**: `compose.py lessons/<topic>.json 9x16/dubbed.mp4 9x16/dubbed.timeline.json
   9x16/<topic>_vertical_9x16.mp4 --format 9x16` (and `16x9` -> `<topic>_horizontal_16x9.mp4`). Cards per
   format (9:16 lower panel, 16:9 right panel), accent spans, wrong/right pills, Vietnamese line revealed
   after the Chinese is heard, countdown badge + ticks over the challenge pause, soft pop / chime SFX,
   captions of every spoken line (9:16 just above the card panel, under her chin; 16:9 bottom centre;
   none in the silent repeat pauses), optional `MUSIC=track.mp3` ducked under the voice, -16 LUFS. It prints the card cadence: WARN when a card
   is too short to read or nothing changes for > 8 s.
9. **QA (both files)**: `qa_lesson.py lessons/<topic>.json 9x16/<topic>_vertical_9x16.mp4
   9x16/dubbed.timeline.json --format 9x16` must say `RESULT PASS`: name, size, fps, 110-130 s, -16 LUFS,
   true peak <= -1 dBTP, room tone in pauses, challenge silence >= 3 s, no unplanned gap > 1 s, pitch range
   per phrase (MONOTONE), speaking rate, vi/zh voice match, Whisper hears the Vietnamese (>= 85 %), and
   muse-video `pron.py` hears every Mandarin syllable and tone. Then lip sync with muse-video
   `speakers.py` with the command qa_lesson prints (all lines `W`, a solo to-camera shot) and a frame sheet at the
   card times: text inside the panel, never over the face or mouth.
10. **Deliver**: preview both files from the work folder (`SendUserFile`, display render), with a
    Vietnamese `captions.json` per file, one caption per platform (`../social-captions/SKILL.md`; hook,
    what the viewer learns, the platform's CTA and hashtags; `captions.py check` PASS). Only after the user
    accepts (thumbnails per format with `../thumbnail/SKILL.md` style `chinese`, into `work/<topic>/9x16/thumbs`): `FINAL=1 CAPTIONS_FILE=captions.json THUMB_DIR=work/<topic>/9x16/thumbs ../muse-video/scripts/deliver.sh 9x16/<topic>_vertical_9x16.mp4 work/<topic>/9x16 <topic>_vertical`
    and the same for 16x9, with `--wide` on its thumbnails (each deliver trashes its own format folder), then trash `work/<topic>/`
    (voice, still). The two exports and their thumbnails are the only files left on the Desktop.

## Known limits (say them, don't hide them)
- Same teacher, voice and lesson in both formats, but each format follows its own render's lips, so
  phrase start times can differ by a few tenths of a second between the two files. Phrase audio is identical.
- muse may drift the face or outfit across a 15-clip chain; the shared still keeps the start the same,
  check_clip catches drift, but a re-render is the only fix.
- The synthetic breath is tunable (`BREATH=0`); judge it on headphones.
- Rendering is 2 x ~15 clips; a lesson takes hours of account time. Render the 9:16 chain first if the user
  wants one format sooner.

## Files
- `lessons/*.json` - lesson content (worked example: `bi-so-sanh.json`)
- `prompt/teacher.txt` - teacher style block appended to every clip prompt
- `scripts/lesson.py` - `check` content gate, `clips` per-format clip prompts
- `scripts/voice.py` - `synth` voice track, `dub` onto a render
- `scripts/still.sh` - shared teacher still + per-format first frames
- `scripts/compose.py` - per-format cards, countdown, SFX, music, final mix
- `scripts/qa_lesson.py` - final quality gate per export

## Maintaining this skill
A problem found in a lesson becomes a check (lesson.py, qa_lesson.py, compose cadence) or a rule here,
with the date and what happened, before the lesson is redone.
