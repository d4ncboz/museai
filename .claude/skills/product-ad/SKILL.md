---
name: product-ad
description: Make a short vertical marketing / advertising video (TikTok, Reels, Shorts, Facebook ads) that sells a real product from the seller's own photos - a scroll-stopping hook in the first 1.5 s, beat-cut product shots, muse-animated "hero" shots (light sweeping across the real product, slow push-in), big on-beat text cards in the buyer's language, a desire build (variety, personalisation, gift angle), a clear call to action, and a loop back to the first frame so viewers rewatch. Use for "marketing video", "ad video", "quảng cáo", "video bán hàng", "product video", "promo reel", "make people want to buy this", or any request to advertise a product from photos. Never for places (use scenic-drop-reel or zoominview). Takes the shared brief (muse-video "Format skills", subject = the product); files are named ad-<slug>.
---

# product-ad

Paths are relative to this folder (`.claude/skills/product-ad/`). Server, retries, the brief and delivery come from `../muse-video/SKILL.md` ("Format skills"); music from `../muse-video/scripts/music.py` ("Music": ACE ignores the BPM, so plan in seconds). Name everything `ad-<slug>`.

## Rule 1: the product on screen is the real product
Buyers get what the photos show. Every frame showing the product comes from the seller's photo (ffmpeg motion) or a muse image-to-video of that photo whose product still matches it (same parts, colours, letters/logo). Never let muse invent the product from text, never show a hand or person holding a product muse redrew. Keep the seller's watermark.

## The format (18-22 s, 9:16, cuts on the beat)
| beats | part | job | how |
|---|---|---|---|
| seconds | part | job | how |
|---|---|---|---|
| 0-2 | **HOOK** | stop the scroll in < 2 s | 4 flash cuts (~0.5 s) of the most colourful variants, each punching in 1.3 → 1.0; a hook line on screen from frame 1 |
| 2-7 | **HERO** | make them want it | muse hero shots (2-3 s each): light glints over the product, slow push-in, close detail (name, engraving, texture) |
| 7-13 | **VARIETY** | "there's one for me" | ~6 cuts of ~1 s, every colour / variant, alternating zoom direction, "Choose your colour" |
| 13-17 | **ANGLE 2** | second reason to buy | ~2 s each: related product, gift use, bundle, how it's made |
| 17-21 | **CTA** | tell them what to do | the hook's first product again, 3-4 s, zoom out → into the hook framing (seamless loop), CTA + shop handle |

Pacing: only the hook flashes. Every later shot stays ≥ 0.85 s (`compose.py` enforces it), ~1 s for variety, 2-3 s for hero/CTA: the viewer must be able to read the product and the text. Plan in seconds (`sec`), compose snaps to the track's real beats.

Hook lines that work (pick one per ad, in the buyers' language): the missing thing ("Your phone is missing this"), POV ("POV: your name, bead by bead"), curiosity ("Guess whose name this is"), price shock ("Only 49k for your own name"), objection ("Not another boring phone strap"). Text on screen from the very first frame: many watch muted.

Retention rules: something new every ~1 s (cut, text, or zoom direction change); no shot longer than ~3 s; text ≤ 6 words per card, ≤ 2 cards at once; end on a frame that matches the first frame so the loop is invisible (watch time counts rewatches).

Safe zone (TikTok / Reels / Shorts UI): text between y=280 and y=1500, x < 940. Never cover the product's letters / logo with text.

## Steps
1. **Read the photos**: list each photo, its product, colour, variant, personalised text, and where the product sits (crop centre `cx` for a vertical 9:16 strip; wide products such as bracelets use `"mode": "fit"`). Note anything the seller's text must not claim (price, material) unless the user gave it.
2. **Music** (background, ~3-5 min):
   ```bash
   uv run --no-project ../muse-video/scripts/music.py \
     --style "catchy cute K-pop bubblegum pop, bright ukulele strum, whistle melody hook, handclaps, finger snaps, bouncy bass, sweet female vocals, earworm chorus, TikTok viral song" \
     --lyrics "[chorus] la la la, your name on a string ..." --bpm 118 --intro-beats 0 --body-beats 40 --out WORK/track.m4a
   ```
   Catchy = a sung hook: a short "la la la" / "oh oh" chorus about the product, a whistle or ukulele melody, claps. An instrumental bed of plucks sounded generic (snowfeng v1). No riser intro: the hook needs energy on second 0. Match the product: cute/handmade → bubblegum pop, ukulele, whistle; beauty → soft R&B vocals; tech → punchy electronic with a vocal chop; luxury → slow piano + strings. Listen before composing; a weak chorus → re-render with another `--seed`.
3. **Hero shots** (one line each in `jobs.txt`, run by `../muse-video/scripts/render-queue` in one background call, one at a time; never one background call each):
   ```bash
   scripts/hero WORK/photos/4.jpg WORK/hero ad-<slug>-hero-blue 0.52 5
   ```
   Crops a sharp 1080x1920 first frame around `cx` and asks muse for light + push-in only (`prompt/product.txt`). Contact sheet each (`ffmpeg -i x.mp4 -vf "fps=1.2,scale=270:-1,tile=6x1" -frames:v 1 x.jpg`): keep only the seconds where the product still matches the photo (every letter readable and right). Drop a clip that came back below 1080p.
4. **Plan** `WORK/ad.json` (format in `scripts/compose.py` docstring): shots in seconds (`sec`), texts by shot index (`shot`/`to`/`delay`). Hero mp4 shots get `"zoom": [1.0, 1.0]` and `"ss"` to skip into the good part.
5. **Compose**: `uv run --no-project --python 3.12 --with pillow python scripts/compose.py WORK/ad.json WORK/ad.mp4` (~90 s). Reads the BPM from `track.beats.json`.
6. **Check**: `ffmpeg -i ad.mp4 -vf "fps=1,scale=216:-1,tile=10x2" -frames:v 1 sheet.jpg`: every text renders (no ☐ boxes: font missing glyphs), sits in the safe zone, never on the product's letters; cuts land on the beat; last frame ≈ first frame. Then `python3 ../muse-video/scripts/qa.py ad.mp4 --travel 0 sheet.jpg` for format and loudness (its smooth/motion checks flag the planned cuts: ignore those).
7. **Deliver**: make the thumbnails first (`../thumbnail/SKILL.md` style `chinese`, `--at` the hero product shot, `--title` the offer). Show the preview from the work folder; after the user accepts, `CAPTION_FILE=caption.txt THUMB_DIR=WORK/thumbs FINAL=1 ../muse-video/scripts/deliver.sh ad.mp4 WORK ad-<slug>`. Caption: hook line, one line of what they get (personalised, handmade, colours), how to order, 3-6 hashtags (in the buyers' language, e.g. `#charmdienthoai #quatang #handmade #vongtaykhacten`).

## Lessons
- Avenir Next Heavy (ttc index 8) has no Vietnamese glyphs; Bold (0) / DemiBold (2) do (snowfeng, 2026-10-29). Check the sheet for ☐ boxes after any font change.
- muse image-to-video of a bead strap (snowfeng, 2026-10-29): the light sweep and glints looked great and the letters held, but the "slow" push-in reached ~2.5x by 5 s and cropped the name off. Use the first ~3 s. One of three renders came back 704x1248: drop it, don't upscale.
- ACE-Step ignores `--bpm`: asked 100, played 131 (snowfeng, 2026-10-29). The v1 plan in beats made every 1-beat cut 0.46 s and the user called the transitions too fast. Plan in seconds; compose snaps to the measured tempo and holds showcase shots ≥ 0.85 s.

## Maintaining this skill
Record proven lessons here (hooks that held, prompt wording that kept the product faithful, fonts, pacing), following `../muse-video/SKILL.md` "Maintaining this skill". Put new rules in `compose.py` / `prompt/product.txt`, not only in one ad's plan.
