"""Usage: jumps.py video.mp4  -> one-frame picture jumps (exit 1 if any).
A jump is a frame whose luma change (signalstats YDIF) is > 3, > 5x the median of the
25 frames around it and > 2.5x both neighbours: the picture snaps (reframe, zoom, pose)
between two frames. Too small for qa's hard-cut detector, but the user sees it as a glitch.
EP09 v7: each clip seam jumped 17.3 (clips start ~3.7 % zoomed against the previous clip's
last frame) and muse clip B snapped 6 times inside the clip (YDIF 3-9); calm frames sit at
~0.6. Dissolves (xfade) spread the change over several frames and are not flagged.
Run it before burn_subs.py: each caption appearing or leaving is a one-frame jump too."""

import re
import statistics
import subprocess
import sys


def jumps(video):
    """[(time, ydif, local_median), ...]"""
    out = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            video,
            "-vf",
            "signalstats,metadata=print:key=lavfi.signalstats.YDIF:file=-",
            "-an",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    ).stdout
    t = [float(x) for x in re.findall(r"pts_time:([\d.]+)", out)]
    y = [float(x) for x in re.findall(r"YDIF=([\d.]+)", out)]
    found = []
    for i in range(1, len(y) - 1):
        local = statistics.median(y[max(0, i - 12) : i + 13])
        if y[i] > 3 and y[i] > 5 * local and y[i] > 2.5 * max(y[i - 1], y[i + 1]):
            found.append((t[i], y[i], local))
    return found


if __name__ == "__main__":
    found = jumps(sys.argv[1])
    for t, v, local in found:
        print(f"JUMP {t:6.2f}s  YDIF {v:4.1f} (around {local:.1f})")
    print("RESULT", "ok" if not found else f"FAIL {len(found)} jumps")
    sys.exit(1 if found else 0)
