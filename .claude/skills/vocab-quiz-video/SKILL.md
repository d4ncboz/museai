---
name: vocab-quiz-video
description: Make a vertical vocabulary quiz video (TikTok / YouTube Shorts) for any language and level with ONE prompt in muse.ai - hook "Can you get 6/6?", 6 words over scenery from the language's country, English prompt with a 3-2-1 circle countdown and ticks, then the answer with pronunciation said twice (listen & repeat), score CTA and next-episode teaser. Use when the user asks for a vocabulary / word quiz / flashcard video in German, Spanish, French, Japanese, Chinese or another language, names a level (A1, A2, B1, HSK 2, N5, ...) and a topic, or wants a new episode of the vocab quiz series.
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

- 1080x1920, 30 fps, about 50 s. Ticks + voices only, no background music (added on TikTok).
- 0-3 s hook: "Can you get 6/6 in {LANGUAGE}?" + small "{LANGUAGE} · {LEVEL} · {TOPIC}" badge. English narrator at 0.3 s: "Can you get six out of six in {LANGUAGE}? Let's go!"
- 6 words × 7.0 s, progress `n/6` top-left:
  - 0-3.5 s: card with "{LEVEL} · {TOPIC}" and the English word (stays the whole time).
  - 0.5-3.5 s: small circle countdown 3-2-1 below the card, a tick at the start of each number.
  - 3.5-7.0 s: card switches to the answer + pronunciation. Voice at 3.6 s; "Listen & repeat" at 5.0 s; voice again at 5.3 s.
- 5 s end card: "How many did you get right?", "Comment your score: 0–6!", "Next: {LANGUAGE} {NEXT_LEVEL} {NEXT_TOPIC}". English narrator at 0.3 s: "How many did you get right? Comment your score below! Next time: {LANGUAGE} {NEXT_LEVEL}, {NEXT_TOPIC}."
- All text is added by ffmpeg. The AI clips contain no text.

Why it is built this way (tested on muse.ai, 2026-11-02): one AI clip is ~10 s and not controllable, at most 6 AI clips per message, and the model cannot spell text reliably inside a scene. muse.ai has ffmpeg and TTS on its own machine, so it can do all overlays and the join itself. User choices: English stays visible during the countdown; small circle timer; 3 s guess; listen & repeat; English narrator script on hook and end card (hook 3 s, end 5 s to fit it); one video without music, music added on TikTok (muse.ai music was a sine-wave chord bed when left free); one new chat per video.

## Steps

1. **Pick the episode.** Language, level, topic, next level and topic. Check `series.md`: the teaser must name an episode that will really be made. If the language has no file in `languages/`, create one from `_new-language.md` first (see "New language").
2. **Pick the 6 words** and write them to `/tmp/vocab-german-a1-travel.words.txt`, one per line in quiz order: `English | answer | pronunciation` (example: `bridge | die Brücke | BRÜ-keh · /ˈbʁʏkə/`). Rules:
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
   Run it in the background; it takes about 15-20 min. It prints the chat URL first and muse's final reply at the end, and saves `german-a1-travel.mp4`. Then it renames the chat to the prompt's first line, `Vocab Quiz #<episode> · <date> · <language> <level> <topic>`, so episodes are easy to find in muse.ai's side chat list. Send nothing else in the chat. Old or failed chats: Archive them (thread menu), never Delete.
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
- The chat rename in `muse_run.py` fails in background tabs (the active thread row is not found); rename by hand. Tested 2026-11-04: 2 runs in one window, Kitchen in 7 min, Body in 40 min, both found within 20 s of muse.ai finishing.
- Videos come back as `blob:` URLs; `muse_run.py` downloads them in 3 MB chunks.
- A new Chromium start shows "Allow remote debugging?" once; the user clicks Allow.
- Speech-to-text on a 2.5 s clip can mishear a correct word (v1: "Bahnhofer" for "Bahnhof"); if one word fails, ask the user to listen before re-rendering.
