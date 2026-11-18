# Dialogue = shot / reverse-shot (jinxiu-01/02 lesson, 2026-11)

Two-person clips from muse make the listener mime the speaker's words, give "sound without lips" and
wrong-voice lines. Never render a two-shot with speech. One person per clip, cut between speakers.

## Pipeline (tools in `scripts/dialogue/`; they assume ~/Movies/museai/jinxiu-tools, copy there first)
1. Stills: one 9:16 single still per character per set, `character-bank/scripts/bank.py scene OUT "text" CHAR --size 1080x1920 --n 1`
   (MUSE_SKILL_DEV=1). Body faces camera, head turned ~15 deg to the off-frame partner, both eyes and
   whole mouth visible, lips closed, nobody else in frame. Same set text and light for both speakers.
2. `mkshots.py`: per speaker 2-4 clips (3-4 lines each), 1.6 s listening pause (lips closed) between
   lines, script file `.script` for QA. Split a person's lines over 2 clips so each stays <= 10 s.
3. `batch.sh "V X still.png" ...`: sequential renders + `check_clip.sh` QA, one retake on failure.
   One muse request at a time (also across projects: wait for other render-queues).
4. `shotcut.py V`: whisper words per clip -> line spans (char-count check, print `heard/expected`);
   cut each line `start-0.15 .. end+0.30` from its clip and join in dialogue order. Mismatch ->
   `w/spans.override.json` {clip: [[s,e] | [s,e,gap0,gap1] | null]} (gap = dead air removed inside a line).
5. `voice_unify.py` (W 235 Hz, M 118, L 92 formant .90), `finish.py spec.json` (hook, cards, recap,
   quiz, teaser), run with `uv run --with pillow --with numpy --with soundfile`.

## Smooth transitions per character
- Hard cut on the line end + 0.30 s breath; next shot starts 0.15 s before its first syllable. The
  alternation is the rhythm; no dissolves inside one conversation (dissolve only between scenes).
- Each character keeps ONE still, pose and eyeline across all their clips (same side of frame:
  woman looks right-of-frame partner, man looks left; keeps the 180-degree line). Never mirror.
- Reaction beat: lips closed, still jaw, slight attentive look; never nod or smile mid-line.
- Same light, lens, set and framing for both speakers so the cut is invisible; match costume.
- Cut length 1.0-3.5 s; a line > 3.5 s with dead air inside gets its gap removed (override file).
- Keep speakers' voices constant: one voice per character via voice_unify targets.

## Tail (review) must have sound
- Recap words from the dubbed audio, a spoken Mandarin quiz question (cloned bank voice, e.g. W-high-05
  via clone_tts.py with "……" before each clause), quiet guzheng bed; mix in numpy, not ffmpeg `amix`
  (amix + adelay produced a 0.01 s file). Background = blurred, dimmed last frame (not a zoom).
- Word card goes to the bottom safe zone (x 357-724, y 1440), never over heads. Hook <= 5 words
  when the head top is above y=250 (hook.py NO HEADROOM).
