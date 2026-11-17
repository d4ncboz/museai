#!/usr/bin/env python3
"""The ~15 s vertical hook (1080x1920) cut from the long film's own clips: no new renders, same quota.
A beat whose clip is not rendered yet (muse video quota) falls back to its still with a slow push-in.

  python3 short.py story.json --music music.m4a --out healing-<slug>-short.mp4

story.json `short`: {"text": "hook line", "shots": [[beat, start_s, secs, x], ...]} where x (0..1) is the centre
of the 9:16 crop inside the 16:9 frame (0.5 = middle; put her hands or the food there). 4-6 shots of 2.5-3.5 s:
open on the most striking motion (a burr opening, steam off the lid), end on the meal. The clips' own sound
under quiet music. The hook line sits in the upper third for the first 3.5 s, clear of the platform UI below.
Needs Pillow (the ACE-Step venv python has it).
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, XF = 1080, 1920, 30, 0.35
ITALIC = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
LNORM = Path(__file__).resolve().parents[2] / "healing-video" / "scripts" / "lnorm.py"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"failed: {' '.join(map(str, cmd))[:300]}\n{r.stderr[-1500:]}")


def text_png(line, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    f = ImageFont.truetype(ITALIC, 76)
    words, lines, cur = line.split(), [], ""
    d = ImageDraw.Draw(img)
    for w in words:
        t = f"{cur} {w}".strip()
        if d.textlength(t, font=f) > W - 180 and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    lines.append(cur)
    y0 = int(H * 0.22)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    for k, ln in enumerate(lines):
        ds.text(((W - ds.textlength(ln, font=f)) / 2, y0 + k * 100 + 3), ln, font=f, fill=(0, 0, 0, 200))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(img)
    for k, ln in enumerate(lines):
        d.text(((W - d.textlength(ln, font=f)) / 2, y0 + k * 100), ln, font=f, fill=(250, 244, 230, 255))
    img.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("story")
    ap.add_argument("--music", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sp = Path(a.story).resolve()
    root, story = sp.parent, json.loads(sp.read_text())
    sh = story["short"]
    tmp = root / "build-short"
    tmp.mkdir(exist_ok=True)
    segs = []
    for k, (beat, st, secs, x) in enumerate(sh["shots"]):
        src, still = root / f"s{beat}.mp4", root / "stills" / f"s{beat}.png"
        need = secs + (XF if k < len(sh["shots"]) - 1 else 0)
        seg = tmp / f"v{k}.mp4"
        crop = f"crop=608:1080:'min(max(0,{x}*1920-304),1312)':0,scale={W}:{H}:flags=lanczos"
        afade = (f"aresample=48000,aformat=channel_layouts=stereo,afade=in:d=0.2,"
                 f"afade=out:st={need - 0.3:.3f}:d=0.3")
        if src.exists():
            # 16:9 -> 9:16: crop the full height, 1080*9/16 = 607.5 wide around x, upscale with lanczos
            vf = (f"scale=1920:1080,{crop},fps={FPS},eq=saturation=0.96,noise=alls=3:allf=t,"
                  f"trim=duration={need:.3f},setpts=PTS-STARTPTS")
            run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{st}", "-i", str(src), "-vf", vf, "-af",
                 f"atrim=duration={need:.3f},asetpts=PTS-STARTPTS,{afade}", "-c:v", "libx264", "-crf", "17",
                 "-pix_fmt", "yuv420p", str(seg)])
        elif still.exists():
            # clip not rendered yet (muse video quota): the still with a slow push-in, room tone under it
            n = int(need * FPS) + 1
            vf = (f"scale=3840:2160,zoompan=z='1+0.04*on/{n}':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d={n}:"
                  f"s=1920x1080:fps={FPS},{crop},eq=saturation=0.96,noise=alls=3:allf=t")
            run(["ffmpeg", "-y", "-hide_banner", "-loop", "1", "-i", str(still), "-f", "lavfi", "-i",
                 "anoisesrc=color=brown:amplitude=0.002", "-vf", vf, "-af", afade, "-t", f"{need:.3f}",
                 "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", str(seg)])
        else:
            sys.exit(f"short: no clip or still for beat {beat}")
        segs.append((seg, secs))
    total = sum(s for _, s in segs)
    ins, fc, last, alast, off = [], "", "0:v", "0:a", 0.0
    for seg, _ in segs:
        ins += ["-i", str(seg)]
    for k in range(1, len(segs)):
        off += segs[k - 1][1]
        fc += f"[{last}][{k}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{k}];"
        fc += f"[{alast}][{k}:a]acrossfade=d={XF}[y{k}];"
        last, alast = f"x{k}", f"y{k}"
    png = tmp / "hook.png"
    text_png(sh["text"], png)
    ins += ["-loop", "1", "-t", f"{total:.3f}", "-i", str(png)]
    t = len(segs)
    fc += (f"[{t}:v]format=rgba,fade=in:st=0.2:d=0.5:alpha=1,fade=out:st=3.3:d=0.5:alpha=1[t];"
           f"[{last}][t]overlay=0:0:enable='between(t,0,3.9)',fade=out:st={total - 0.8:.3f}:d=0.8[v]")
    video = tmp / "video.mp4"
    run(["ffmpeg", "-y", "-hide_banner", *ins, "-filter_complex", fc, "-map", "[v]", "-map", f"[{alast}]",
         "-t", f"{total:.3f}", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le",
         str(tmp / "v.mkv")])
    run(["ffmpeg", "-y", "-hide_banner", "-i", str(tmp / "v.mkv"), "-c:v", "copy", "-an", str(video)])
    run(["ffmpeg", "-y", "-hide_banner", "-i", str(tmp / "v.mkv"), "-vn", str(tmp / "fol.wav")])
    run(["python3", str(LNORM), str(tmp / "fol.wav"), str(tmp / "fol.n.m4a"), "-22"])
    run(["ffmpeg", "-y", "-hide_banner", "-i", a.music, "-af",
         f"atrim=duration={total:.3f},afade=in:d=0.4,afade=out:st={total - 1.2:.3f}:d=1.2", str(tmp / "mus.wav")])
    run(["python3", str(LNORM), str(tmp / "mus.wav"), str(tmp / "mus.n.m4a"), "-21"])
    run(["ffmpeg", "-y", "-hide_banner", "-i", str(tmp / "fol.n.m4a"), "-i", str(tmp / "mus.n.m4a"),
         "-filter_complex", "[0:a][1:a]amix=inputs=2:normalize=0[o]", "-map", "[o]", str(tmp / "mix.wav")])
    run(["python3", str(LNORM), str(tmp / "mix.wav"), str(tmp / "mix.n.m4a"), "-14"])
    run(["ffmpeg", "-y", "-hide_banner", "-i", str(video), "-i", str(tmp / "mix.n.m4a"), "-map", "0:v", "-map",
         "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out])
    print(f"wrote {a.out} ({total:.1f} s)")


if __name__ == "__main__":
    main()
