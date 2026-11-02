---
name: vocab-quiz-video
description: Make a vertical vocabulary quiz video (TikTok / YouTube Shorts) for any language and level with ONE prompt in muse.ai - hook "Can you get 6/6?", 6 words over scenery from the language's country, English prompt with a 3-2-1 circle countdown and ticks, then the answer with pronunciation said twice (listen & repeat), score CTA and next-episode teaser. Use when the user asks for a vocabulary / word quiz / flashcard video in German, Spanish, French, Japanese, Chinese or another language, names a level (A1, A2, B1, HSK 2, N5, ...) and a topic, or wants a new episode of the vocab quiz series.
---

# vocab-quiz-video

One muse.ai chat, one prompt, one finished MP4. muse.ai renders 6 scene clips and builds the video itself with ffmpeg and TTS on its own machine. This skill fills the prompt, sends it through `browser-harness`, downloads the result and checks it.

Paths below are relative to this folder (`.claude/skills/vocab-quiz-video/`).

Needs: `browser-harness` connected to a Chromium/Chrome that is logged in to muse.ai (setup: `docs/browser-harness.md`), `ffmpeg`, and `uv` for the speech-to-text check. Unlike `muse-video`, this skill does not use the museai server: muse.ai itself builds the final video.

## Files

| File | Role |
|---|---|
| `prompt-template.md` | The one muse.ai prompt, language-neutral, with `{PLACEHOLDERS}` |
| `languages/<language>.md` | Language playbook: values for the language placeholders (front matter) + notes, word-list rules, lessons |
| `languages/german.md` | **Reference playbook** (tested end to end). Copy its shape for a new language |
| `languages/_new-language.md` | Empty playbook to copy |
| `series.md` | Series plan, design system, pre-post checklist, analytics log |
| `scripts/fill_prompt.py` | Template + language file + episode values → final prompt |
| `scripts/muse_run.py` | browser-harness script: new side chat, send, wait, download |
| `scripts/check_video.sh` | Format, ticks, speech-to-text of every answer, frame sheet |

## Episode format (same in every language)

- 1080x1920, 30 fps, about 46.5 s, no background music (ticks + voice only, music to be decided later).
- 0-1.5 s hook: "Can you get 6/6 in {LANGUAGE}?" + small "{LANGUAGE} · {LEVEL} · {TOPIC}" badge.
- 6 words × 7.0 s, progress `n/6` top-left:
  - 0-3.5 s: card with "{LEVEL} · {TOPIC}" and the English word (stays the whole time).
  - 0.5-3.5 s: small circle countdown 3-2-1 below the card, a tick at the start of each number.
  - 3.5-7.0 s: card switches to the answer + pronunciation. Voice at 3.6 s; "Listen & repeat" at 5.0 s; voice again at 5.3 s.
- 3 s end card: "How many did you get right?", "Comment your score: 0–6!", "Next: {LANGUAGE} {NEXT_LEVEL} {NEXT_TOPIC}".
- All text is added by ffmpeg. The AI clips contain no text.

Why it is built this way (tested on muse.ai, 2026-11-02): one AI clip is ~10 s and not controllable, at most 6 AI clips per message, and the model cannot spell text reliably inside a scene. muse.ai has ffmpeg and TTS on its own machine, so it can do all overlays and the join itself. User choices: English stays visible during the countdown; small circle timer; 3 s guess; listen & repeat; no music; one new chat per video.

## Steps

1. **Pick the episode.** Language, level, topic, next level and topic. Check `series.md`: the teaser must name an episode that will really be made. If the language has no file in `languages/`, create one from `_new-language.md` first (see "New language").
2. **Fill the prompt:**
   ```bash
   python3 scripts/fill_prompt.py --lang german --level A1 --topic Travel --next-level A1 --next-topic Food > /tmp/vocab-german-a1-travel.prompt.txt
   ```
   It fails if any placeholder is left unfilled. Name the prompt file after the episode (`/tmp/vocab-<language>-<level>-<topic>.prompt.txt`, same slug as `REC` and `OUT`), so videos made at the same time never share a file.
3. **Gate the prompt (always).** Run the `video-prompt-reviewer` skill (it runs in a subagent) with args `gate mode for vocab-quiz-video: /tmp/vocab-german-a1-travel.prompt.txt`. Send only a `READY` prompt (>= 90/100, no blockers). If `BLOCKED`, fix the episode values, language file or template, fill again and re-score; after 2 failed rounds ask the user.
4. **Send it in a new muse.ai side chat and wait** (Chromium must be running with remote debugging on; never quit Chromium):
   ```bash
   PROMPT_FILE=/tmp/vocab-german-a1-travel.prompt.txt OUT=videos/german-a1-travel.mp4 REC=german-a1-travel \
     timeout 2100 browser-harness < scripts/muse_run.py
   ```
   Run it in the background; a build takes 10-15 min. It prints the chat URL first and muse's final reply at the end, and saves the MP4.
5. **Check the video:**
   ```bash
   bash scripts/check_video.sh videos/german-a1-travel.mp4 de
   ```
   Then look at the frame sheet it prints. Pass = 1080x1920, ~46.5 s, 3 ticks per word 1 s apart, speech-to-text matches each answer twice, progress and answers right in the frames, no AI-made text.
6. **Report** to the user: file path, chat URL, the gate verdict and score, the 6 words, every check result, and what still needs their ears/eyes (`series.md` → "By you").
7. **Update `series.md`** (episode row + status) and, if something new was learned about the language, the language file's "Lessons".

If a check fails, re-render once in a **new** chat with the failing rule repeated more strongly in the prompt (gate the changed prompt again); after 2 failed renders deliver the best one and name the failure.

## New language

1. Copy `languages/_new-language.md` to `languages/<language>.md` and fill every front-matter key (see `german.md` for a worked example).
2. Use the official word list for the level (DELE/Instituto Cervantes for Spanish, DELF/CEFR lists for French, HSK for Chinese, JLPT for Japanese, Goethe-Institut for German).
3. Pick the pronunciation aid learners of that language actually use (IPA, pinyin with tone marks, romaji, ...), and a font that covers the script.
4. Run one episode and fix the file from what the checks show.

## Gotchas

- Chats: open `https://muse.ai/thread/new` for every video. Never reuse a chat.
- The muse.ai sidebar lists other chats with words like "Generating"; wait for a `<video>` longer than 30 s, not for a status word (`muse_run.py` does this).
- Videos come back as `blob:` URLs; `muse_run.py` downloads them in 3 MB chunks.
- A new Chromium start shows "Allow remote debugging?" once; the user clicks Allow.
- Speech-to-text on a 2.5 s clip can mishear a correct word (v1: "Bahnhofer" for "Bahnhof"); if one word fails, ask the user to listen before re-rendering.
