"""Assemble a gown-run video: the reference reel's 7 hard cuts (4.2 / 1.6 / 1.3 / 1.3 / 1.6 / 1.1 / 3.9 s
= 15 s), a bright grade (a shot under BRIGHT mean luma gets a gamma lift first), music over the
clips' wind ambience, fade out on the hero frame.

Usage:
  python3 scripts/compose.py --idea idea.json --music track.m4a --out gown-<slug>.mp4 \
      s1.mp4 s2.mp4@1.5 ... s7.mp4      # clip@start = where the window starts (default 1.0 s)
  [--cuts 4.2,1.6,...] [--ambience 0.25] [--size 1080x1920]
"""
import argparse
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

LNORM = Path(__file__).resolve().parent.parent.parent / "healing-video/scripts/lnorm.py"
BRIGHT = 115  # minimum mean luma of a shot before the grade (real bright daylight footage sits at 110-130)
XF = 0.3  # ambience cross-fade between shots (s): a hard-cut wind bed jumps in level at every cut


def has_audio(clip):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", clip], capture_output=True, text=True)
    return bool(r.stdout.strip())


def luma(path):
    out = subprocess.run(["ffmpeg", "-i", path, "-vf", "fps=2,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
                          "-an", "-f", "null", "-"], capture_output=True, text=True).stdout
    v = [float(ln.split("=")[1]) for ln in out.splitlines() if "YAVG=" in ln]
    return sum(v) / len(v)


def lift(path):
    """gamma lift for a clip darker than BRIGHT, so no shot reads dim"""
    m = luma(path)
    if m >= BRIGHT:
        return ""
    g = min(1.8, math.log(m / 255) / math.log(BRIGHT / 255))
    print(f"note: {path} mean luma {m:.0f} < {BRIGHT}: gamma {g:.2f}", file=sys.stderr)
    return f"eq=gamma={g:.2f},"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+", help="shot.mp4 or shot.mp4@start_seconds, in shot order")
    ap.add_argument("--idea", required=True, help="idea JSON (ideas.py next/show output)")
    ap.add_argument("--music", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cuts", help="comma-separated seconds per shot (default: the idea's cuts)")
    ap.add_argument("--ambience", type=float, default=0.25, help="clips' wind/fabric sound under the music")
    ap.add_argument("--size", default="1080x1920")
    a = ap.parse_args()

    idea = json.loads(Path(a.idea).read_text())
    cuts = [float(x) for x in a.cuts.split(",")] if a.cuts else idea["cuts"]
    n = len(a.clips)
    if len(cuts) != n:
        raise SystemExit(f"{n} clips but {len(cuts)} cuts")
    w, h = map(int, a.size.split("x"))
    total = sum(cuts)
    tmp = Path(tempfile.mkdtemp())
    fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=r_frame_rate",
                          "-of", "csv=p=0", a.clips[0].partition("@")[0]], capture_output=True, text=True).stdout.strip()

    args, graph = ["ffmpeg", "-v", "error", "-y"], []
    for c, d in zip(a.clips, cuts, strict=True):
        path, _, start = c.partition("@")
        args += ["-ss", start or "1.0", "-t", f"{d + XF:.3f}", "-i", path]
    args += ["-i", a.music]
    for i, d in enumerate(cuts):
        # bright real-footage grade: the old dark cinematic grade + vignette took gr-001 v1 to luma 63 and read
        # as AI; lift dim shots, a touch of saturation, no vignette
        graph.append(f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps},setsar=1,"
                     f"{lift(a.clips[i].partition('@')[0])}eq=contrast=1.02:saturation=1.06:brightness=0.02,vibrance=intensity=0.15,"
                     f"trim=duration={d:.3f},setpts=PTS-STARTPTS[v{i}]")
        path = a.clips[i].partition("@")[0]
        src = f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo" if has_audio(path) else \
            f"anullsrc=r=44100:cl=stereo,atrim=duration={d + XF:.3f}"
        graph.append(f"{src},asetpts=PTS-STARTPTS[a{i}]")
    prev = "a0"
    for i in range(1, n):
        graph.append(f"[{prev}][a{i}]acrossfade=d={XF}:c1=qsin:c2=qsin[x{i}]")
        prev = f"x{i}"
    graph += [
        "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,fade=t=in:d=0.2,"
        f"fade=t=out:st={total - 0.6:.3f}:d=0.6,format=yuv420p[vout]",
        f"[{prev}]atrim=duration={total:.3f},afftdn=nf=-30,loudnorm=I=-30,volume={a.ambience}[amb]",
        f"[{n}:a]atrim=duration={total:.3f},afade=in:d=0.2,afade=out:st={total - 1.5:.3f}:d=1.5[mus]",
        "[mus][amb]amix=inputs=2:normalize=0[aout]",
    ]
    args += ["-filter_complex", ";".join(graph), "-map", "[vout]", "-map", "[aout]",
             "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "pcm_s16le", str(tmp / "mix.mov")]
    subprocess.run(args, check=True)
    # one fixed gain to -14 LUFS (single-pass loudnorm pumps), then mux
    subprocess.run(["python3", str(LNORM), str(tmp / "mix.mov"), str(tmp / "mix.m4a"), "-14"], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp / "mix.mov"), "-i", str(tmp / "mix.m4a"),
                    "-map", "0:v", "-map", "1:a", "-c", "copy", "-movflags", "+faststart", a.out], check=True)
    print(f"{a.out}: {n} shots = {total:.1f} s")


if __name__ == "__main__":
    main()
