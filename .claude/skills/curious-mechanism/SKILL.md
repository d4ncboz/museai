---
name: curious-mechanism
description: Make a video for The Curious Mechanism (@curiousmechai) - a faceless, AI-illustrated educational channel that explains the hidden engineering, design decisions and strange history of everyday things, in a clean 2D cartoon look (bold outlines, flat colours, cel shading, expressive characters, teal / amber / cream with red for danger). Every story opens on what went wrong (an accident, a failure, a near miss) and then explains why. Long-form 8-12 min 16:9 mini-documentaries (one a week) and 30-55 s 9:16 Shorts (complete mini-stories), built from one episode.json - verified claims with 2 sources each, a script for the ear, illustrations through museai animated scene by scene with muse video, one fixed narrator voice, editorial labels drawn in the edit, a 1280x720 thumbnail and a QA gate. Use for "Curious Mechanism", "curiousmechai", "why are airplane windows round", "how X actually works", "hidden engineering of X", "everyday engineering video", "explainer like the airplane window one", or the next episode or Short of this channel.
---

# curious-mechanism

Paths are relative to this folder. Script: `scripts/cm.py` (run with
`uv run --no-project --python 3.12 --with edge-tts --with pillow python scripts/cm.py ...`).
The full channel playbook is in `playbook/` (`PLAYBOOK.md`, `brand/style-guide.md`, `templates/`,
`research/topic-backlog.md`, `production/001-airplane-windows/`). The channel kit (handle, bios, art) is
`../new-channel/channels/curious-mechanism/`. Never print `data/api_key` or `data/accounts.json`.

**Honesty rule**: never say a video, file or check exists or passed unless the command that makes it ran
and its output says so. Never put a fact into narration that is not a verified claim with 2 sources.

## The channel in five lines
- One video answers one question an ordinary viewer never thought to ask ("Why are airplane windows round?").
- Pillars: Everyday Engineering + Invisible Systems ~80 %, Strange Origins ~15 %, Forgotten Mechanisms ~5 %.
- Look: clean 2D cartoon, like a good animated educational series (`prompt/look.txt`, `prompt/avoid.txt`):
  bold outlines, flat colours with soft cel shading, expressive characters, deep teal, warm amber, cream,
  red only for danger or the key part, subject filling the frame. Never photoreal. No text inside
  generated images: labels are drawn in the edit. (2026-11-13: replaces the playbook's engraving look, which
  was faded on a phone; picked over a cinematic painted look after a side-by-side test of s002.)
  Change the look in those two files only. `CM_LOOK=painted` renders the old painted look
  (`prompt/look-painted.txt`) into its own work folder `<id>--painted` for comparison.
- Story: open on what went wrong (an accident, a failure, a myth), let the viewer feel it through people,
  then explain the mechanism, then the twist, then the everyday object today. Hook = the danger itself.
- People: anonymous, ordinary passengers, crew, engineers, with real emotion. Never a real victim's face,
  never invented dialogue or quotes, no gore. Show the accident itself (viewers expect to see it), but only
  from far away, as a witness would (a jet breaking apart high in the sky), or through what it leaves (an
  empty gate, a suitcase). Never people dying, never inside the cabin at the moment of the accident.
- Voice: one narrator for the whole channel (`CM_VOICE`, default `en-US-AndrewNeural`, rate `+0%`): a curious
  storyteller, warm, restrained, a pause before reveals. Change it only for the whole channel, never per video.
- Title formulas: *Why does X...?* / *The hidden engineering inside X* / *How X actually works*. Thumbnail:
  one subject, 2-4 words that are not the title.

## Pipeline (one episode = `episodes/<id>/episode.json`)
Order matters: research, then script, then pictures. Never generate images before the script is locked.

1. **Topic.** Pick from `playbook/research/topic-backlog.md`; score it with
   `playbook/templates/topic-scorecard.md`. Approve at >= 20/25; Evidence < 3 = reject, however good the rest.
2. **Research.** Fill `claims` in the episode: every fact the narration states is one claim with 2
   independent sources (title, publisher, URL) and `verified: true` only after you opened both and they agree.
   Prefer primary sources (accident reports, manufacturer docs, museums, textbooks). An AI answer is never a
   source. List myths: they often make the best twist. Cannot verify? Cut it, or say the doubt on screen.
3. **Script = scenes.** `python scripts/cm.py new <id> "<Title>" [--short]` copies `episode.template.json`.
   Each scene: `say` (narration for one picture, 4-8 s, written for the ear), `section`
   (hook / mystery / background / mechanism / discovery / payoff), `image` (`subject`, `show`, `variant`:
   main | cutaway | closeup | map | diagram) or the id of an earlier scene to reuse its picture, `move`
   (push_in | pull_out | pan_left | pan_right | pan_up | pan_down | still), `labels` (uppercase editorial
   labels drawn on the frame), `claims` (ids the line relies on).
   - Long-form: 1150-1750 words (8-12 min at ~145 wpm). Hook <= 20 s, no channel intro. Structure from the
     playbook: hook, mystery, background, mechanism (analogies), unexpected discovery, payoff.
   - Short: 75-130 words, 30-55 s, spoken hook <= 3 s (the danger: "This jet is about to break apart."),
     the incident (1-2 scenes), the mechanism (2-3), the twist, the payoff on today's object. A complete
     mini-story, never a trailer for the long video.
   - Reuse one illustration as wide shot, close-up and labelled detail (`"image": "S03"`, new move / labels).
     Long-form budget: 12-18 main + 8-12 close-ups + 4-6 cutaways + 2-4 maps.
4. **Gate.** `cm.py check <id>` must print `RESULT ok` (length, hook, every claim with 2 sources and
   verified, no filler phrases like "since the dawn of", no text asked of the image model, valid
   moves / reuse, title formula, 2-4 thumbnail words). `--draft` lets unverified claims through for a test
   render only; never publish a draft.
5. **Pictures.** museai must run on the real browser driver (`python -m museai` with accounts; the mock
   driver returns 64 px squares that QA rejects). `cm.py images <id>` renders each scene's illustration with
   the master prompt from `playbook/brand/style-guide.md` at the episode's frame (16:9 or 9:16) into
   `videos/curious-mechanism/<id>/img/`; existing files are skipped, `--only S04` redoes one. Look at every
   image at 100 %: reject photoreal frames, garbled letters, wrong mechanics (check against a real
   reference photo). AI illustrations are not automatically accurate technical diagrams.
6. **Voice.** `cm.py voice <id>` -> one wav per scene + `timeline.json` (0.3 s breath inside a section,
   0.7 s between sections, 1.2 s hold at the end; every episode ends with the `CTA` subscribe outro from cm.py). Listen to it before building; fix a word by rewriting the
   line (spell a name the way it sounds), then re-run (unchanged lines are cached).
7. **Animate.** Every scene is a muse video clip, not a still (user rule 2026-11-13: "I want animation").
   Each scene needs `motion`: what moves and how, in concrete terms (the crack grows in short jumps, the
   water rises, clouds drift); `move` becomes the camera line. `cm.py anim <id>` writes one
   `muse-video` job per scene into `anim/jobs.txt` (`STYLE=animation`, the scene's illustration as the
   first frame, `DURATION` = scene length + 0.5 s, min 5 s); run it in ONE background call with
   `../muse-video/scripts/render-queue anim/jobs.txt` (one clip at a time, ~10-15 min each).
   `--only S05` re-renders one clip (RETAKE). Look at every clip: same cartoon style and faces as the
   still, the motion happens, no warp, no text, no cut.
8. **Build.** `cm.py build <id>` -> `<id>.mp4` (1920x1080 or 1080x1920, 30 fps): each scene's muse clip,
   muted and cut to the scene length (a short clip holds its last frame); a scene without a clip falls
   back to a slow 8 % push / pull / pan on its still. Labels fade in after 0.6 s, narration -14 LUFS,
   optional licensed music (`music.file`, ducked under the voice), plus `<id>.srt` captions.
9. **Thumbnail.** `cm.py thumb <id> [--scene S03]` -> `<id>_thumb.jpg` (1280x720, paper left with 2-4
   words in ink blue + muted red, illustration right, brass CM mark).
10. **QA.** `cm.py qa <id>` checks frame, duration, audio, loudness, image size, time per picture and the
   thumbnail, then prints the playbook's manual checklist. Go through each manual line. Never publish with an
   unresolved factual error, a misleading thumbnail or a copyright doubt because of a deadline.
11. **Publish.** Description from `playbook/publishing/descriptions.md`: chapters, every source, "original
    illustrations created with AI-assisted tools", music licence, max 3 hashtags (`#howitworks
    #engineering #designhistory`). Turn on YouTube's *altered or synthetic content* label when the policy asks.
    Log music / SFX in `playbook/templates/asset-license-log.md` and results in
    `playbook/publishing/analytics/metrics-log.md`. Schedule: 1 long-form + 2-3 Shorts a week.

## Episodes
- `s002-comet-corners` - Short "Why do airplane windows have round corners?": the 1954 Comet breakups,
  the water-tank test, the crack at the roof ADF window (not a passenger window), stress at corners.
- `s001-window-hole` - first test Short (hole in the window), engraving look; rejected by the user
  (look hard to see, no incident hook). Kept as a reference, not for publishing.
- Long-form 001 airplane windows: research leads in `playbook/production/001-airplane-windows/`
  (none verified yet; the Comet crack origin nuance is the trap most videos get wrong).

## Rules
- Do not mass-produce near-identical videos: each one needs real editorial input (YouTube's
  repetitive-content rule is the main monetisation risk for AI channels).
- Never invent quotes, dialogue or historical scenes. Stylised illustration only, never fake evidence.
- Change rules in this file, `scripts/cm.py` or `playbook/`, not in one episode's prompts.
