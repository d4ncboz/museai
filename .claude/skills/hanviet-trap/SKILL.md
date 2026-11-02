---
name: hanviet-trap
description: Make a ~30 s vertical "Bẫy Hán-Việt" skit through museai - recurring pair from the EVERYDAY CHINESE episodes, Vietnamese student Linh (new dress every episode) and her Chinese friend Hạo: Linh misreads one Chinese word through its Hán-Việt sound (地道 ≠ địa đạo, 对象 ≠ đối tượng, 师傅 ≠ sư phụ), Hạo (or a role like a landlady or a guard) reacts and fixes it, the frame freezes with a red BẪY HÁN-VIỆT stamp, a truth card shows the real meaning, and Linh ends on an A/B comment poll plus next-episode teaser. Picks the next word from a pinyin-checked bank of 21 traps and logs what shipped so no word repeats. Use for "Hán-Việt trap", "bẫy Hán-Việt", "từ Hán-Việt dễ hiểu sai", "false friends Chinese Vietnamese", "next trap episode", or a short Chinese vocab skit built on a misleading Hán-Việt word.
---

# hanviet-trap

An EVERYDAY CHINESE-style skit series built on `../muse-video/`: same render, check, stitch, dub
(cloned voices), tone-coloured captions, hook, QA and deliver steps. This skill adds the word bank,
the clip briefs, the overlay engine (`fx.py`) and the episode log. Every step not written here follows
`../muse-video/SKILL.md`, and its rules win.

Run this skill's scripts from `.claude/skills/hanviet-trap/`, muse-video's from `.claude/skills/muse-video/`.

## Why this format
Vietnamese learners read most Chinese words through Hán-Việt, so they "know" words they don't. Only
this audience has the dilemma, so the hook stops the scroll and the poll pulls comments. A lecture
didn't work (user, 2026-11-02: "too ugly, not catchy, where is the hook? where is the character
introduction"). The skit form shows the mistake happening to a likeable recurring character.
Bank kinds:
- `meaning`: the Hán-Việt word means something else in Vietnamese (对象 = người yêu, 师傅 = bác tài).
- `tone`: a tone or neutral tone changes the word (地道 dìdao = chuẩn vs dìdào = địa đạo).
- `rude`: the word reads harmless but is crude or insulting (下流, 小姐). Linh says it and the partner
  is shocked. Teach it respectfully and never make the insult the joke.

Only words a Vietnamese learner really misreads go in. 便宜 was dropped: nobody reads it as tiện nghi.

## Episode structure (~30 s, 9:16)
| beat | ~s | clip | what |
|---|---|---|---|
| hook | 0-3 | A | hook band (`hook.py`) + name tags (character intro) over the first line |
| trap | 0-5 | A | partner says the word, Linh reacts with the Hán-Việt reading (speaker `linh`: partner setup, Linh says it, partner reacts) |
| stamp | +1.6 | post | freeze on the misreading, red BẪY HÁN-VIỆT stamp, `地道 ≠ địa đạo` card, scratch + boom |
| truth | 7-14 | B | partner explains; truth card (✓ real meaning, misreading crossed out); Linh says the line again correctly |
| poll | 14-22 | C | Linh alone to camera: `<quiz>什么意思？`; A/B poll card, "Comment A hay B nhé", teaser `Tập sau: 公公 ≠ công công` |

## Pipeline
1. **Pick**: `python3 scripts/trap.py next` (the first word never shipped) or `list` to choose one.
   - A word not in the bank: add it to `bank.json` first (all fields; `line`, `explain` and `quiz` use the word).
   - Then run `uv run --no-project --python 3.12 --with pypinyin --with opencc-python-reimplemented python scripts/trap.py check`. It must print `RESULT ok`.
   - Neutral-tone WARNs are the standard reading.
   - A FAIL where pypinyin guesses wrong passes only with `"py_ok": ["<field>"]`, after you check a dictionary.
   - Never invent a meaning. When unsure, leave the word out.
2. **Brief**: `python3 scripts/trap.py brief <id> ~/Movies/museai/Bẫy-Hán-Việt-NN/` writes:
   - `A.txt`, `B.txt`, `C.txt`: muse prompts, starting "NO TEXT ON SCREEN", with Linh's fixed face plus
     this episode's dress, the partner, the set, lip-sync, acting and audio rules (no music), and the script;
   - `plan.json`: hook, tags, stamp, truth, poll, teaser, cues, YouTube title and final file name.
3. **Still**: one two-shot still (Linh SCREEN LEFT, partner right, three-quarter faces, heads below 20 %,
   since the hook and the truth card sit in the top band), following muse-video "Faces toward the camera
   need a first frame". Linh and Hạo are the EVERYDAY CHINESE EP49 couple in everyday clothes, and the
   user wants those faces, not new ones (2026-11-02: "use the character which used for creating daily
   episode video"), and not the EP46 party look ("normal character, not birthday theme please").
   `/v1/images/generations` takes no reference image, so a generated still gets new faces. Use the real
   EP49 frames as stills, scaled to 1080x1920: `refs/linh-hao.jpg` (`plan.ref`, hallway two-shot) for
   clips A and B, `refs/linh-solo.jpg` (`plan.ref_solo`, Linh alone, frontal) for C. Render clips A and B
   with `IMAGE=` that still, then `CONTINUE_FROM`. Render C as its own clip: a centred still of Linh,
   head top below 20 %, joined with a hard cut (muse-video "Intro shot + cut", `planned_cuts=1`).
4. **Render, check, stitch, dub**: muse-video steps 1-8.
   - Use `check_clip.sh` with `SCRIPT=` and `GAZE=O` for A/B, `GAZE=C` for C.
   - Run `ease_seams.py`, then `stitch.sh`.
   - Dub with `dub.py` (W = Linh). The partner's letter follows the partner's sex in `cast`.
   - Build cues.json from `plan.json` `cues` plus C's quiz line.
5. **Captions**: `burn_subs.py` with `dubbed.cues.json` (zh / tone-coloured pinyin / vi).
6. **Overlays**: from `dubbed.cues.json`, find these times:
   - the end of the misreading line (`--stamp`);
   - the explain line (`--truth start,end`);
   - clip C (`--poll start,end`, `--teaser` at its last second).

   Then run:
   ```
   uv run --no-project --python 3.12 --with pillow python scripts/fx.py apply subbed.mp4 plan.json fx.mp4 \
       --tags 0.1,3.2 --stamp <T> --truth <s,e> --poll <s,e> --teaser <t>
   ```
   Every time is on the input's timeline; fx.py shifts the windows after the freeze by 1.6 s itself.
   Then run `hook.py fx.mp4 "<plan.hook>" hooked.mp4 <end of first line>`. Name tags sit at y≈49-56 %,
   between the faces and the captions. If tags cover a face in the still, say so before rendering.
7. **QA + deliver**:
   - Run muse-video `qa.py` on the dubbed, uncaptioned video. The freeze is a planned still: QA comes before fx.py.
   - Check frame grabs of the hook, the stamp, the truth card and the poll.
   - Deliver with `deliver.sh` under `plan.file` (`Bẫy Hán-Việt NN - 地道 không phải địa đạo.mp4`).
8. **Captions + log**:
   - Write Vietnamese post captions per platform (`../social-captions/SKILL.md`), with `plan.title` as the YouTube title.
   - After the user accepts the final: `python3 scripts/trap.py done <id> <final.mp4>`, then commit `history.json`.

**Storyboard first** (new look, new word kind, or when the user asks to see it): run
`uv run --no-project --python 3.12 --with pillow python scripts/fx.py board plan.json board.png [still.png]`.
It draws five key frames with the real overlay code, on the still or on a placeholder set, at no muse cost.

## Files
- `bank.json`: the curated traps. Fields:
  - id, kind, zh, py, hv, assumed, real, say_instead;
  - partner (name tag), speaker (`partner` | `linh`). `"cast": "hao"` makes the partner Hạo, the recurring
    man. Write a role cast only when the script needs someone Hạo can't be (公公 needs a married woman,
    a teacher and his wife, a ticket seller, a karaoke host, a guard);
  - setup (only when speaker is `linh`), line, react, explain, replay, quiz;
  - hook (≤ 8 words, shows the word), cast, set, note, py_ok.
- `history.json`: shipped episodes (created by `done`).
- `refs/linh-hao.jpg`, `refs/linh-solo.jpg`: the pair's face reference (EP49 hallway frames, no text).
- `scripts/trap.py`: list / next / check / brief / done. `LINH` + `DRESSES` and `HAO` + `FITS` keep the
  faces the same and rotate the clothes.
- `scripts/fx.py`: apply (tags, stamp freeze + SFX, truth, poll, teaser) / board.

## Maintaining this skill
A problem found in an episode becomes one of these, with the date, before the episode is redone:
- a bank fix;
- a `trap.py check` rule;
- an `fx.py` change;
- a line here.
