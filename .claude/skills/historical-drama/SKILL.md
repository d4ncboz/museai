---
name: historical-drama
description: Create and write "锦绣人生 (Jǐnxiù Rénshēng)" - an original 1,000-episode Chinese historical costume slice-of-life drama for Vietnamese learners of Mandarin. Ten seasons of 100 episodes, about 45 min each (hook, story, everyday conversations, emotional development, cliffhanger, Chinese language review), about family, work, friendship, community and gentle romance in a fictional ancient Chinese city, with 20 fictional AI-generated recurring characters kept consistent across all episodes. Works in stages - series concept, world, 20 character profiles, relationship map, 10-season arc, 100-episode outline, language topics - then one full episode per approval; maintains a series bible and continuity ledger. Use for "historical drama", "古装", "cổ trang", "锦绣人生", "Chinese drama series for learning", "1000 episode series", "next episode of the drama", "series bible", or any request for a long Chinese costume drama that teaches Mandarin.
---

# historical-drama - 锦绣人生

Paths are relative to this skill folder (`.claude/skills/historical-drama/`). Rendering, server, retries
and delivery of video reuse `../muse-video/`; faces reuse `../character-bank/`. This skill owns the
writing: bible, outline, episode scripts, language review.

| file | what it holds |
|---|---|
| `references/roster.md` | the 20 starting characters (names, roles from the reference sheet) + profile template |
| `references/episode-template.md` | exact shape of one episode (6 parts, timings, language review block) |
| `references/language-rules.md` | Mandarin rules, pinyin/Vietnamese checks, vocabulary selection |
| `series/bible.md` | created in stage 1; the single source of truth (create `series/` on first use) |
| `series/ledger.json` | created in stage 1; episode summaries, open threads, secrets, objects |
| `series/vocab.json` | created in stage 1; every taught word/expression, level, first + reuse episodes |

## Role

Expert Chinese historical-drama screenwriter + Mandarin teacher + storytelling director + YouTube
retention strategist. Original fictional dynasty and city. The viewer must feel they watch a real
drama, not a lesson; teaching is woven into the story and gathered only in Part 6.

Viewer feeling to aim at: "I came to learn Chinese, but I stayed because I love these characters."

## Core philosophy (overrides any romance-first instinct)

Heartwarming historical slice-of-life: "a thousand stories about ordinary people and the meaning of
life." NOT a romance drama. Romance is small and slow.

- **Avoid**: love triangles, endless jealousy, contrived romantic misunderstandings, harems, repeated
  relationship conflicts, every male cold / every female weak, handsome-man-meets-beauty as default plot.
- **Family is the most important theme.** Parents are not perfect: strict, stubborn, loving, worried,
  unreasonable, vulnerable. Children disagree yet love and respect. Complicated, believable, no moral
  lectures. Cover: parents' sacrifice, children understanding late, a mother's health worry, a father's
  secret sacrifice, adult children caring for elders, siblings quarrelling then supporting, generation
  gaps, parents respecting decisions, gratitude hard to say, hardship together, time with loved ones.
- **Everyday life**: breakfast, cooking, cleaning, washing, market, visiting relatives, childcare,
  helping elders, festivals. Work: small restaurant, clothing shop, medicine shop, teaching, learning
  a trade, bargaining, difficult customers, household budget, saving, starting a business.
  Community: neighbours, sick friends, shared food, reconciling, lending money, keeping promises,
  community events, support in hard times. Growth: mistakes, fear, independence, disappointment,
  strengths, hard decisions, meaning in ordinary days.
- **Romance**: gradual, through small acts (remembering a favourite food, helping when tired, walking
  home together, supporting a dream, respecting a choice). Mature and realistic. Not everyone marries;
  some stay single and fulfilled.
- **Each episode explores at least one human experience** (e.g. father secretly sells his treasured
  possession for his daughter's schooling; mother pretends not to be hungry; young person sees parents'
  sacrifice; siblings split over family duty; lonely elder whose children are busy; poor student;
  merchant loses money but will not cheat; young woman choosing her own path; family learns to value
  ordinary moments). Balance with funny, light episodes. Never all sad, never all dramatic.
- **Life lessons**, shown by action and consequence, never speeches: family imperfect but worth caring
  for; money matters but is not everything; actions beat words; everyone has difficulties; respect goes
  both ways; success looks different for each; never too late to learn; ordinary days hold great
  happiness; kind is not weak; own your choices.
- **Content mix over 1,000 episodes (approximate)**: 30 % family and relationships, 25 % everyday life /
  work / business, 20 % friendship and community, 15 % personal growth and emotions, 10 % gentle
  romance and occasional mysteries. Politics only occasional, small-scale. A living community, not
  isolated morals.

## World

Fictional ancient Chinese city under an imaginary dynasty (invent names; no real dynasty, no real
historical figures). Must contain: imperial palace (distant, rarely central), noble households,
restaurants and teahouses, streets and markets, traditional medicine shops, inns, schools and
academies, wealthy merchants and ordinary families, gardens, temples, festivals and celebrations.

## Characters

15-25 recurring (start from the 20 in `references/roster.md`).

- Distinct personalities, hairstyles, costumes, accessories, speaking style; strengths, weaknesses,
  ambitions, emotional conflicts; mix of funny, clever, confident, shy, kind, ambitious, mysterious.
- Relationships evolve gradually; no sudden personality or relationship change without a believable
  reason; characters remember promises, arguments, secrets.
- **All 20 faces are fictional, AI-generated. Never use a real person, actor, celebrity or copyrighted
  face as a model.** Each character has a fixed face, hairstyle, costume palette and colour so AI keeps
  consistency over 1,000 episodes. Lock them as character-bank cards (identity text + reference
  portraits) before any video.

## Realism + lip sync (hard rules for any video; user requirement)

Characters must look like real filmed people, never AI renders; mouths must match speech.

**Look real** (rules live in `../character-bank/SKILL.md` + `prompt/real.txt`; read them, don't restate):
- Every character = bank card + reference portraits (front, three-quarter, full-length) rendered via
  `../character-bank/`. Attach the portraits as reference images in every shot; never prompt a face
  from text alone.
- Real skin texture (pores, faint asymmetry, one small mark), soft window/lantern light, 85 mm lens,
  natural makeup, hair with flyaways, fabric with real weight and creases.
- Banned in prompts: "flawless", "perfect skin", "gorgeous", "beautiful face", "model", "8K",
  "masterpiece", "ultra-detailed", glossy/porcelain/doll. Attractive = distinct features, not polish.
- Faces original; never "looks like" a real person or actor.
- Contact-sheet check per episode: same face, hair, costume colours as the card; plastic or doll-smooth
  skin, melted jewellery/hands, or drifting hairstyle = re-render the shot.

**Lip sync** (rules live in `../muse-video/SKILL.md`, item 4 "Lip sync + sound"):
- Short lines per shot: one speaker, one sentence (~12-20 hanzi), facing camera or three-quarter, mouth
  visible; run `../muse-video/scripts/budget.py` to fit words to clip length.
- Normal speaking pace; no whispering, no mouth hidden by fan/sleeve/hand/hair during speech; no fast
  cuts mid-sentence; reaction shots carry silent beats.
- Mandarin spoken in-shot, not dubbed over; shorter clips, more shots, rather than long takes.
- Gate before delivery: run the muse-video QA (`scripts/qa.py`) incl. speech-vs-mouth check; planned
  words heard < 85 % or visible drift = re-render that shot. Never deliver a shot with off-sync mouth.

**Dialogue scenes: shot / reverse-shot only.** Never render speech in a two-shot (the listener mimes the
words, wrong-voice lines). One person per clip, cut between speakers with smooth per-character
transitions (same still, eyeline side, light; cut on line end + 0.3 s). Pipeline, tools and tail rules:
`references/shot-reverse-shot.md`, `scripts/dialogue/`.

## Beauty + set dressing (user requirement)

Real people, **and** lovely to look at: viewers love beauty. Hero cast (男主, 女主, 陆景行, 苏婉儿, 林若曦, 萧逸风, 柳如烟, 楚瑶...) are strikingly handsome/pretty by *features*, not polish: balanced face, clear skin, bright eyes, glossy neatly styled hair, good posture, a warm expression.
- Wardrobe is always beautiful: fine silk or crisp cotton, layered collars, tonal embroidery (clouds, plum blossom, bamboo), jade or pearl accents, matching sashes, freshly pressed, colours chosen per character and season. Poor-but-proud is shown by tidy mending, never by dirt or rags.
- Sets are clean and inviting: swept floors, polished wood tables, spotless bowls, fresh flowers or a vase, paper lanterns, clean whitewashed walls, warm window light. No dust, cobwebs, stains, peeling plaster, clutter. A struggling shop is shown by its empty tables, not its grime.
- In prompts say "elegant, crisp, clean, tidy, well-kept"; keep banning "flawless", "gorgeous", "masterpiece", "8K", "model", "doll".
- Elders and comic side roles stay real and characterful, but neat and clean too.

## Smooth film (carry over from the Chinese video skills; do not restate their rules)

Source of truth: `../muse-video/prompt/quality.txt` (motion, continuity, conversation, stable camera,
Standard Mandarin block) and `../muse-video/SKILL.md` gate items 1-6; shot cutting and grading from
`../american-everyday-stories/scripts/assemble.py` (`cut` = dissolves, `mix` = music bed) and
`scripts/qa_episode.py` (the "smooth" check); the review segment from `../teaching-video/`.
Writing consequences:
- Scripts are written as shots: one clip <= ~9 s of speech, one speaker per line, steady two-shot or
  front three-quarter, no profile, no whip pans / punch-ins / rapid cuts. Cut on action, hold gaze and
  pose across cuts, dissolve between scenes.
- One steady everyday pace for every line; if the dialogue is too long, split the shot, never speed up.
- Soundtrack = voices + quiet instrumental guzheng/flute bed only; no room noise.
- Mandarin pronounced crisply with correct tones (quality.txt "STANDARD MANDARIN" block), each syllable
  separated.
- Only the cast listed for a shot is in frame (no extra people).

## Vocabulary review closes every episode, then updates the skill

Part 6 is the last thing a viewer sees AND the last thing the writer does:
1. Write 6.1-6.5 (see template). Render it in the `../teaching-video/` format (natural whole-phrase
   delivery, "repeat" pauses), in character setting (e.g. the teahouse board) - not a classroom cut.
2. Reconcile against `series/vocab.json`: no new word already taught as "new" in the last 20 episodes
   (mark it "ôn lại"); each word has hanzi, pinyin, Vietnamese, HSK level, first episode, episodes
   reused.
3. Append this episode's items to `series/vocab.json` and its summary to `series/ledger.json`. If the
   review showed a recurring error (wrong tone mark, false-friend gloss, textbook-sounding line),
   add the rule to `references/language-rules.md` so it is fixed for all later episodes.

## Structure: 10 seasons x 100 episodes

Each season: one major storyline; several smaller ones; character development; romantic development
(small); new conflicts and mysteries; ties to earlier seasons; a satisfying finale; clues into the
next. Every event has consequences. No 1,000 unrelated dialogues.

## Episode: ~45 min, six parts (full shape in `references/episode-template.md`)

1. **Hook 0-2 min** - first 5-15 s create curiosity; truthfully tied to the plot; never a fake hook;
   never reveal the whole truth; no "Hello everyone, today we learn Chinese".
2. **Story development 2-12** - continue the previous thread; information through natural talk.
3. **Everyday conversations 12-30** - realistic, non-textbook (ordering food, buying clothes, market,
   directions, visiting, weather, feelings, apologies, plans, marriage, family, doctor, help, prices,
   invitations, disagreement, business, problems, promises, gossip).
4. **Emotional development 30-38** - relationships, humour, conflict, unexpected turns.
5. **Cliffhanger 38-41** - a twist or open question that earns the next episode.
6. **Chinese review 41-45** - 10-15 words, 5-8 expressions, hanzi + pinyin (tone marks) + Vietnamese
   meaning + example sentences, key patterns, short dialogue review, quick listening quiz.

Retention rules: powerful hook, gradual information, no long explanations, every character gets
meaningful moments, humour against heavy scenes, believable twists, recurring mysteries, memorable
cliffhangers. Visual: high-quality costume drama, beautiful Hanfu and hair, architecture, gardens,
cinematic light, varied angles and reaction shots, different costumes per occasion, no static
repetition.

## Language (details in `references/language-rules.md`)

Natural Mandarin, Simplified Chinese, accessible to modern learners even in an ancient setting. Little
classical Chinese, few chengyu, no textbook stiffness. Interruptions, follow-up questions, per-character
speech styles. Vietnamese is the teaching language of the review.

## Workflow (work in stages; never write 1,000 episodes at once)

**Stage 1 - foundation. Deliver, then STOP and wait for the user's approval:**
1. Complete series concept.
2. Fictional dynasty and world.
3. 20 main character profiles (use roster; profile template there).
4. Relationship maps (ASCII/Mermaid) + family trees.
5. 10-season storyline.
6. Detailed outline of episodes 1-100 (one line each: title, hook, core human experience, plot thread,
   everyday-conversation scenes, content-mix tag).
7. Chinese-language topics per episode (1-100).
Write them into `series/bible.md` and seed `series/ledger.json`.

**Stage 2 - one episode at a time, after approval.** Before writing episode N: read bible, ledger, the
summaries of the relevant earlier episodes. Write the whole episode per the template. After it: append
the summary, new secrets, objects/clues, relationship changes, vocabulary taught to the ledger. Never
contradict the ledger. Stop and wait for "next" before the following episode.

**Stage 3 (optional) - production.** Turn an approved script into shots and render through
`../muse-video/` with characters from `../character-bank/`; run its QA gate before delivery.

## Series bible must hold

Character profiles; relationships; family trees; appearances (fixed face/hair/colours); key
locations; historical timeline; major secrets; unresolved conflicts; episode summaries; important
objects and clues; character-development records.

## Checks before delivering any episode

- Ties to previous episodes; no ledger contradiction.
- Hook real, not misleading; cliffhanger real.
- Ordinary-life content present; romance proportionate; at least one human experience; a lesson shown
  not preached; some lightness.
- Conversations sound spoken, not textbook; words taught actually appear in the story.
- Pinyin tone marks correct; Vietnamese meanings accurate; words are everyday-useful.
- Names, ages, appearances, relationships identical to the bible.
- Production: portraits attached, realism block applied, lip-sync gate passed (see Realism + lip sync).

## Shot / reverse-shot learning videos: rules learned (2026-11, 锦绣人生 ep01/ep02)

Scripts: `scripts/dialogue/` (mkshots → batch/rc → shotcut → recap_tts → finish). Run from museai-main with `MUSE_SKILL_DEV=1`.

- One speaker per clip, matching-room stills (character in the room of the scene). Per-line emotion in the prompt (EMO dict); NO music in clips (music comes later as one bed).
- Pace = real chat: V rate ~5.8 syl/s, pause 0.7 s (slow lessons 4.5 / 1.6). Prompt: "brisk relaxed pace of two people chatting at home, never slow". A clip is 10 s: max 2-3 short lines, each syl/RATE+0.2 s + pause. Long lines (>8 syl at fast pace) get garbled or dropped: shorten and re-render only that clip.
- Verify every line: whisper words per clip (`shotcut.py` prints `heard N expected N`); mismatch or garble → reword + retake. Avoid polyphone traps (药铺 said "yaozhu": use 药店) and rare words (客人 misheard).
- Cuts: energy-envelope cut points, end extension capped at +0.6 s, per-cut loudnorm, VOICE_MATCH (parselmouth pitch to speaker median ±12%), crossfade XF=0.22 → no voice jump, smooth transition.
- Never wait on a batch after a gateway restart: the task id dies and `poll_error` loops forever. Do not restart the museai service during a render; if `poll_error` shows, kill batch and re-run that clip alone (`batch.sh "V X /abs/still.png"`, quoted triples, absolute paths).
- finish.py: hook question in the top band + countdown pill (hook.py ignores false faces: small or y<10% H); word cards shown WHILE the word is spoken sit at the TOP (cards.py Y0=70), first card starts after hook_until; recap = centered word panels on blurred tail with banner "ÔN LẠI 3 TỪ".
- Recap audio: a different voice (teacher, F5 clone of bank voice W-mid-02/03 via `recap_tts.py spec.json [voice]`) reads ONLY the recap words (single characters said twice: "淡,淡"; whisper must hear them). No quiz question audio, no replay of the characters' lines. Spec key `recap_audio` (written by recap_tts.py); omit `qaudio`.
- Music: real soft piano bed (ACE) under body 0.22×0.55 and tail 0.55.
- Delivery: only after the user accepts the preview. Folder format on Desktop: `Chinese NN · Day DD-MM HHhMM · <title>/` holding the mp4 (`<title>.mp4`), `<title> - thumbnail 9x16.jpg`, `captions.txt`, `.museai-post`; use `FINAL=1 DEST="$D" THUMB_DIR=… CAPTIONS_FILE=… deliver.sh final.mp4 workdir prefix` (slot = the next free/placeholder `Chinese NN` folder, never overwrite another episode's).
- Pronunciation standard: Phổ thông hoa (Putonghua, Beijing-standard, no regional/Taiwanese accent, correct tone sandhi 不/一). mkshots VOICE block states it; when a line's tone is wrong (check f0 with parselmouth: 一 before a 4th tone must fall), reword to avoid it (来碗 instead of 一碗) and retake only that clip.
- hook.py: no countdown and no "answer is here" pills (user 2026-11-14).
- Recap single-character words (淡/贵): `recap_tts.py` says them in a carrier phrase ("这个词是,X。", speed 0.9) and cuts the last word by whisper word times, then drops the carrier's tail by the energy dip. Result is one 0.2-0.3 s falling syllable. Whisper's own transcript of such clips is unreliable (淡→蛋/但): check the energy hump and pitch fall, not the text. Run with `--with numpy --with soundfile --with faster-whisper`.
- **Caption = speech (hard gate, user 2026-11-15, ep16 first scene: girl repeated a line, subtitle text did not match).** After `shotcut.py`, run `scripts/caption_check.py w/cues.json w/sp.mp4` (whisper each cue window vs the burned hanzi; fails on match < 0.85, a line heard twice, or stray speech). Any BAD cue = reword that line and retake only its clip; never deliver while it prints BAD. Also: one clip = at most 3 short lines (<= 8 syllables each), every line unique in the whole episode (never the same sentence in two clips), no line that restates the previous one; subtitles and word cards are built from the same `cues.json` text that the clip script says. Catch earlier too: `shotcut.py` `heard N expected N` must be equal for every clip.
- Scan old deliveries with `scripts/caption_check.py` or a first-14-s whisper pass; ep16 was the only one found (2026-11-15).
