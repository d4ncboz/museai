#!/usr/bin/env python3
"""Cut the rendered shots into the reel the way the reference reels look, then add subtitles and new words.

  uv run --no-project --python 3.12 --with faster-whisper --with 'av<14' --with pillow python scripts/finish.py WORK OUT.mp4

WORK holds script.json (build.py) and clips/<id>-<shot>.mp4 (render.sh). Steps:
1. Per line shot, Whisper word times -> keep 0.35 s before the first word to 0.6 s after the last
   (the reaction beat the reference reels hold; a shot's "hold": N keeps N s after it, for a payoff such as
   a laugh after the punchline); a silent shot keeps 0.3 s .. 0.3 + sec. Each heard
   line is compared with the script; under 70 % word match prints MISHEARD (re-render that shot).
2. Every segment is graded and re-encoded to 720x1280 (the references' size: a softer picture reads as
   film, 1080p micro-detail reads as AI), exactly N frames at 24 fps with its audio padded/cut to the same
   length, then joined with hard cuts (concat demuxer), so lips never drift at a join.
3. Overlays (Pillow PNGs, ffmpeg overlay with enable windows), all as in references/reference-study.md:
   each spoken line as a small white English subtitle centred at ~74 %, an optional handle watermark
   (HANDLE="@page"), then a 3.5 s "new words" card (script `words`, else its phrase) over a blurred
   freeze of the last frame. Nothing else: no hook, no translation line, no highlight.
Optional MUSIC=file.m4a lays a bed at MUSIC_DB (default -26 dB) under the reel.
Writes WORK/trims.json, WORK/cues.json ([start, end, en] in reel time) and OUT."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 720, 1280, 24
FONTS = "/System/Library/Fonts/Supplemental/"
ROUND, SERIF, ITALIC = FONTS + "Arial Rounded Bold.ttf", FONTS + "Georgia Bold.ttf", FONTS + "Georgia Italic.ttf"
VI = FONTS + "Arial Bold.ttf"  # Arial Rounded has no Vietnamese diacritics
WHITE = (255, 255, 255)
HANDLE = os.environ.get("HANDLE", "")
CARD = 3.5


# Grade toward the reference reels: soft, low-contrast, gently muted warm pastel. A small lift and a soft
# top end, a little less saturation, warm mids, a light screen-blended halation, a touch of blur to take
# the AI micro-sharpness off skin, fine grain. References: mean RGB 88-130/72-109/65-96, shadows ~20/15/10,
# mids R-B 25-42. RGB before the blend: a screen blend on YUV planes shifts colour to magenta.
GRADE = os.environ.get("GRADE", "format=gbrp,curves=all='0/0.05 0.25/0.29 0.5/0.58 0.8/0.86 1/0.97',"
                       "eq=saturation=0.86,colorbalance=rs=0.01:bs=-0.01:rm=0.025:bm=-0.025:rh=0.01:bh=-0.005,"
                       "split[a][b];[b]gblur=sigma=24[g];[a][g]blend=all_mode=screen:all_opacity=0.12,"
                       "gblur=sigma=0.6,noise=alls=4:allf=t,format=yuv420p")


def run(a, **kw):
    return subprocess.run(a, check=True, **kw)


def dur(p):
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                     capture_output=True, text=True).stdout)


def words_of(s):
    return re.findall(r"[a-z]+", s.lower().replace("'", "").replace("’", ""))


def trims(work, sc):
    from faster_whisper import WhisperModel
    model = WhisperModel(os.environ.get("WMODEL", "small.en"), device="cpu", compute_type="int8")
    out, bad = {}, []
    for sh in sc["shots"]:
        clip = work / "clips" / f"{sc['id'].lower()}-{sh['id']}.mp4"
        d = dur(clip)
        if not sh.get("line"):
            a = min(0.3, max(0, d - sh["sec"]))
            out[sh["id"]] = [a, min(d, a + sh["sec"]), None, None]
            continue
        segs, _ = model.transcribe(str(clip), language="en", word_timestamps=True, vad_filter=False)
        ws = [w for s in segs for w in s.words]
        heard = " ".join(w.word.strip() for w in ws)
        want = words_of(sh["line"]["en"])
        got = words_of(heard)
        match = sum(1 for w in want if any(g == w or g.endswith(w) for g in got)) / max(1, len(want))
        if not ws or match < 0.7:
            bad.append(sh["id"])
            print(f"MISHEARD {sh['id']}: want {sh['line']['en']!r} heard {heard!r}")
        # muse sometimes says the line twice: keep only up to the word that completes it the first time
        last, i = len(ws) - 1, 0
        for j, w in enumerate(ws):
            g = words_of(w.word)
            if i < len(want) and g and (g[0] == want[i] or g[0].endswith(want[i])):
                i += 1
                if i == len(want):
                    last = j
                    break
        s = max(0.0, (ws[0].start if ws else 0.6) - 0.35)
        said = ws[last].end if ws else sh["sec"]
        e = min(d, said + sh.get("hold", 0.6))
        out[sh["id"]] = [round(s, 3), round(e, 3), round((ws[0].start if ws else 0.6) - s, 3), round(said + 0.5 - s, 3)]
        print(f"{sh['id']} {match:.0%} heard {heard!r} keep {s:.2f}-{e:.2f}")
    (work / "trims.json").write_text(json.dumps(out, indent=1))
    return out, bad


def cut(work, sc, tr):
    segs, cues, t = [], [], 0.0
    for sh in sc["shots"]:
        clip = work / "clips" / f"{sc['id'].lower()}-{sh['id']}.mp4"
        s, e, lead, said = tr[sh["id"]]
        n = max(1, round((e - s) * FPS))
        length = n / FPS
        seg = work / "seg" / f"{sh['id']}.mp4"
        seg.parent.mkdir(exist_ok=True)
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s}", "-i", str(clip), "-frames:v", str(n),
             # the 540 p pass gives the soft DVD picture of the references (no crisp micro-detail)
             "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},fps={FPS},"
                    f"scale=540:960:flags=area,scale={W}:{H}:flags=bicubic,"
                    f"setsar=1,{GRADE}",
             "-af", f"aresample=48000,apad,atrim=0:{length:.4f}", "-ar", "48000", "-ac", "2",
             "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
             str(seg)])
        if sh.get("line"):
            cues.append([round(t + lead - 0.1, 3), round(t + min(said, length), 3), sh["line"]["en"]])
        segs.append(seg)
        t += length
    lst = work / "seg" / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in segs))
    film = work / "film.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(film)])
    (work / "cues.json").write_text(json.dumps(cues, ensure_ascii=False, indent=1))
    return film, cues, t


def font(p, size):
    return ImageFont.truetype(p, size)


def wrap(text, f, maxw, d):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur]


def centred(d, y, text, f, fill, stroke=2):
    d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill, stroke_width=stroke,
           stroke_fill=(20, 16, 14))


def subtitle_png(en, path):
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    f = font(ROUND, 30)
    rows = wrap(en, f, W * 0.8, d)
    y = int(H * 0.735) - 19 * (len(rows) - 1)
    for r in rows:
        centred(d, y, r, f, WHITE)
        y += 38
    img.save(path)


def handle_png(path):
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    f = font(ITALIC, 20)
    d.text((W - 40 - d.textlength(HANDLE, font=f), int(H * 0.945)), HANDLE, font=f, fill=(255, 255, 255, 140))
    img.save(path)


def words_png(frame, words, path):
    base = Image.open(frame).convert("RGB").resize((W, H)).filter(ImageFilter.GaussianBlur(14))
    base = Image.blend(base, Image.new("RGB", (W, H), (14, 11, 10)), 0.5).convert("RGBA")
    d = ImageDraw.Draw(base)
    fh, fe, fv = font(ROUND, 22), font(SERIF, 40), font(VI, 25)
    blocks = [[(r, fe, WHITE, 50) for r in wrap(w["en"], fe, W * 0.84, d)]
              + [(r, fv, (232, 224, 218), 38) for r in wrap(w["vi"], fv, W * 0.84, d)] for w in words]
    y = (H - 64 - sum(sum(x[3] for x in b) + 36 for b in blocks)) / 2
    centred(d, y, "NEW WORDS", fh, (255, 255, 255, 200), 1)
    y += 64
    for b in blocks:
        for r, f, c, lh in b:
            centred(d, y, r, f, c, 1)
            y += lh
        y += 36
    base.save(path)


def finish(work, out):
    work = Path(work)
    sc = json.loads((work / "script.json").read_text())
    tr, bad = trims(work, sc)
    film, cues, total = cut(work, sc, tr)
    ov = work / "ov"
    ov.mkdir(exist_ok=True)
    last = ov / "last.png"
    run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.05", "-i", str(film), "-frames:v", "1", "-update", "1", str(last)])
    words_png(last, sc.get("words") or [sc["phrase"]], ov / "card.png")
    for i, c in enumerate(cues):
        subtitle_png(c[2], ov / f"sub{i}.png")
    end = total + CARD
    inputs = ["-i", str(film), "-loop", "1", "-t", f"{CARD}", "-i", str(ov / "card.png")]
    fc = [f"[1:v]fps={FPS},format=yuv420p,setsar=1[card]", "[0:v][card]concat=n=2:v=1:a=0[v0]"]
    cur, k = "v0", 2
    if HANDLE:
        handle_png(ov / "handle.png")
        inputs += ["-i", str(ov / "handle.png")]
        fc.append(f"[v0][2:v]overlay=enable='lt(t,{total:.3f})'[vh]")
        cur, k = "vh", 3
    for i, (s, e, _) in enumerate(cues):
        inputs += ["-i", str(ov / f"sub{i}.png")]
        nxt = cues[i + 1][0] if i + 1 < len(cues) else total
        fc.append(f"[{cur}][{k + i}:v]overlay=enable='between(t,{max(0, s):.3f},{min(e, nxt, total):.3f})'[c{i}]")
        cur = f"c{i}"
    fc.append(f"[0:a]apad=whole_dur={end:.3f},afade=t=out:st={total:.3f}:d=1.5[a0]")
    amap = "[a0]"
    music = os.environ.get("MUSIC")
    if music:
        inputs += ["-stream_loop", "-1", "-i", music]
        fc.append(f"[{k + len(cues)}:a]atrim=0:{end:.3f},volume={os.environ.get('MUSIC_DB', '-26')}dB,"
                  f"afade=t=in:d=1,afade=t=out:st={end - 2:.3f}:d=2[m]")
        fc.append("[a0][m]amix=inputs=2:duration=first:normalize=0[a1]")
        amap = "[a1]"
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", f"[{cur}]", "-map", amap,
         "-t", f"{end:.3f}", "-r", str(FPS), "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)])
    print(f"{out}: {end:.1f} s, {len(cues)} lines" + (f", MISHEARD {bad}" if bad else ""))
    return not bad


if __name__ == "__main__":
    sys.exit(0 if finish(*sys.argv[1:3]) else 1)
