"""Usage: qa.py quizzes/<topic>.json out.mp4
Run: uv run --no-project --python 3.12 --with numpy python scripts/qa.py ...

Final gate. Prints PASS/FAIL per check and `RESULT PASS|FAIL`:
  format     1080x1920, 30 fps, h264 + aac, duration = 3 + 8.5 x words + 3.5 s (+-0.3)
  loudness   -14 LUFS +-1.5, true peak <= -1 dBTP
  hook       frame 0 is not dark (mean luma > 40) and has text-like detail (edge density),
             the picture moves in the first second (mean frame diff 0 -> 0.5 s), sound starts
             before 0.3 s, and the first 3 s hold no silence > 0.4 s
  pace       a visible change at least every 3.5 s (scene-diff peaks), the way a quiz keeps eyes on it
  loop       last frame resembles the first scene (the replay seam)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

W, H = 1080, 1920


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def frame(path, t, w=270, h=480):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                          "-vf", f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w).astype(np.float32)


def main(quiz, video):
    q = json.loads(Path(quiz).read_text())
    res = []

    def check(name, ok, detail):
        res.append(ok)
        print("PASS" if ok else "FAIL", f"{name:10s}", detail)

    p = json.loads(run("ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", video).stdout)
    v = next(s for s in p["streams"] if s["codec_type"] == "video")
    a = next((s for s in p["streams"] if s["codec_type"] == "audio"), None)
    dur = float(p["format"]["duration"])
    want = 3 + 8.5 * len(q["words"]) + 3.5
    check("format", v["width"] == W and v["height"] == H and v["r_frame_rate"] == "30/1"
          and v["codec_name"] == "h264" and a and a["codec_name"] == "aac" and abs(dur - want) < 0.3,
          f"{v['width']}x{v['height']} {v['r_frame_rate']} {v['codec_name']}/{a and a['codec_name']} {dur:.2f}s (want {want:.1f})")

    ln = run("ffmpeg", "-hide_banner", "-i", video, "-af", "ebur128=peak=true", "-f", "null", "-").stderr
    i_lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", ln)[-1])
    peak = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", ln)[-1])
    check("loudness", abs(i_lufs + 14) <= 1.5 and peak <= -1.0, f"{i_lufs:.1f} LUFS, true peak {peak:.1f} dBTP")

    f0, f05 = frame(video, 0), frame(video, 0.5)
    edges = np.mean(np.abs(np.diff(f0, axis=1)) > 40)
    motion = float(np.mean(np.abs(f05 - f0)))
    sil = run("ffmpeg", "-hide_banner", "-t", "3", "-i", video, "-af", "silencedetect=n=-45dB:d=0.4", "-f", "null", "-").stderr
    gaps = re.findall(r"silence_start: (-?[\d.]+)", sil)
    first = run("ffmpeg", "-hide_banner", "-t", "0.3", "-i", video, "-af", "volumedetect", "-f", "null", "-").stderr
    mx = float(re.search(r"max_volume: (-?[\d.]+) dB", first).group(1))
    check("hook", f0.mean() > 40 and edges > 0.01 and motion > 4 and mx > -30 and not gaps,
          f"frame0 luma {f0.mean():.0f}, text edges {edges:.3f}, motion 0-0.5s {motion:.1f}, "
          f"sound by 0.3s {mx:.0f} dB, silences in 0-3s {gaps or 'none'}")

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", "fps=4,scale=90:160,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 160, 90).astype(np.float32)
    ts = np.arange(len(fr)) / 4
    # local change: the busiest 10x10 cell, so a ticking ring or a popping card counts, not only cuts
    cells = np.abs(np.diff(fr, axis=0))[:, :160, :90].reshape(len(fr) - 1, 16, 10, 9, 10).mean(axis=(2, 4))
    events = [float(ts[i + 1]) for i, c in enumerate(cells.max(axis=(1, 2))) if c > 12]
    holes = [(round(a, 1), round(b, 1)) for a, b in zip([0.0, *events], [*events, dur], strict=True) if b - a > 3.5]
    check("pace", not holes, f"{len(events)} visible changes, still stretches > 3.5 s: {holes or 'none'}")

    # colour layout only (27x48): the hook's stickers sit on the same scene the outro ends on
    last, f_hook = frame(video, dur - 0.05, 27, 48), frame(video, 0.2, 27, 48)
    diff = float(np.mean(np.abs(last - f_hook)))
    check("loop", diff < 40, f"last vs first frame diff {diff:.1f} (< 40)")
    print("RESULT", "PASS" if all(res) else "FAIL")
    return 0 if all(res) else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(*sys.argv[1:]))
