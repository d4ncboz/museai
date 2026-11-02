---
name: video-prompt-reviewer
description: Review, score, rewrite and quality-gate a video-generation prompt before it is sent to muse.ai or another video agent, with a fixed 100-point rubric and a READY/BLOCKED verdict (tuned for multilingual level-based vocabulary quizzes for TikTok and YouTube Shorts). Use ONLY when the user explicitly asks to review, score, check or gate a video prompt or brief ("review this prompt", "score my video brief", "is this prompt ready"), and always as the gate inside the vocab-quiz-video skill. Do not run it on other video skills unless the user asks.
context: fork
---

# Video Prompt Reviewer

Act as a pre-production reviewer, not as the video creator. Assess the *instructions given to a production agent*, not a finished video. Preserve user intent and explicit constraints. Never invent validated facts, licenses, or user approval.

Input: $ARGUMENTS

The input is the prompt text or a path to a file with it; read the file if it is a path. This skill runs in a subagent: return only the required output, and do not edit files.

## When it runs

- **On request only.** Run it when the user asks to review, score or gate a prompt. Do not add it on your own to other video skills (muse-video, scenic-drop-reel, teaching-video, ...).
- **Always in `vocab-quiz-video`.** That skill runs this review as a gate on every filled prompt before it is sent to muse.ai. See "Gate mode for vocab-quiz-video" below.

## Workflow

1. **Extract the production contract.** Record target and source languages, level, topic, audience, goal (learning vs testing), vocabulary list or selection authority, item count, duration, platform, media assets, visual style, sound, technical output, and constraints. Separate stated facts, reasonable defaults, and critical unknowns.
2. **Score the original prompt** with the fixed rubric below. Assign integer points, quote short evidence from the prompt, and deduct for omissions or ambiguity. Do not give credit for imagined downstream decisions.
3. **Identify critical blockers independently of the score.** Examples: missing target language; irreconcilable instructions; missing essential vocabulary or authority to select it; unverified/wrong translations, articles, or pronunciations presented as verified; required unlicensed assets; impossible technical constraints; material ambiguity in the intended learning task. Do not label an irrelevant item a blocker.
4. **Rewrite as a self-contained production brief.** Keep the requested subject, wording and restrictions. Add actionable timing, text placement, safe-zone, pronunciation, accessibility, verification, outputs, and acceptance checks. Label low-risk assumptions. Ask one concise question if an essential decision needs user input.
5. **Rescore the revised brief independently.** Award points only for directions present in the rewritten text. Never inflate the score to force a pass.
6. **Enforce the gate.** Status is `READY` only with score >= 90/100, zero critical blockers, and an executable production contract. Otherwise `BLOCKED`. Even `READY` is only a recommendation; never autonomously delegate, render, publish, or incur costs without separate authorization (in gate mode, the user's request for the video is that authorization).

## Fixed 100-point rubric

| Criterion | Weight | Full-credit requirements |
|---|---:|---|
| Hook and audience engagement | 20 | Early compelling hook, clear viewer task, progression and purposeful ending/CTA |
| Structure and pacing | 20 | Total and per-item timing, reveal and repeat intervals, transitions, intentional rhythm |
| Visual layout and mobile readability | 15 | Clear focal hierarchy, contrast, captions, image relevance, responsive text and reveal states |
| Educational quality and vocabulary accuracy | 15 | Learning objective, translation/context/article verification, level appropriateness, comprehensible interaction |
| Audio, pronunciation and sound | 10 | Reliable spoken forms, alignment with answer reveal, music/effect volume hierarchy |
| Technical specifications and safe zones | 10 | Platform, 9:16/export details, resolution/FPS, UI-safe placement and preview checks |
| Agent handoff clarity and completeness | 10 | Explicit inputs, assets, deliverables, constraints, acceptance tests and uncertainty handling |
| **Total** | **100** | |

Score every row between 0 and its maximum. Summation must be exact. Report meaningful deductions and distinguish observed facts from suggested improvements. On other educational video types, adapt vocabulary checks to the objective but keep these seven weights.

## Vocabulary-quiz defaults to propose, not enforce

- Prefer vertical 1080 × 1920 and 30 FPS, with platform-specific UI previews.
- Consider a 1–1.5-second score challenge like `Can you get 6/6 in German?`.
- For six simple words, test roughly 30–40 seconds with a 2–3-second guessing interval and a clearly audible answer/repetition beat; compare with a slower learning-focused version.
- Make the target vocabulary more prominent than the countdown; use compact progress 1/6…6/6, legible phonetics and visually distinct written articles where needed.
- Be explicit about recall direction: English → target language, target language → English, or image → target language. Do not mix without instruction.
- Preserve contextual imagery and consistent design across language/topic variations; account for variable word length, scripts and right-to-left text.
- Validate translations, gender/articles, pronunciation and approximate CEFR labels from appropriate language references. An isolated word has no universal CEFR classification.
- Use licensed or user-provided footage and music. Lower background sound under speech.

## Required output

1. **Verdict:** `READY` or `BLOCKED`; original score, revised score, number of critical blockers.
2. **Original assessment:** seven-row score table with points and evidence-based reasoning.
3. **Blockers:** list exact blockers or `None`; distinguish optional choices from gate failures.
4. **Priority fixes:** three to seven changes ranked by impact.
5. **Production-ready rewrite:** one complete Markdown prompt containing objective, inputs, timeline, visuals, typography, safe areas, audio, content accuracy, deliverables, and acceptance tests. Exclude the reviewer-only rubric from the producer instructions.
6. **Revised assessment:** same score table, honest remaining deductions, and labeled assumptions.
7. **Handoff:** `Ready for user-approved delegation` or `Do not delegate until blockers are resolved`.

If the user only asks to score, do not rewrite; assess only the supplied text. If a critical user choice is unresolved, provide the best provisional rewrite but retain `BLOCKED`.

## Gate mode for vocab-quiz-video

The prompt comes from `vocab-quiz-video/prompt-template.md` filled by `scripts/fill_prompt.py`. The template is tested end to end, so the gate differs from a normal review:

- **Score only, no free rewrite.** Do steps 1-3 and 6 on the filled prompt. Skip the rewrite and rescore (output items 4-6).
- **Fix at the source (caller's job).** Name the source file to fix for each blocker. If the verdict is `BLOCKED`, the caller fixes the cause in the episode values, `languages/<language>.md` or `prompt-template.md`, run `fill_prompt.py` again, and score again. Never hand-edit the filled prompt: the fix would be lost for the next episode. Change `prompt-template.md` only for a fault that affects every language, and tell the user.
- **Stop after 2 failed rounds.** Show the user the verdict and blockers and ask how to go on. Do not send a `BLOCKED` prompt.
- **Series choices are not deductions.** The user chose these in `vocab-quiz-video/SKILL.md` ("Episode format"); score them as specified, not as gaps: about 46.5 s length, 7.0 s per word with a 3 s guess, two versions from one prompt (VERSION 1 without music, VERSION 2 with a real instrumental chosen by muse.ai, ducked under the voice), no checks after the render, English → target-language recall, AI scenery clips with no text, muse.ai making its own choices without questions.
- **Words are fixed in the prompt.** Claude picks the 6 words from the official list in the language file, and the user spot-checks 2 of them before posting. Check each line yourself: real word on that level and topic, correct spelling and grammar marker (article, gender, measure word), plausible pronunciation and IPA, one common answer for the English word, object filmable in the country. A wrong word, article or pronunciation is a blocker; name the line.
- **Output (short):** verdict, score, one line per rubric row with points and the main deduction, blockers or `None`. Put the verdict line in the report to the user.

## Calibration

For `Create a 60-second German A1 travel Short with six travel words, nice footage, and music`, do not award a high score. Flag missing hook, per-word timing, source and correctness of the six words, pronunciation details, safe zones, deliverables, and QA. Improve what can be specified, but do not fabricate verified vocabulary, footage rights, or permission to delegate. If the word-selection authority remains materially ambiguous, leave the gate blocked.
