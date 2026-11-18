"""Usage: ease_seams.py out_dir clip1.mp4 clip2.mp4 [...]   (EASE=1.5 seconds)
  uv run --no-project --python 3.12 --with opencv-python-headless==4.10.0.84 \\
      python scripts/ease_seams.py eased a.mp4 b.mp4 c.mp4
then  scripts/stitch.sh out.mp4 eased/a.mp4 eased/b.mp4 eased/c.mp4

Smooths the seam jump that makes a multi-clip muse video look generated, without blending
mouths: a CONTINUE_FROM clip starts zoomed/shifted against the previous clip's last frame
(EP09 v7: 3.7-4.2 % zoom, ~10 px; YDIF 17 at the seam vs ~0.6 per frame; eased: diff 20 -> 2-3).
Each seam is measured (ECC affine between the two frames) and spread over EASE seconds as a
slow camera move: when the next clip is tighter, the end of the previous clip pushes in to
its framing; when it is wider, the next clip starts at the old framing and eases out.
So the warp always samples inside the picture. No frame is added,
dropped or retimed and the audio is copied, so lip sync holds. XFADE in stitch.sh hides a
seam only over silence; this works over speech too. Clips are written to out_dir under the
same names, ready for stitch.sh (which drops each next clip's duplicate first frame).
Run jumps.py on the stitched file afterwards: it must say RESULT ok. A jump left inside a
clip is muse snapping pose and face between two frames, not a reframe (EP09 v7 clip B: the
diff stayed 7-10 after aligning the frames), so no warp hides it: re-render that clip."""

import os
import subprocess
import sys

import cv2
import numpy as np

EASE = float(os.environ.get("EASE", "1.5"))
RESIDUAL_MAX = float(os.environ.get("RESIDUAL_MAX", "3.5"))


def frames(path, size=None):
    """size (w, h): scale every frame to it; muse returned EP24 clip C at 704x1248 in a 1080x1920 chain."""
    cap = cv2.VideoCapture(path)
    out = []
    while True:
        ok, f = cap.read()
        if not ok:
            return out
        if size and (f.shape[1], f.shape[0]) != size:
            f = cv2.resize(f, size, interpolation=cv2.INTER_LANCZOS4)
        out.append(f)


def jump_warp(a, b):
    """3x3 W with b(W x) ~ a(x), estimated at 1/4 size."""
    s = 0.25
    ga, gb = (
        cv2.GaussianBlur(
            cv2.resize(cv2.cvtColor(f, cv2.COLOR_BGR2GRAY), None, fx=s, fy=s), (5, 5), 0
        ).astype(np.float32)
        for f in (a, b)
    )
    w = np.eye(2, 3, dtype=np.float32)
    _, w = cv2.findTransformECC(
        ga,
        gb,
        w,
        cv2.MOTION_AFFINE,
        (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-6),
        None,
        5,
    )
    w[:, 2] /= s
    return np.vstack([w.astype(np.float64), [0, 0, 1]])


def warp(f, m):
    """f sampled at m x (output pixel x reads source pixel m x)."""
    return cv2.warpAffine(
        f,
        m[:2],
        (f.shape[1], f.shape[0]),
        flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        borderMode=cv2.BORDER_REPLICATE,
    )


def smooth(x):
    return x * x * (3 - 2 * x)


def diff(a, b):
    return float(np.abs(a.astype(np.int16) - b.astype(np.int16)).mean())


out_dir, clips = sys.argv[1], sys.argv[2:]
os.makedirs(out_dir, exist_ok=True)
fps = cv2.VideoCapture(clips[0]).get(cv2.CAP_PROP_FPS)
n = max(2, round(EASE * fps))
first = cv2.VideoCapture(clips[0])
size = (int(first.get(cv2.CAP_PROP_FRAME_WIDTH)), int(first.get(cv2.CAP_PROP_FRAME_HEIGHT)))
data = [frames(c, size) for c in clips]
ident = np.eye(3)
plan = [{} for _ in clips]  # clip -> {frame index: 3x3 sampling matrix}

# seams: (clip of the frames before, index of the last frame before, clip of the frame after, its index)
events = [(i - 1, len(data[i - 1]) - 1, i, 1, "seam") for i in range(1, len(clips))]

for cb, kb, ca, ka, what in events:
    before, after = data[cb][kb], data[ca][ka]
    w = jump_warp(before, after)
    zoom = float(np.sqrt(abs(np.linalg.det(w[:2, :2]))))
    if zoom >= 1:  # tighter after the jump: push the frames before it in to that framing
        target = np.linalg.inv(w)
        m = min(n, kb + 1)
        for j in range(m):
            idx = kb - m + 1 + j
            step = ident + smooth((j + 1) / m) * (target - ident)
            plan[cb][idx] = plan[cb].get(idx, ident) @ step
        fixed = diff(warp(before, target), after)
    else:  # wider after the jump: start at the old framing and ease out
        m = min(n, len(data[ca]) - ka)
        for j in range(m):
            idx = ka + j
            step = ident + smooth(1 - j / m) * (w - ident)
            plan[ca][idx] = plan[ca].get(idx, ident) @ step
        if ka == 1:  # duplicate first frame of a continued clip, dropped by stitch.sh
            plan[ca][0] = plan[ca].get(0, ident) @ w
        fixed = diff(before, warp(after, w))
    print(
        f"{os.path.basename(clips[ca])} {what}: zoom {zoom:.3f} shift {w[0, 2]:+.0f},{w[1, 2]:+.0f}px  "
        f"diff {diff(before, after):.1f} -> {fixed:.1f}"
    )
    if (
        fixed > RESIDUAL_MAX
    ):  # EP44 A->B: 4.7 left after easing, the pose itself changed at the seam
        print(
            f"  RESIDUAL {fixed:.1f}: pose differs, not only framing. Trim both sides to ~0.4 s after/before "
            f"speech and join this seam with XFADE=0.12 XFADE_AT={ca} in stitch.sh"
        )

for clip, fr, p in zip(clips, data, plan, strict=True):
    h, w_ = fr[0].shape[:2]
    out = os.path.join(out_dir, os.path.basename(clip))
    enc = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{w_}x{h}",
            "-r",
            f"{fps}",
            "-i",
            "-",
            "-i",
            clip,
            "-map",
            "0:v",
            "-map",
            "1:a?",
            "-c:v",
            "libx264",
            "-crf",
            "16",
            "-preset",
            "slow",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            out,
        ],
        stdin=subprocess.PIPE,
    )
    for k, f in enumerate(fr):
        enc.stdin.write((warp(f, p[k]) if k in p else f).tobytes())
    enc.stdin.close()
    enc.wait()
    print("WROTE", out, f"({len(p)} frames eased)")
