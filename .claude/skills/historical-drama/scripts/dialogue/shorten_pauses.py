"""Usage: shorten_pauses.py video.mp4 out.mp4 [max_gap=1.0] [keep=0.45]
Shortens every pause longer than max_gap s to about keep s by cutting inside the silence and
joining the two sides with a 0.2 s xfade + acrossfade. Nothing is retimed, so lip sync stays.
EP08: four 1-2 s pauses between lines, shortened this way; on a locked camera the dissolves
were invisible and no syllable moved. Run it on the stitched video, before dub.py and cues
(it changes every time after the first cut). Speech spans come from gaps.py (audio energy).
KEEP=12.5-17.0 (comma-separated a-b spans, seconds of the input): pauses inside are left alone, e.g. the
review pauses of a vocabulary recap (EP30: those pauses are wanted, see REVIEW= in pace.py).
SPANS_FROM=voc.mp4: read speech spans from another file of the same timeline, e.g. the demucs vocal stem
(EP29: muse's music filled every pause, gaps.py on the mix found none to cut).
Where to cut inside a pause: the person keeps moving while silent (a head turn, a breath, a lean), and a
dissolve between two different poses reads as the view jumping (EP36 ghost face; user, EP44: "sometime
transition is not smooth enough, make the view jump"). So each cut is placed at the frame pair inside the
silence that looks most alike (small grey thumbnails, mean abs diff), letting the kept pause vary by
+-0.15 s. It prints that diff per cut; `SHIFT` (diff > SHIFT_MAX, default 2.5) means no still pair
exists in that pause: KEEP= it, or cut it by hand where she is still, and check jumps.py.
MATCH=0 restores the old middle-of-pause cut."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gaps import speech_spans  # noqa: E402

video, out = sys.argv[1], sys.argv[2]
max_gap = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
keep = float(sys.argv[4]) if len(sys.argv) > 4 else 0.45
FADE = 0.2
SHIFT_MAX = float(os.environ.get("SHIFT_MAX", "2.5"))
SLACK = 0.15  # the kept pause may differ from keep by this much to find a still frame pair
KEEP = [tuple(map(float, x.split("-"))) for x in os.environ.get("KEEP", "").split(",") if x]

dur = float(
    subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
)
fps = subprocess.run(
    [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=r_frame_rate",
        "-of",
        "csv=p=0",
        video,
    ],
    capture_output=True,
    text=True,
    check=True,
).stdout.strip()
rate = eval(fps.replace("/", "/1.0/") if "/" in fps else fps)  # noqa: S307 - ffprobe "24/1"
TW, TH = 36, 64
raw = subprocess.run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-i",
        video,
        "-vf",
        f"scale={TW}:{TH},format=gray",
        "-an",
        "-f",
        "rawvideo",
        "-",
    ],
    capture_output=True,
    check=True,
).stdout
thumbs = [raw[i : i + TW * TH] for i in range(0, len(raw) - TW * TH + 1, TW * TH)]


def fdiff(t0, t1):
    """mean abs grey difference of the frames shown at t0 and t1 (0-255 scale)"""
    i, j = min(int(t0 * rate), len(thumbs) - 1), min(int(t1 * rate), len(thumbs) - 1)
    return sum(abs(p - q) for p, q in zip(thumbs[i], thumbs[j], strict=True)) / (TW * TH)


def best_cut(b, a):
    """(x, y, diff): cut out x..y inside the pause b..a; both audio fades stay inside the silence."""
    pad = (
        keep + FADE
    ) / 2  # old rule: silence left on each side of a cut; the xfade eats FADE of it
    x0, y0 = b + pad, a - pad
    if os.environ.get("MATCH", "1") == "0":
        return x0, y0, fdiff(x0, y0)
    best, step = (fdiff(x0, y0), x0, y0), 1 / rate
    lo, hi = b + FADE + 0.05, a - FADE - 0.05  # x - FADE >= b, y + FADE <= a
    removed = y0 - x0
    for r in (removed + step * k for k in range(-int(SLACK * rate), int(SLACK * rate) + 1)):
        x = lo
        while x + r <= hi:
            d = fdiff(x, x + r)
            if d < best[0] - 0.05:
                best = (d, x, x + r)
            x += step
    return best[1], best[2], best[0]


spans = speech_spans(os.environ.get("SPANS_FROM", video))
segs, start = [], 0.0
for (_, b), (a, _) in zip(spans, spans[1:], strict=False):
    if a - b > max_gap and not any(k0 <= b and a <= k1 for k0, k1 in KEEP):
        x, y, d = best_cut(b, a)
        segs.append((start, x))
        start = y
        kept = a - b - (y - x) - FADE
        flag = (
            f"  SHIFT: no still frame pair, KEEP={b:.2f}-{a:.2f} or cut by hand"
            if d > SHIFT_MAX
            else ""
        )
        print(
            f"pause {b:6.2f}-{a:6.2f} ({a - b:.2f} s) -> ~{kept:.2f} s, cut {x:.2f}->{y:.2f} diff {d:.1f}{flag}"
        )
segs.append((start, dur))
if len(segs) == 1:
    sys.exit(f"no pause over {max_gap} s; nothing to do")

f, t = [], 0.0
for k, (a, b) in enumerate(segs):
    f.append(f"[0:v]trim={a}:{b},setpts=PTS-STARTPTS,fps={fps},settb=1/24[v{k}]")
    f.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS[a{k}]")
v, a_ = "[v0]", "[a0]"
t = segs[0][1] - segs[0][0]
for k in range(1, len(segs)):
    t -= FADE
    f.append(f"{v}[v{k}]xfade=transition=fade:duration={FADE}:offset={t:.3f}[x{k}]")
    f.append(f"{a_}[a{k}]acrossfade=d={FADE}[y{k}]")
    v, a_ = f"[x{k}]", f"[y{k}]"
    t += segs[k][1] - segs[k][0]
subprocess.run(
    [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-i",
        video,
        "-filter_complex",
        ";".join(f),
        "-map",
        v,
        "-map",
        a_,
        "-c:v",
        "libx264",
        "-crf",
        "16",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        out,
    ],
    check=True,
)
print(f"WROTE {out}  {dur:.2f} s -> {t:.2f} s")
