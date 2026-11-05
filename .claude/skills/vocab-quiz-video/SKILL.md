---
name: vocab-quiz-video
description: Make a vertical vocabulary quiz video (TikTok / YouTube Shorts) for any language and level with ONE prompt in muse.ai - hook "Can you get 6/6?", 6 words over scenery from the language's country, fast ~36 s cut with the first word at 1.5 s, English prompt with a 2-1 circle countdown, a reveal chime, the answer with gender-colored article and IPA said once with a listen-and-repeat pause, a recap, one score CTA and a next-episode teaser. Use when the user asks for a vocabulary / word quiz / flashcard video in German, Spanish, French, Japanese, Chinese or another language, names a level (A1, A2, B1, HSK 2, N5, ...) and a topic, or wants a new episode of the vocab quiz series.
---

# vocab-quiz-video

One muse.ai chat, one gated prompt, one MP4. muse.ai renders 6 scene clips, builds the video itself with ffmpeg and TTS on its own machine and sends it without background music (the user adds music on TikTok). This skill picks the words, fills and gates the prompt, sends it through `browser-harness` and downloads the video. No checks after the render: the gate is the only quality step.

Paths below are relative to this folder (`.claude/skills/vocab-quiz-video/`).

Needs: `browser-harness` connected to a Chromium/Chrome that is logged in to muse.ai (setup: `docs/browser-harness.md`), and `uv` for the gate (`uvx`). Unlike `muse-video`, this skill does not use the museai server: muse.ai itself builds the final video.

## Files

| File | Role |
|---|---|
| `prompt-template.md` | The one muse.ai prompt, language-neutral, with `{PLACEHOLDERS}` |
| `languages/<language>.md` | Language playbook: values for the language placeholders (front matter) + notes, word-list rules, lessons |
| `languages/german.md` | **Reference playbook** (tested end to end). Copy its shape for a new language |
| `languages/_new-language.md` | Empty playbook to copy |
| `series.md` | Series plan, design system, pre-post checklist, analytics log |
| `log.md` | Your own log of made episodes (file, chat, gate) and words used. Git-ignored; copy `log.template.md` on first use |
| `log.template.md` | Empty log to copy |
| `scripts/fill_prompt.py` | Template + language file + episode values → final prompt |
| `scripts/muse_run.py` | browser-harness script: new side chat, send, wait for the video, download it |
| `scripts/run_parallel.sh` | Several prompts at once on one browser profile, one background tab each |
| `scripts/check_video.sh` | Manual use only, not part of the flow: format, ticks, speech-to-text, frame sheet |

## Episode format (same in every language)

- 1080x1920, 30 fps, about 36 s (fast cut, default since 2026-11-04; episodes 1-14 are the 50 s baseline). Ticks, reveal chime + voices only, no background music (added on TikTok).
- 0-1.5 s hook over clip 1 playing in full color: "{LANGUAGE} {LEVEL}: Can you get 6/6?" + small "{TOPIC}" label. English narrator at 0.1 s: "Can you get six out of six?"
- 6 words × 5.0 s, progress `n/6` top-left, clip keeps moving:
  - 0-2.0 s: compact card with the English word; small circle countdown 2-1 below it, a soft tick at the start of each number.
  - 2.0-2.2 s: reveal, 200 ms fade + scale-in and one soft chime (means "here is the answer", never "you were right").
  - 2.2-5.0 s: answer (article colored by gender, article always written) + IPA. Voice once at 2.3 s; then "Listen & repeat" and silence for the viewer to say it back.
- 4.5 s end over clip 1 again (loops into the opening): 0-2 s recap of all 6 answers, then "What was your score? 0–6", "Comment below", small "Next: {LANGUAGE} {NEXT_LEVEL} {NEXT_TOPIC}". English narrator at 2.1 s: "What was your score? Comment zero to six!" One ask only.
- All 6 clips: same warm color grade, real motion or a gentle push-in, framing varied, object large in frame.
- All text is added by ffmpeg. The AI clips contain no text.

Why it is built this way (tested on muse.ai, 2026-11-02): one AI clip is ~10 s and not controllable, at most 6 AI clips per message, and the model cannot spell text reliably inside a scene. muse.ai has ffmpeg and TTS on its own machine, so it can do all overlays and the join itself. User choices: English stays visible during the countdown; small circle timer; listen & repeat; English narrator on hook and end card; after the 2026-11-04 review: fast 36 s cut (first word at 1.5 s, 2 s guess, 5 s per word), IPA only, gender colors der blue / die red / das green, reveal chime, recap and one score CTA; one video without music, music added on TikTok (muse.ai music was a sine-wave chord bed when left free); one new chat per video.

## Steps

1. **Pick the episode.** Language, level, topic, next level and topic. Check `series.md`: the teaser must name an episode that will really be made. If the language has no file in `languages/`, create one from `_new-language.md` first (see "New language").
2. **Pick the 6 words** and write them to `/tmp/vocab-german-a1-travel.words.txt`, one per line in quiz order: `English | answer | pronunciation` (example: `bridge | die Brücke | /ˈbʁʏkə/`). Rules:
   - From the official list in the language file's `word_list` for this level, on the topic; nouns, singular, in the language file's `answer_form` and `pronunciation` format.
   - One common answer per English word (skip "ticket": die Fahrkarte / das Ticket). No word with a second meaning the scene cannot make clear; follow the language file's `word_notes`.
   - The object can be filmed clearly in a scene from the country (not "airport" if the scene would be only sky).
   - Not in `log.md` → "Vocabulary" for this language (`fill_prompt.py` refuses repeats).
   - Mix easy and less obvious words; double-check spelling, grammar marker and pronunciation.
3. **Fill the prompt:**
   ```bash
   python3 scripts/fill_prompt.py --lang german --level A1 --topic Travel --next-level A1 --next-topic Food --episode 1 \
     --words /tmp/vocab-german-a1-travel.words.txt > /tmp/vocab-german-a1-travel.prompt.txt
   ```
   It fails if any placeholder is left unfilled, the words file is not 6 lines of 3 fields, or a word is already in the log. Name the prompt file after the episode (`/tmp/vocab-<language>-<level>-<topic>.prompt.txt`, same slug as `REC` and `OUT`), so videos made at the same time never share a file.
4. **Gate the prompt (always).** Run the `video-prompt-reviewer` skill (it runs in a subagent) with args `gate mode for vocab-quiz-video: /tmp/vocab-german-a1-travel.prompt.txt`. Send only a `READY` prompt (>= 90/100, no blockers). If `BLOCKED`, fix the words file, episode values, language file or template, fill again and re-score; after 2 failed rounds ask the user.
5. **Send it in a new muse.ai side chat and wait** (Chromium must be running with remote debugging on; never quit Chromium):
   ```bash
   PROMPT_FILE=/tmp/vocab-german-a1-travel.prompt.txt OUT=videos/german-a1-travel.mp4 REC=german-a1-travel \
     timeout 3000 browser-harness < scripts/muse_run.py
   ```
   Several videos at once on one browser profile (museai running): `bash .claude/skills/vocab-quiz-video/scripts/run_parallel.sh <profile> <prompt files...>` from the repo root. It launches the profile through `/v1/profiles`, runs each prompt in its own background tab of the profile's one window, 20 s apart, and closes each run's tabs when it ends.
   Run it in the background; it takes about 10-40 min. It prints the chat URL first and muse's final reply at the end, and saves `german-a1-travel.mp4`. Then it renames the chat to the prompt's first line, `Vocab Quiz #<episode> · <date> · <language> <level> <topic>`, so episodes are easy to find in muse.ai's side chat list. Send nothing else in the chat. Old or failed chats: Archive them (thread menu), never Delete.
6. **Report** to the user: the file path, chat URL, the gate verdict and score, the 6 words, and what still needs their ears/eyes (`series.md` → "By you").
7. **Log it.** If `log.md` does not exist, copy `log.template.md` to it. Add one row to `log.md` → "Content" and six rows to `log.md` → "Vocabulary" (the words file).
8. **Update `series.md`** (episode row + status) and, if something new was learned about the language, the language file's "Lessons".

If muse.ai sends no video or fails, start again in a **new** chat with the same prompt; after 2 failed runs report the failure.

## New language

1. Copy `languages/_new-language.md` to `languages/<language>.md` and fill every front-matter key (see `german.md` for a worked example).
2. Use the official word list for the level (DELE/Instituto Cervantes for Spanish, DELF/CEFR lists for French, HSK for Chinese, JLPT for Japanese, Goethe-Institut for German).
3. Pick the pronunciation aid learners of that language actually use (IPA, pinyin with tone marks, romaji, ...), and a font that covers the script.
4. Run one episode and fix the file from what the checks show.

## Gotchas

- Chats: open `https://muse.ai/thread/new` for every video. Never reuse a chat.
- The muse.ai sidebar lists other chats with words like "Generating"; wait for a `<video>` longer than 30 s, not for a status word (`muse_run.py` does this).
- 5 chats at once per account (2026-11-04, 10 videos, one window per run): 8 finished in 15-30 min, but 1 chat per account stayed on "Assistant is typing" with no output until the 45 min timeout, and the browser stalled with 20+ tabs. Retries in new chats worked. Since then runs share the profile's window as background tabs, close their tabs, and `bh-profile` starts Chromium with background throttling off.
- A background tab never loads `<video>` metadata, so `muse_run.py` does not read the length in the page: when muse.ai stops replying it downloads the new videos newest first and keeps the first one over 30 s (`ffprobe`). Scene clips (~5 s) sit in the chat next to the final video.
- muse.ai can keep its Stop button after the final reply, so `muse_run.py` checks new videos as soon as they appear instead of waiting for muse.ai to go idle.
- A chat reopened in a background tab that was never shown renders no messages (only "Show in library"); activate the tab to read an old chat. New runs are not affected.
- Account problems appear inside the chat, not as errors (2026-11-05, 3 accounts × 5 chats): one account asked to approve access to speech.platform.bing.com ("Allow once / Always allow this site"), another said "Please try again later… when the limit has reset". `muse_run.py` now exits with `ACCOUNT PROBLEM: …` as soon as such text shows; stop using that account and tell the user. Never click the approval for them.
- The chat rename in `muse_run.py` fails in background tabs (the active thread row is not found); rename by hand. Tested 2026-11-04: 2 runs in one window, Kitchen in 7 min, Body in 40 min, both found within 20 s of muse.ai finishing.
- Videos come back as `blob:` URLs; `muse_run.py` downloads them in 3 MB chunks.
- A new Chromium start shows "Allow remote debugging?" once; the user clicks Allow.
- Speech-to-text on a 2.5 s clip can mishear a correct word (v1: "Bahnhofer" for "Bahnhof"); if one word fails, ask the user to listen before re-rendering.
