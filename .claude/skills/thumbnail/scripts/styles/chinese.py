"""chinese: people on camera (EVERYDAY CHINESE, teaching-video, product-ad with a presenter).

The best face frame (open eyes, not mid-word, smiling, sharp, toward the lens; every face of the video
in frame), the hook phrase in yellow hanzi, the title white on a red box, a sub line and an episode
badge. No faces at all: the most vivid, sharp frame.
"""
import sys

import cv2
import numpy as np
from core import (
    CENTRE,
    SAFE,
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
from PIL import Image


def add_args(p):
    p.add_argument("--title", required=True, help="2-5 words, the viewer's language, uppercase reads best")
    p.add_argument("--zh", default="", help="the big hook phrase in the taught language (optional)")
    p.add_argument("--sub", default="", help="small line under the title (pinyin, a question)")
    p.add_argument("--badge", default="", help='e.g. "TẬP 33"')
    p.add_argument("--at", type=float, help="frame time in seconds (skips the automatic pick)")
    p.add_argument("--skip", default="", help="time ranges to never pick, e.g. 17.2-20.2,30-31")
    p.add_argument("--cut", type=float, default=0,
                   help="burned-in captions start at this fraction of the height (e.g. 0.6): never shown")


def erase_captions(frame, cut):
    """Paint the burned-in captions (bright or coloured letters with a dark outline, from ``cut`` of the
    height down to 85 %) out of the frame from the pixels around them. A white apron or a sky has no
    dark outline, so it stays."""
    img = cv2.cvtColor(np.array(frame), cv2.COLOR_RGB2BGR)
    h = img.shape[0]
    y0, y1 = int(cut * h) - 10, int(0.85 * h)
    band = img[y0:y1]
    hsv = cv2.cvtColor(band, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(band, cv2.COLOR_BGR2GRAY)
    letters = ((gray > 175) | ((hsv[..., 1] > 120) & (hsv[..., 2] > 170))).astype(np.uint8)
    outline = cv2.dilate((gray < 60).astype(np.uint8), np.ones((5, 5), np.uint8))
    mask = cv2.dilate(letters & outline, np.ones((15, 15), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    img[y0:y1] = cv2.inpaint(band, mask * 255, 9, cv2.INPAINT_TELEA)
    return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))


def vertical(frame, boxes, args):
    """Full bleed, the text in the free band above the heads or under the chins. Burned-in captions
    (``--cut``) are painted out first and the text goes over where they were. No panel, no blur, no
    dark wash; no text within 60 px of a face."""
    if args.cut:
        frame = erase_captions(frame, args.cut)
    im = grade(frame.resize((1080, 1920), Image.LANCZOS))
    s = frame.width / 1080
    face_top = min(b[1] / s for b in boxes) if boxes else 600
    face_bottom = max(b[3] / s for b in boxes) if boxes else 1000
    w = CENTRE[1] - CENTRE[0]
    top = SAFE[1] + 110  # under the badge
    low = max(face_bottom + 60, args.cut * 1920 - 80) if args.cut else face_bottom + 60
    bands = [(SAFE[3] - low, "below"), (face_top - 60 - top, "above")]
    if args.cut:
        bands = bands[:1]  # the text covers where the captions were
    for room, where in sorted(bands, reverse=True):
        blk = block_fit(args, w, room)
        if blk:
            y = low + (room - blk.height) // 2 if where == "below" else top
            im.paste(blk, (CENTRE[0], int(y)), blk)
            break
    else:
        blk = block(args, w, 0.55)
        im.paste(blk, (CENTRE[0], SAFE[3] - blk.height), blk)
    badge(im, args.badge, 540, SAFE[1] - 20)
    return im


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
