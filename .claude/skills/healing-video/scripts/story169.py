"""Compose a long 16:9 narrated healing story: one clip per beat, voice-over per beat (vo/bN.wav),
serif subtitles, 0.6 s dissolves, each clip's own sound low under the voice, soft piano ducked under it.

  python3 story169.py story.json --music track.m4a --out out.mp4 [--dry]
"""
import argparse
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 24
XF = 0.6
LEAD, HOOK_LEAD, GAP, TAIL = 0.7, 0.35, 0.9, 3.0
# HV_ASSETS: a folder with the fonts (and rain) when this runs off the Mac (longform compose on Colab)
FONT = os.path.join(os.environ.get("HV_ASSETS", "/System/Library/Fonts/Supplemental"), "Georgia.ttf")
LNORM = str(Path(__file__).resolve().parent / "lnorm.py")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"failed: {' '.join(map(str, cmd))[:300]}\n{r.stderr[-2000:]}")
    return r


def dur(p):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).stdout)


def has_audio(p):
    return bool(run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of",
                     "csv=p=0", str(p)]).stdout.strip())


def luma(p, start):
    err = run(["ffmpeg", "-hide_banner", "-ss", str(start), "-t", "3", "-i", str(p), "-vf",
               "fps=2,signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"]).stderr
    v = [float(x) for x in re.findall(r"YAVG=([\d.]+)", err)]
    return sum(v) / len(v) if v else 135


def chunks(text, maxc=84):
    """Subtitle pages of at most 2 lines of ~maxc chars, split on sentence/phrase bounds."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > maxc and cur:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    lines.append(cur)
    return ["\n".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]


def sub_png(text, path):
    # small text hugging the bottom edge so it takes little of the scene (user 2026-11-12); a slim dark band
    # and an outline keep it readable on bright sky or light walls
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    font = ImageFont.truetype(FONT, 38)
    lines = text.split("\n")
    lh, bottom = 48, 40
    y0 = H - bottom - lh * len(lines)
    top = y0 - 36
    band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    for y in range(top, H):
        bd.line([(0, y), (W, y)], fill=(0, 0, 0, int(150 * min(1.0, (y - top) / 50))))
    img = Image.alpha_composite(img, band)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    for k, ln in enumerate(lines):
        tw = ds.textlength(ln, font=font)
        ds.text(((W - tw) / 2, y0 + lh * k + 2), ln, font=font, fill=(0, 0, 0, 255))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(3)))
    d = ImageDraw.Draw(img)
    for k, ln in enumerate(lines):
        tw = d.textlength(ln, font=font)
        d.text(((W - tw) / 2, y0 + lh * k), ln, font=font, fill=(255, 255, 255, 255),
               stroke_width=2, stroke_fill=(0, 0, 0, 230))
    img.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("story")
    ap.add_argument("--music", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    sp = Path(a.story).resolve()
    root = sp.parent
    beats = json.loads(sp.read_text())["beats"]
    tmp = root / "build"
    tmp.mkdir(exist_ok=True)

    plan, t = [], 0.0
    for i, b in enumerate(beats, 1):
        vo = root / "vo" / f"b{i}.wav"
        vd = dur(vo)
        lead = HOOK_LEAD if i == 1 else LEAD
        L = lead + vd + GAP + (TAIL if i == len(beats) else 0)
        plan.append(dict(i=i, clip=root / b.get("clip", f"s{i}.mp4"), start_clip=b.get("start", 0.8), vo=vo, vd=vd,
                         lead=lead, L=L, T=t, text=b["vo"], foley_db=float(b.get("foley_db", 0))))
        t += L
    total = t + XF * 0  # last segment carries no extra XF
    print(f"{len(plan)} beats, {total:.1f} s ({total / 60:.2f} min)")
    if a.dry:
        for p in plan:
            print(f"b{p['i']:>2} T={p['T']:6.1f} L={p['L']:4.1f} vo={p['vd']:4.1f}")
        return

    # 1. video segments with grade + subtitles; foley segments
    for p in plan:
        if (tmp / f"seg{p['i']}.mp4").exists() and (tmp / f"fol{p['i']}.wav").exists():
            p["seg"], p["fol"] = tmp / f"seg{p['i']}.mp4", tmp / f"fol{p['i']}.wav"
            continue
        need = p["L"] + (XF if p["i"] < len(plan) else 0)
        cd = dur(p["clip"])
        st = min(p["start_clip"], max(0.0, cd - need))
        avail = cd - st
        f = max(1.0, need / avail)
        if f > 1.6:
            st, f = 0.0, need / cd
        gamma = 1.0
        y = luma(p["clip"], st)
        if y < 125:
            gamma = min(1.5, math.log(max(y, 20) / 255) / math.log(130 / 255))
        # subtitle pages timed over the speech by character share
        pages = chunks(p["text"])
        total_c = sum(len(x) for x in pages)
        ov, inputs, t0 = [], [], p["lead"] - 0.1 + (XF / 2 if p["i"] > 1 else 0)
        span = p["vd"] + 0.2
        for k, pg in enumerate(pages):
            png = tmp / f"sub{p['i']}_{k}.png"
            sub_png(pg, png)
            inputs += ["-loop", "1", "-t", f"{need:.3f}", "-i", str(png)]
            d = span * len(pg) / total_c
            ov.append((t0, t0 + d))
            t0 += d
        vf = (f"[0:v]trim=start={st:.3f},setpts=(PTS-STARTPTS)*{f:.4f},fps={FPS},"
              f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"eq=gamma={gamma:.3f}:saturation=1.03:contrast=1.02,colorbalance=rs=0.02:bs=-0.02,"
              f"noise=alls=4:allf=t,trim=duration={need:.3f}[v0]")
        last = "v0"
        for k, (a0, a1) in enumerate(ov):
            vf += f";[{k + 1}:v]format=rgba,fade=in:st={a0:.2f}:d=0.25:alpha=1,fade=out:st={a1 - 0.25:.2f}:d=0.25:alpha=1[s{k}]"
            vf += f";[{last}][s{k}]overlay=0:0:enable='between(t,{a0:.2f},{a1:.2f})'[v{k + 1}]"
            last = f"v{k + 1}"
        seg = tmp / f"seg{p['i']}.mp4"
        run(["ffmpeg", "-y", "-hide_banner", "-i", str(p["clip"]), *inputs, "-filter_complex", vf, "-map", f"[{last}]",
             "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(seg)])
        fol = tmp / f"fol{p['i']}.wav"
        if has_audio(p["clip"]):
            atempo = 1 / f
            run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{st:.3f}", "-i", str(p["clip"]), "-af",
                 f"atempo={max(atempo, 0.5):.4f},atrim=duration={need:.3f},highpass=f=80,lowpass=f=9000,"
                 # beat's own gain (a clip whose people talk: "foley_db": -15), then a limiter so a shout or
                 # laugh in the clip never pokes out of the bed (sixth Christmas cut: clip voices too loud)
                 f"volume={p['foley_db']:.1f}dB,acompressor=threshold=0.05:ratio=8:attack=5:release=200,"
                 f"afade=in:d=0.3,afade=out:st={max(0, need - 0.5):.3f}:d=0.5", "-ar", "48000", "-ac", "2", str(fol)])
        else:
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{need:.3f}", str(fol)])
        p["seg"], p["fol"] = seg, fol
        print(f"seg {p['i']} ok (speed x{1 / f:.2f}, gamma {gamma:.2f})", flush=True)

    # 2. join video with dissolves
    ins, fc, last, off = [], "", "0:v", 0.0
    for p in plan:
        ins += ["-i", str(p["seg"])]
    for k in range(1, len(plan)):
        off += plan[k - 1]["L"]
        fc += f"[{last}][{k}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{k}];"
        last = f"x{k}"
    fc += f"[{last}]fade=out:st={total - 1.5:.3f}:d=1.5[vout]"
    video = tmp / "video.mp4"
    if not video.exists():
      run(["ffmpeg", "-y", "-hide_banner", *ins, "-filter_complex", fc, "-map", "[vout]", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), str(video)])

    # 3. audio: voice track, foley track, music ducked under voice
    def place(files, delays, out, pre=""):
        ins, fc = [], ""
        for k, (f_, d_) in enumerate(zip(files, delays, strict=False)):
            ins += ["-i", str(f_)]
            fc += f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,{pre}adelay={int(d_ * 1000)}:all=1[a{k}];"
        fc += "".join(f"[a{k}]" for k in range(len(files))) + f"amix=inputs={len(files)}:normalize=0,apad,atrim=duration={total:.3f}[o]"
        # -t caps the output: apad is infinite and a 37-input foley mix once ran past atrim, writing 700 GB of WAV
        run(["ffmpeg", "-y", "-hide_banner", *ins, "-filter_complex", fc, "-map", "[o]", "-t", f"{total:.3f}", str(out)])

    voice = tmp / "voice.wav"
    place([p["vo"] for p in plan], [p["T"] + p["lead"] + (XF / 2 if p["i"] > 1 else 0) for p in plan], voice,
          pre="highpass=f=70,")
    foley = tmp / "foley.wav"
    place([p["fol"] for p in plan], [p["T"] for p in plan], foley)
    # level stems: voice -18, foley -30 (hook louder via its own segment level), music -24 before ducking
    for stem, lufs in ((voice, -18), (foley, -31)):
        run(["python3", LNORM, str(stem), str(stem.with_suffix(".n.m4a")), str(lufs)])
    music = tmp / "music.wav"
    if a.music == "none":
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{total:.3f}",
             str(music.with_suffix(".n.m4a"))])
    else:
        run(["ffmpeg", "-y", "-hide_banner", "-stream_loop", "-1", "-i", a.music, "-af",
             f"atrim=duration={total:.3f},afade=in:st=0.8:d=2.5,afade=out:st={total - 4:.3f}:d=4,aresample=48000,"
             "aformat=channel_layouts=stereo", str(music)])
        run(["python3", LNORM, str(music), str(music.with_suffix(".n.m4a")), "-25"])
    mix = tmp / "mix.wav"
    # the voice ducks both the piano and the clips' own sound (their generated speech fought the narration)
    fc = ("[1:a]asplit=3[vsc][vsc2][vmix];[2:a][vsc]sidechaincompress=threshold=0.03:ratio=4:attack=80:release=900[mduck];"
          "[0:a][vsc2]sidechaincompress=threshold=0.03:ratio=3:attack=60:release=700[fduck];"
          "[fduck][vmix][mduck]amix=inputs=3:normalize=0[o]")
    run(["ffmpeg", "-y", "-hide_banner", "-i", str(foley.with_suffix(".n.m4a")), "-i", str(voice.with_suffix(".n.m4a")),
         "-i", str(music.with_suffix(".n.m4a")), "-filter_complex", fc, "-map", "[o]", str(mix)])
    final_a = tmp / "final.m4a"
    run(["python3", LNORM, str(mix), str(final_a), "-16"])
    run(["ffmpeg", "-y", "-hide_banner", "-i", str(video), "-i", str(final_a), "-map", "0:v", "-map", "1:a", "-c:v",
         "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out])
    print(f"wrote {a.out} ({dur(a.out):.1f} s)")


if __name__ == "__main__":
    main()
