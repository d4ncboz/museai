---
name: thumbnail
description: Make the thumbnails for a finished museai video - one 9:16 cover (YouTube Shorts, TikTok, Facebook / Instagram Reels), plus a 16:9 thumbnail (YouTube video, Facebook feed) only for a horizontal video, from the video's best frame, in a style per kind of video (chinese: faces + red-box title; travel: stakes/scale frame, red-ringed subject, shock hook + big place name), with a big readable hook title placed clear of faces and the platform UI - and hand them to deliver.sh, which puts them next to the video on the Desktop and the dashboard. Use after every video (muse-video, EVERYDAY CHINESE, scenic-drop-reel, zoominview, product-ad, teaching-video) before the final delivery, and for "thumbnail", "cover", "ảnh bìa", "ảnh thumbnail", "make a cover for this video".
---

# thumbnail

Every video posted from museai gets thumbnails (user rule, 2026-10-29). `deliver.sh` refuses a final
without `THUMB_DIR=` (or `NO_THUMB=1` for a video that will not be posted).

## Which sizes (researched 2026-10)

| Where | Shape | Size we make | Notes |
|---|---|---|---|
| YouTube Shorts | 9:16 | 1080x1920 | custom Shorts thumbnail: upload in YouTube Studio on a computer (verified channel); 9:16 recommended, min 640 high |
| YouTube video | 16:9 | 1920x1080 | JPG/PNG; Google recommends large (3840x2160 max), 2 MB limit from mobile, 50 MB desktop; a 16:9 thumbnail on a vertical video is replaced |
| TikTok | 9:16 | 1080x1920 | cover = a frame or an uploaded image; the profile grid crops the centre to 3:4 |
| Facebook / Instagram Reels | 9:16 | 1080x1920 | custom cover upload; grid and feed crop the centre to 3:4 / 4:5 / 1:1 |
| Facebook feed video | 16:9 | 1920x1080 | |

A vertical video needs only `<name>_9x16.jpg`: every place it is posted takes a 9:16 cover, and a 16:9
thumbnail on a vertical video is replaced anyway (user rule, 2026-10-30: no 16:9 for a 9:16 video). A
horizontal video (teaching-video `--format 16x9`) also gets `<name>_16x9.jpg` (`--wide`): one 9:16 image
cannot serve YouTube long-form. Both stay under 2 MB.

**9:16 safe box**: all text inside x80-960 / y300-1560. That survives the centre crops to 3:4 (y240-1680),
4:5 (y285-1635) and 1:1 (y420-1500, keep the title low in the box), the right-hand button column
and the bottom 20 % (caption, username) on TikTok / Reels / Shorts. The 16:9 layout leaves the
bottom-right corner free of text (YouTube's duration badge).

**Alignment**: every line is centred, the series badge too (top of the safe box on 9:16, above the
text column on 16:9). On 9:16 the block is centred on the frame's centre line (x120-960,
symmetric, still clear of the button column); on 16:9 it is centred in the text column beside the faces
(centring on the whole frame would cover them).

## What makes it get clicked
- A real face with a clear emotion (smile, surprise) and eye contact; big enough to read at phone size.
- 2-5 words of title, huge, high contrast; it adds to the video title instead of repeating it.
- One focal point, bright saturated colour, no clutter; the same layout every episode so a series is recognisable.
- Never misleading: the picture is a real frame from the video.

### Travel: make it a shock, not a postcard (user rule, 2026-10-29)
A pretty landscape scrolls past; a cover that makes the viewer gasp or doubt gets the tap.
- **Frame**: pick the moment with stakes or scale, not the widest calm shot: a person on the edge,
  a tiny boat under a giant waterfall, a road clinging to a cliff, the drop below a ledge. A human or
  boat in frame beats empty scenery (scale = shock). Use the picks sheet / a contact sheet, then `--at`.
- **Point at it**: `--circle x,y[,r]` puts a red ring + arrow on that person/boat/edge, so the eye lands
  there first. `--zoom 1.2-1.4 --focus x,y` crops in so the subject is big and the empty sky is gone
  (coordinates are fractions of the frame; `--circle` is measured after the zoom). Keep the subject below
  the text (y > 0.5) and above the bottom UI (y < 0.85).
- **Hook** (huge yellow on a tilted solid black plate, 2-5 words + one emoji 😱 😳 🤯; shorter = bigger letters): the loudest thing on the cover, read
  in half a second at phone size; a fact that sounds unreal, not a mood or a label. Patterns:
  danger/stakes ("604 m drop. No rails"), scale ("That boat is tiny"), a number ("One step from 700 m",
  "250 m free fall"), disbelief ("Is this even real?"), secret ("Locals hide this beach"). True for the
  frame shown and for the place - check the number. Never "beautiful", "amazing", "stunning", "paradise",
  "Welcome to …", "This is <country>": the script refuses those and a hook without an emoji (user, 2026-10-31:
  Shangri-La's "THIS IS CHINA" over a back view was "not special"; "60 tons. It spins?! 🤯" over the giant
  prayer wheel with tiny people below was the fix; outlined text alone got lost on busy prayer flags, the
  solid plate fixed it and "Not Tibet?! 😳" over the flag spiral was the pick).
- **People**: never text on a person. The style finds people (back views too) and moves the text to the
  centre when the top is taken (never the bottom: platform UI); a "text covers a person" warning means pick another frame.
- **Title**: the place name only, huge; the hook carries the emotion. The sub is the country + flag.
- **Reaction covers** (`--split`, zoominview): the most shocked face of the video - mouth open, eyes wide,
  hands on head (as Madeira) - not a calm profile; put the shock line in `--sub`.
- **Colour**: bright and natural, never dark or crushed - a dim, heavy cover tires the eye (user, 2026-10-29).
  The style lifts dark frames itself; still prefer a well-lit frame over a moody one.
- Look at the 9:16 at phone size (360 px wide) before delivering: hook readable, ring on the subject,
  subject not under the text.

## Styles
One script, one style per kind of video. Each style is a file in `scripts/styles/`; the shared toolkit
(frame grab, face and scenery scoring, grade, safe box, red-box title block, badge, flag emoji, picks
sheet, 2 MB JPEG writer) is `scripts/core.py`.

| Style | For | Look |
|---|---|---|
| `chinese` | EVERYDAY CHINESE, teaching-video, product-ad, any video with people talking | best face frame, yellow hanzi hook, title white on a red box, sub line, episode badge |
| `travel` | scenic-drop-reel, muse-video travel mode; `--split` for zoominview | stakes/scale frame full bleed, bright natural grade (dark frames lifted), optional zoom and red ring + arrow on the subject, huge yellow hook on a black plate (labels refused), Futura place name, text kept off people, sub with flag |

## Rules every style keeps
What makes a cover get tapped (YouTube / TikTok creator guidance, high-CTR channels): one sharp,
expressive face or one clear subject, big; 3-5 words of high-contrast text; nothing busy; readable at
phone-grid size. What makes it look cheap, and the scripts never do:
- **No blur, no ghost copies, no panels on 9:16.** A frame of the other aspect is cropped (travel) or set
  beside a solid panel (`chinese` 16:9). The 9:16 cover is always the full frame: the owner rejected
  both a black and a blurred text panel under the picture.
- **No text on a face.** Text sits in the free band above the heads or under the chins, at least 60 px
  from every face box, shrunk (to 55 %) before it may touch one; when no band holds it, the picture goes
  at 55 % under the chins (9:16), or on the left panel (16:9).
- **No dark wash over people.** Contrast comes from the red box, the outline and the drop shadow on the
  text, not from darkening the picture under it.
- Every face of the frame stays inside the 16:9 window; the window widens rather than crop a person.

## Make them
```
uv run --no-project --python 3.12 --with mediapipe==0.10.14 --with opencv-python-headless==4.10.0.84 \
    --with pillow==11.0.0 --with fonttools python scripts/thumb.py STYLE OUT_DIR VIDEO [VIDEO ...] [options]
```
Writes `<name>_9x16.jpg` (with `--wide`, for a horizontal video, also `<name>_16x9.jpg`) and, when the style picked the frame itself, `<name>_picks.jpg`
(the 6 best frames with their times and scores). `--name` sets the prefix (default: the first video's name).
Prints `THUMB <file> <KB>`. Look at the images (and `_picks.jpg`) before delivering: face not covered,
text readable, frame not mid-blink or mid-transition. Re-run with `--at` from the picks sheet if needed.
`scripts/thumb.py STYLE -h` lists a style's options.

**chinese** (one video):
- `--title` (required): 2-5 words in the viewer's language, uppercase, white on a red box.
- `--zh`: the big hook phrase in the taught language (yellow, above the title), e.g. the ending question.
- `--sub`: one small line under the title (a question or promise).
- `--badge`: series tag, centred at the top, e.g. `TẬP 33`.
- `--at T`: use this frame; without it, frames sampled at 4 fps are scored (all faces, eyes open, not
  mid-word, smiling, toward the lens, sharp).
- `--skip 17.2-20.2,...`: never pick these spans (vocab cards, cuts, text cards).
- `--cut 0.6`: the video has burned-in captions from 60 % of the height down; the 9:16 then has the
  captions painted out of the frame (inpaint of outlined letters; a white apron stays) and the text
  goes over where they were, full bleed. Better: run on the cut **before** captions are
  burned in, then no `--cut` and the picture stays full bleed.

**travel** (the raw shots in plan order, not the reel: its intro text, dips and transitions would be picked):
- `--title` (required): the place name; uppercase Futura, two balanced lines when it is long.
- `--hook`: 2-5 words + one emoji, huge yellow on a black plate above the title, the shock line (see "Travel: make it a shock").
- `--sub`: line under it, may end in a flag emoji ("Norway 🇳🇴").
- `--zoom 1.3 --focus 0.45,0.4`: crop into the frame around x,y (fractions) so the subject is big.
- `--circle 0.4,0.56,0.07`: red ring (radius as a fraction of the short side, default 0.12) + arrow on the
  subject, coordinates in the zoomed frame.
- `--at shot.mp4@2.5` (or seconds in the first video): use this frame. Without it the most vivid, sharp,
  still frame of all shots wins, 0.5 s clear of each shot's ends; the first shot (the hook) gets a bonus.
- A shot of the other aspect is cropped round the subject (the `--circle`, else the middle), full bleed
  and sharp: 9:16 shot on 16:9, 16:9 shot on 9:16.
- `--split [--view T]` (one video with a person): reaction on top, the view below, the title on the seam
  (white on red, as `chinese`); the view is the best frame without faces unless `--view` names one.

Per kind of video:
- **EVERYDAY CHINESE**: `chinese --zh "<ending question or key phrase>" --title "<topic in Vietnamese, uppercase>"
  --sub "Nói sao bằng tiếng Trung?" --badge "TẬP NN"`, skip the vocab-card span; frame of both people
  smiling at each other or at the lens.
- **teaching-video**: `chinese` on each format's video; `--zh` the pattern, `--title` the lesson in Vietnamese.
- **product-ad**: `chinese --at` the hero product shot, `--title` the offer (3-4 words).
- **scenic-drop-reel / muse-video travel**: `travel OUT s1.mp4 s2.mp4 ... --title "<PLACE>" --hook "<shock fact> 😱"
  --sub "<Country> <flag>" --at <stakes frame> --circle <subject>` (e.g. Trolltunga: `--hook "One step from 700 m 😱"
  --zoom 1.3 --focus 0.45,0.4 --circle 0.40,0.56,0.07` on the frame with the hiker on the tongue).
- **zoominview**: `travel OUT reel.mp4 --split --title "<PLACE>" --sub "<wow line in the caption language>"`.

## Add a style
1. Copy the closest `scripts/styles/*.py` to `scripts/styles/<name>.py`; its docstring's first line is the
   `-h` help.
2. `add_args(p)`: its options (`out_dir`, `videos` and `--name` are already there).
3. `make(args)` returns `(9x16 image, 16x9 image, picks sheet or None, info line)`: 1080x1920 and
   1920x1080 RGB images; `thumb.py` saves them under the usual names, so `deliver.sh` and the dashboard
   need nothing new.
4. Build on `core.py` (frame pick, grade, `cover`, `picks_sheet`, `emoji`); keep text inside `SAFE`
   on 9:16 and out of the bottom-right corner on 16:9. A helper two styles need goes into `core.py`.
5. Add it to the table above and to "Per kind of video", and point the video skill at it.

## Deliver
Write them into the work folder (e.g. `WORK/thumbs`), then pass `THUMB_DIR=WORK/thumbs` to
`../muse-video/scripts/deliver.sh`. It copies them next to the video as
`<video name> - thumbnail 9x16.jpg` (and `16x9.jpg` when the video is horizontal) before it trashes the work folder; the dashboard's
"Ready to post" card shows both (click to view, drag into the upload page) and trashes them with
the video once it is posted everywhere.
