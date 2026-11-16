"""chinese: people on camera (EVERYDAY CHINESE, teaching-video, product-ad with a presenter).

The best face frame (open eyes, not mid-word, smiling, sharp, toward the lens; every face of the video
in frame), the hook phrase in yellow hanzi, the title white on a red box, a sub line and an episode
badge. No faces at all: the most vivid, sharp frame.
"""
import sys

from core import (
    CENTRE,
    SAFE,
    YELLOW,
    badge,
    block,
    block_fit,
    face_mesh,
    faces,
    grab,
    grade,
    horizontal,
    pick,
    picks_sheet,
    to_pil,
)
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


def add_args(p):
    p.add_argument("--title", required=True, help="2-5 words, the viewer's language, uppercase reads best")
    p.add_argument("--zh", default="", help="the big hook phrase in the taught language (optional)")
    p.add_argument("--sub", default="", help="small line under the title (pinyin, a question)")
    p.add_argument("--badge", default="", help='e.g. "TẬP 33"')
    p.add_argument("--at", type=float, help="frame time in seconds (skips the automatic pick)")
    p.add_argument("--skip", default="", help="time ranges to never pick, e.g. 17.2-20.2,30-31")
    p.add_argument("--cut", type=float, default=0,
                   help="burned-in captions start at this fraction of the height (e.g. 0.6): never shown")


def vertical(frame, boxes, args):
    """Full bleed with the text in the free band above the heads or under the chins; when neither holds
    it (or burned-in captions are cut off), the picture on top and the text below it on the same frame,
    blurred and dimmed: the scene's colours carry on and the burned-in captions are unreadable.
    No text within 60 px of a face."""
    im = grade(frame.resize((1080, 1920), Image.LANCZOS))
    s = frame.width / 1080
    face_top = min(b[1] / s for b in boxes) if boxes else 600
    face_bottom = max(b[3] / s for b in boxes) if boxes else 1000
    w = CENTRE[1] - CENTRE[0]
    top = SAFE[1] + 110  # under the badge
    if not args.cut:
        bands = [(SAFE[3] - (face_bottom + 60), "below"), (face_top - 60 - top, "above")]
        for room, where in sorted(bands, reverse=True):
            blk = block_fit(args, w, room)
            if blk:
                y = SAFE[3] - blk.height if where == "below" else top
                im.paste(blk, (CENTRE[0], int(y)), blk)
                badge(im, args.badge, 540, SAFE[1] - 20)
                return im
    # panel: a window of the picture round the faces (above the burned-in captions), the text below it
    floor = int(args.cut * 1920) if args.cut else 1920
    blk = block_fit(args, w, SAFE[3] - 1000) or block(args, w, 0.55)
    c = SAFE[3] - 60 - blk.height  # picture height
    y0 = int(min(max(face_bottom + 200 - c, 0), floor - c))
    pic = im.crop((0, y0, 1080, y0 + c))
    out = backdrop(im)
    out.paste(pic, (0, 0))
    ImageDraw.Draw(out).rectangle((0, c, 1080, c + 12), fill=YELLOW)
    y = min(c + 12 + (1920 - c - 12 - blk.height) // 2, SAFE[3] - blk.height)  # mid-panel, clear of the feed UI
    out.paste(blk, (CENTRE[0], y), blk)
    badge(out, args.badge, 540, SAFE[1] - 20)
    return out


def backdrop(im):
    """The whole frame, blurred past reading any caption and dimmed so the white and yellow text pops."""
    bg = im.resize((270, 480), Image.LANCZOS).filter(ImageFilter.GaussianBlur(12))
    bg = bg.resize((1080, 1920), Image.LANCZOS).filter(ImageFilter.GaussianBlur(8))
    bg = ImageEnhance.Color(bg).enhance(1.25)
    return ImageEnhance.Brightness(bg).enhance(0.62)


def make(args):
    if len(args.videos) > 1:
        sys.exit("chinese takes one video")
    video = args.videos[0]
    skip = [tuple(float(v) for v in r.split("-")) for r in args.skip.split(",") if r]
    mesh = face_mesh()
    sheet = None
    if args.at is None:
        picks, _ = pick(video, skip, mesh)
        sheet = picks_sheet([(grab(video, t), f"{t:.2f}s  {sc:.2f}") for sc, t in picks])
        t = picks[0][1]
    else:
        t = args.at
    img = grab(video, t)
    boxes = [f["box"] for f in faces(img, mesh)]
    frame = to_pil(img)
    return vertical(frame, boxes, args), horizontal(frame, boxes, args), sheet, f"frame {t:.2f}s, {len(boxes)} face(s)"
