---
name: dream-life
description: Make a short vertical "dream life" video through museai - an impossible, gentle life filmed as if it were ordinary (picking the moon off a ladder, baking clouds, washing rainbows, riding a giant fluffy snail, a star shop at night, a snowy storybook town), in the user's reference looks - Pastel Americana (1950s Kodachrome candy-pastel suburb, giant plush animals), Lavender Fairytale (flower gowns, dandelion trees, lily lakes), Dream Workshop (1970s cream-and-amber star shop), Storybook Ink, Golden Nocturne oil painting, Cosy Anime and Porcelain Fantasy. 6 calm ~5 s shots with soft dissolves, a whimsical vintage instrumental track, no text on the video (the "pov:" hook goes on the thumbnail and captions). Picks from a 1000-idea bank (74 themes x 7 looks x 8 moments) and keeps a history so no video repeats. Use for "dream life video", "dreamy video", "surreal pastel video", "pov: your job is ...", "video like the moon/cloud/giant animal ones", "whimsical fantasy reel", or "next dream video".
---

# dream-life

Paths are relative to this folder (`.claude/skills/dream-life/`). Server, retries, QA and delivery come from `../muse-video/SKILL.md` (Server, "Format skills" shared steps 3-7). Name everything `dream-<slug>`; the work folder is `~/Movies/museai/dream-<slug>/`.

## What the references do (measured 2026-10-31, 4 reels + a 12-post grid)
| | measured |
|---|---|
| format | 9:16, 25-48 s, 6-10 shots, one shot every 4.3-5 s, soft cuts/dissolves, -14 LUFS, no on-screen text |
| idea | ONE impossible thing per shot, done calmly as an everyday chore: a giraffe hands over the moon, stars sprout in pots, a rainbow dries on a clothesline, a cloud is spun like candy floss, the moon is a pancake. Magic is soft and tactile (fur, cotton, glass), never CGI-flashy |
| story | `day` = one person, one dream job, morning → night (db40 moon/star/rainbow chores, c54a star shop → cloud candy → sunset bubble → moon pancake, 2008 flower-gown garden); `friends` = one person, one motif per shot (289a giant plush fish, snail, cat, giraffe, swan, whale); `postcard` = a living painting of a dream place, no lead (grid: snowy ink town, oil-paint Christmas market, aerial snowy village, Westminster watercolour) |
| frame | centred, symmetric, storybook tidy; subject in the middle third, sky above |
| colour | pastel, low contrast, warm film grain; palettes per look in `looks.json` |
| sound | 289a: muffled, rolled-off highs, steady pulse (vintage 1950s ballad on vinyl); 2008: melodic waltz, music-box/strings lines; no voice |

## Files
- `looks.json`: the 7 looks - `style` (appended to every shot), `palette`, `grade` (ffmpeg, compose), `music` (ACE tags), `cast` (fixed characters, the same person in every shot of a video). Change a look here, never in one video's prompt.
- `prompt/dream.txt`: rules every shot gets (one gentle impossible act, centred frame, slow camera, no text, no music, five-finger hands, no doubled creatures).
- `scripts/themes.py`: 74 themes (42 day jobs, 15 friends motifs, 17 postcard places), each 8-10 beats. `scripts/gen_ideas.py` crosses them with looks and moments into `ideas.json` / `ideas.md` (1000 ideas, deterministic). To grow: append themes (8+ beats, `{who}` = the character) at the END of `THEMES`, rerun.
- `scripts/ideas.py`: pick / check / record against `~/.config/museai/dream-history.json`.

## Steps
1. **Pick**: `python3 scripts/ideas.py next > idea.json` (filters: `--look pastel`, `--format friends`, `--theme moon`, `--moment night`, `--n 5` to offer a choice; `search "cloud"` to browse). `next` skips used ideas and themes from the last 12 videos, and stays in the account's look: Pastel Americana and Lavender Fairytale only (photoreal film, the same young-woman lead; user rule 2026-11-01, `FEED_LOOKS` in `scripts/ideas.py`), alternating between the two. The illustrated looks (ink, nocturne, anime, porcelain) and workshop only when the user asks (`--look ink`, `--look any`). Don't ask the user to accept the idea, the clips, the music or the final (user rule 2026-11-02): pick, render, check against this skill's gates, re-render what fails, and deliver to the Desktop on your own; tell the user the title, look, music and Desktop path afterwards. Ask only when a gate keeps failing after two re-renders. Asked for several videos ("keep generating"): run them one after another in a background subagent, each picked by `next` after the previous one is recorded, so no two pick the same idea. A user's own idea → `check --theme <slug> --look <look> --moment "<moment>"`, write 6 beats in the same shape, record with `record custom`.
2. **Write the shots**: `shots[k]` is the brief of shot k (character + action + moment). Sharpen each for the look: name the one thing that moves, the light, what's behind the subject (pink clapboard house, lily lake, star cabinet). Keep the character text word-for-word in every shot so muse draws the same person. Muse drops a mild impossible detail and renders the real-world version (dl-0002: "kitten-sized bees" → a swarm of normal bees, "glowing honey" → plain amber honey): state the magic loudly and concretely - its size against a known thing ("ONE bee as big as a house cat, only this one in the frame"), its light and what it lights ("glows like a lamp, lighting her face from below"), sparkles rising. Never add a fast camera move.
3. **Render** every shot at once, each in its own background call:
   ```bash
   scripts/shot <look> "<brief of shot 1>" ~/Movies/museai/dream-<slug>/s1.mp4
   ```
   6 s per shot, 9:16. For a stronger character match render shot 1 first and pass its best frame as `IMAGE=s1.png` to the rest.
4. **Music**: every video sounds different (user rule 2026-11-01). `scripts/music` picks a style from its 10 `FLAVOURS` (doo-wop, swing, bossa nova, musette, ukulele, minuet, lullaby, lo-fi, fairytale orchestra, cafe jazz) that none of the last 4 videos used, with a random seed, and writes `m_<flavour>.json` beside the track. Render two different flavours that suit the look (one ACE render at a time, ~5 min each) and keep the one with the clearer moving melody in its spectrogram:
   ```bash
   for f in swing bossa; do scripts/music "$(jq -r .music idea.json)" ~/Movies/museai/dream-<slug>/m_$f.m4a 30 "" $f; done
   ffmpeg -i m_swing.m4a -lavfi "showspectrumpic=s=600x150:legend=0:fscale=log:stop=8000" m_swing.png
   ```
   (`""` = random seed, `auto` = an unused flavour, `look` = the look's own `music` tags.) Record it: `ideas.py record ... --music m_<flavour>.json`.
   Never lift the reference reels' audio (someone else's track → claim/mute). To ride a trending sound, post with the platform's "use audio" instead.
5. **Check each clip**: contact sheet (`ffmpeg -i s1.mp4 -vf "fps=2,scale=180:-1,tile=6x2" -frames:v 1 s1.jpg`) and `python3 ../muse-video/scripts/qa.py s1.mp4 --travel 0 s1sheet.jpg`. Reject: text/logos, a face staring into the lens, warped hands, doubled or melted creatures, a character that changed clothes or hair, the magic object popping in or out, time-lapse sky. Re-render a rejected shot with a sharper brief. Pick each clip's calmest 4.6 s (`clip@start`).
6. **Compose**:
   ```bash
   python3 scripts/compose.py --idea idea.json --music m7.m4a --out dream-<slug>.mp4 s1.mp4 s2.mp4@1.2 ...
   ```
   6 shots x 4.6 s with 0.5 s dissolves (~25 s), look grade + light grain, no text on the video (user rule 2026-11-01: the hook lives on the thumbnail and in the captions; `--text hook` only when the user asks for it on a video), clip ambience at 0.25 under the music, -14 LUFS. Then qa + sheet on the result (shared step 6).
7. **Deliver**: cover with `python3 scripts/cover.py --idea idea.json --at s<k>.mp4@2.0 --hook "<3-6 word hook, *accent word*>" --place top|bottom --out thumbs/dream-<slug>_9x16.jpg --grid grid.jpg`. Pick the frame with the lead's face (or the magic object) big, bright and colourful; `--place` puts the text where it does not cover the face. Look at the cover AND `grid.jpg` (the 3:4 crop the profile grid shows) before delivery: hook readable at grid size, face clear. Captions via `../social-captions` (`captions.py check` must PASS; YouTube ends with `#Shorts`): open with the hook, ask a soft question ("which job would you take?"), then plain keywords people search ("dreamy snowy town", "storybook winter"): Instagram search matches caption words, not cover text. 3-5 hashtags only (Instagram caps posts at 5 since 2025-12), e.g. #dreamcore #pastelaesthetic #surreal #aiart #cottagecore. Then shared step 7 (`FINAL=1 THUMB_DIR=thumbs CAPTIONS_FILE=captions.json ../muse-video/scripts/deliver.sh dream-<slug>.mp4 <work dir> dream-<slug>`, preview first). **Record before `FINAL=1`** (it trashes the work folder):
   ```bash
   python3 scripts/ideas.py record dl-0042 --video ~/Desktop/dream-<slug>.mp4 --shots shots.json --music m_<flavour>.json
   ```

## Growing the account
- The account kit (`references/account-kit.md`): handle, bios, profile art, AI labels, pillars, first 30 days. Dream videos post on an account of their own: the dashboard's **Dream** tab, one slot a day at the US evening (`posting.py` `TIMES["dream"]`, calculated by `scripts/post_time.py`; `--plan <day>` for a new account's first 30 days, `--insights` to use the account's own active hours once it has ~100 followers).
- Series beat one-offs: post 3-5 of one format in a row ("pov: your job is ..." day jobs), then rotate. `next --format day --n 5` plans a week.
- One style for the whole account: every video photoreal film, Pastel Americana or Lavender Fairytale, the same lead where the idea allows. A switch to an illustrated look reads as a different account.
- The hook is a pov or a wish ("pov: your job is picking the moon"), never a title card; it goes on the thumbnail and opens every caption, never on the video; the first shot is the most surprising beat (move it first in step 2 if needed).
- Cover rules (Instagram 2026, see `scripts/cover.py`): the profile grid crops every Reel cover to 3:4 (240 px off top and bottom), so text stays in y 300-1620; one hook of 3-6 big rounded words, one accent word in the look's colour (`accent` in `looks.json`), a "dream life no. N" pill that numbers the series so a visitor binges the grid, the same template on every post. The cover sells the profile visit; the Reels feed shows the first frame, so shot 1 must stop the scroll on its own (no text on the video).
- Reach signals Mosseri confirmed: watch time (completion, rewatch: keep ~25 s, loop-friendly fade), sends per reach (DM shares: end on a beat people send to a friend; ask "send this to who'd live here"), likes per reach. Originality counts: never repost watermarked clips. Turn on Instagram's AI label (muse renders are AI).
