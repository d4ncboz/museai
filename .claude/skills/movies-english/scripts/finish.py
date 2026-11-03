#!/usr/bin/env python3
"""Cut the rendered shots into the reel, then burn hook, bilingual captions and the phrase card.

  uv run --no-project --python 3.12 --with faster-whisper --with pillow python scripts/finish.py WORK OUT.mp4

WORK holds script.json (build.py) and clips/<id>-<shot>.mp4 (render.sh). Steps:
1. Per line shot, Whisper word times -> keep 0.35 s before the first word to 0.6 s after the last
   (the reaction beat the reference reels hold); a silent shot keeps 0.3 s .. 0.3 + sec. Each heard
   line is compared with the script; under 70 % word match prints MISHEARD (re-render that shot).
2. Every segment is re-encoded to 1080x1920, exactly N frames at 24 fps with its audio padded/cut to
   the same length, then joined with hard cuts (concat demuxer), so lips never drift at a join.
3. Overlays (Pillow PNGs, ffmpeg overlay with enable windows): the Vietnamese hook in the top band for
   the first 2.8 s, each line's English (key phrase in yellow) with Vietnamese under it in the lower
   caption band (y 62-74 %, clear of faces and of platform buttons), a small handle bottom-left, then a
   3 s phrase card over a blurred, darkened freeze of the last frame.
Optional MUSIC=file.m4a lays a bed at MUSIC_DB (default -24 dB) under the reel.
Writes WORK/trims.json, WORK/cues.json ([start, end, en, vi] in reel time) and OUT."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 24
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
REG = "/System/Library/Fonts/Supplemental/Arial.ttf"
SERIF = "/System/Library/Fonts/Supplemental/Georgia Bold.ttf"
YELLOW, WHITE = (255, 214, 64), (255, 255, 255)
HANDLE = os.environ.get("HANDLE", "Movies English")


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
            out[sh["id"]] = [a, min(d, a + sh["sec"]), None]
            continue
        segs, _ = model.transcribe(str(clip), language="en", word_timestamps=True, vad_filter=False)
        ws = [w for s in segs for w in s.words]
        heard = " ".join(w.word.strip() for w in ws)
        want = words_of(sh["line"]["en"])
        got = words_of(heard)
        match = sum(1 for w in want if w in got) / max(1, len(want))
        if not ws or match < 0.7:
            bad.append(sh["id"])
            print(f"MISHEARD {sh['id']}: want {sh['line']['en']!r} heard {heard!r}")
        s = max(0.0, (ws[0].start if ws else 0.6) - 0.35)
        e = min(d, (ws[-1].end if ws else sh["sec"]) + 0.6)
        out[sh["id"]] = [round(s, 3), round(e, 3), round((ws[0].start if ws else 0.6) - s, 3)]
        print(f"{sh['id']} {match:.0%} heard {heard!r} keep {s:.2f}-{e:.2f}")
    (work / "trims.json").write_text(json.dumps(out, indent=1))
    return out, bad


def cut(work, sc, tr):
    segs, cues, t = [], [], 0.0
    for sh in sc["shots"]:
        clip = work / "clips" / f"{sc['id'].lower()}-{sh['id']}.mp4"
        s, e, lead = tr[sh["id"]]
        n = max(1, round((e - s) * FPS))
        length = n / FPS
        seg = work / "seg" / f"{sh['id']}.mp4"
        seg.parent.mkdir(exist_ok=True)
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s}", "-i", str(clip), "-frames:v", str(n),
             "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1",
             "-af", f"aresample=48000,apad,atrim=0:{length:.4f}", "-ar", "48000", "-ac", "2",
             "-c:v", "libx264", "-crf", "15", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
             str(seg)])
        if sh.get("line"):
            cues.append([round(t + lead - 0.1, 3), round(t + length, 3), sh["line"]["en"], sh["line"]["vi"]])
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


def outlined(d, xy, text, f, fill, stroke=6):
    d.text(xy, text, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))


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


def caption_png(en, vi, phrase, path):
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    fe, fv = font(BOLD, 66), font(BOLD, 44)
    y = int(H * 0.63)
    # mark the key phrase (any inflection of its words, in order) in yellow
    keys = set(words_of(phrase))
    for row in wrap(en, fe, W * 0.84, d):
        x = (W - d.textlength(row, font=fe)) / 2
        for i, tok in enumerate(row.split(" ")):
            tok_s = tok + (" " if i < len(row.split(" ")) - 1 else "")
            hit = any(k == w or (len(k) > 3 and w.startswith(k[:-1])) for w in words_of(tok) for k in keys)
            outlined(d, (x, y), tok_s, fe, YELLOW if hit else WHITE)
            x += d.textlength(tok_s, font=fe)
        y += 80
    y += 6
    for row in wrap(vi, fv, W * 0.84, d):
        outlined(d, ((W - d.textlength(row, font=fv)) / 2, y), row, fv, (235, 235, 235), 5)
        y += 56
    img.save(path)


def hook_png(text, path):
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    f = font(BOLD, 58)
    text = re.sub(r"[^\w\s?!.,'’:-]", "", text).strip()
    rows = wrap(text, f, W * 0.8, d)
    bh = 76 * len(rows) + 36
    y0 = int(H * 0.11)
    bw = max(d.textlength(r, font=f) for r in rows) + 64
    d.rounded_rectangle(((W - bw) / 2, y0, (W + bw) / 2, y0 + bh), 26, fill=(214, 40, 60, 235))
    for i, r in enumerate(rows):
        d.text(((W - d.textlength(r, font=f)) / 2, y0 + 18 + 76 * i), r, font=f, fill=WHITE)
    fs = font(BOLD, 34)
    tag = "Học tiếng Anh qua phim"
    outlined(d, ((W - d.textlength(tag, font=fs)) / 2, y0 + bh + 18), tag, fs, WHITE, 4)
    img.save(path)


def handle_png(path):
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    f = font(SERIF, 30)
    d.text((W - 60 - d.textlength(HANDLE, font=f), int(H * 0.585)), HANDLE, font=f, fill=(255, 255, 255, 150))
    img.save(path)


def card_png(frame, ph, path):
    base = Image.open(frame).convert("RGB").resize((W, H)).filter(ImageFilter.GaussianBlur(18))
    base = Image.blend(base, Image.new("RGB", (W, H), (12, 10, 14)), 0.55).convert("RGBA")
    d = ImageDraw.Draw(base)
    y = int(H * 0.27)
    ft = font(BOLD, 40)
    t = "CÂU HÔM NAY"
    d.text(((W - d.textlength(t, font=ft)) / 2, y), t, font=ft, fill=(255, 255, 255, 200))
    y += 90
    fp = font(SERIF, 92)
    for r in wrap(ph["en"], fp, W * 0.86, d):
        outlined(d, ((W - d.textlength(r, font=fp)) / 2, y), r, fp, YELLOW, 4)
        y += 110
    fv = font(BOLD, 58)
    for r in wrap("= " + ph["vi"], fv, W * 0.86, d):
        d.text(((W - d.textlength(r, font=fv)) / 2, y + 10), r, font=fv, fill=WHITE)
        y += 74
    y += 60
    fe, fx = font(BOLD, 46), font(REG, 40)
    for r in wrap(ph["example_en"], fe, W * 0.82, d):
        d.text(((W - d.textlength(r, font=fe)) / 2, y), r, font=fe, fill=WHITE)
        y += 60
    for r in wrap(ph["example_vi"], fx, W * 0.82, d):
        d.text(((W - d.textlength(r, font=fx)) / 2, y + 6), r, font=fx, fill=(220, 220, 220))
        y += 54
    fs = font(BOLD, 40)
    t = "Follow để học 1 câu mỗi ngày"
    d.rounded_rectangle(((W - d.textlength(t, font=fs)) / 2 - 36, H * 0.70, (W + d.textlength(t, font=fs)) / 2 + 36,
                         H * 0.70 + 78), 39, fill=(214, 40, 60, 240))
    d.text(((W - d.textlength(t, font=fs)) / 2, H * 0.70 + 16), t, font=fs, fill=WHITE)
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
    card = ov / "card.png"
    card_png(last, sc["phrase"], card)
    hook_png(sc["hook_vi"], ov / "hook.png")
    handle_png(ov / "handle.png")
    for i, c in enumerate(cues):
        caption_png(c[2], c[3], sc["phrase"]["en"], ov / f"cap{i}.png")
    card_len = 3.0
    end = total + card_len
    inputs = ["-i", str(film), "-loop", "1", "-t", f"{card_len}", "-i", str(card),
              "-i", str(ov / "hook.png"), "-i", str(ov / "handle.png")]
    inputs += sum((["-i", str(ov / f"cap{i}.png")] for i in range(len(cues))), [])
    fc = [f"[1:v]fps={FPS},format=yuv420p,setsar=1[card]",
          "[0:v][card]concat=n=2:v=1:a=0[v0]",
          f"[v0][2:v]overlay=enable='lt(t,2.8)'[v1]",
          f"[v1][3:v]overlay=enable='lt(t,{total:.3f})'[v2]"]
    cur = "v2"
    for i, (s, e, *_ ) in enumerate(cues):
        nxt = cues[i + 1][0] if i + 1 < len(cues) else total
        fc.append(f"[{cur}][{4 + i}:v]overlay=enable='between(t,{max(0, s):.3f},{min(e + 0.4, nxt, total):.3f})'[c{i}]")
        cur = f"c{i}"
    fc.append(f"[0:a]apad=whole_dur={end:.3f}[a0]")
    amap = "[a0]"
    music = os.environ.get("MUSIC")
    if music:
        inputs += ["-stream_loop", "-1", "-i", music]
        mi = 4 + len(cues)
        fc.append(f"[{mi}:a]atrim=0:{end:.3f},volume={os.environ.get('MUSIC_DB', '-24')}dB,"
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
