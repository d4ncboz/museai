"""Bẫy Hán-Việt overlays: name tags, the trap stamp freeze, truth card, A/B poll, next-episode teaser.

Usage (from .claude/skills/hanviet-trap/, with plan.json from trap.py brief):
  uv run --no-project --python 3.12 --with pillow python scripts/fx.py apply video.mp4 plan.json out.mp4 \\
      --tags 0.1,3.2 --stamp 5.1 --truth 6.9,10.4 --poll 21.4,27 [--teaser 25.5]
  uv run --no-project --python 3.12 --with pillow python scripts/fx.py board plan.json board.png [still.png]

apply: times are on video.mp4's timeline (dubbed cues). --stamp T freezes the frame at T (end of the
misreading line) for STAMP s with the red BẪY HÁN-VIỆT stamp, the Hán-Việt card (red ✗) and a scratch +
boom sound, then the video goes on; later windows shift by STAMP by themselves. Run after captions and
cards, before hook.py (the hook sits in the top band from frame 0, the tags under the faces).
board: the five key frames side by side (hook + tags, misreading, stamp, truth, poll) on still.png or a
placeholder set, so the user can judge the look before any render.
"""
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
STAMP = 1.6
ZH = ("/System/Library/AssetsV2/com_apple_MobileAsset_Font8/86ba2c91f017a3749571a82f2c6d890ac7ffb2fb"
      ".asset/AssetData/PingFang.ttc")
AVENIR = "/System/Library/Fonts/Avenir Next.ttc"
RED, GREEN, GOLD, INK = (232, 40, 52), (24, 176, 96), (255, 205, 60), (20, 20, 28)
TONE_COLORS = {1: (255, 92, 92), 2: (255, 176, 46), 3: (88, 214, 120), 4: (84, 170, 255), 0: (255, 255, 255)}
TONES = {c: t for t, cs in enumerate(("āēīōūǖĀĒĪŌŪǕ", "áéíóúǘÁÉÍÓÚǗ", "ǎěǐǒǔǚǍĚǏǑǓǙ", "àèìòùǜÀÈÌÒÙǛ"), 1) for c in cs}


def avenir(size, style="Bold"):  # Heavy has no Vietnamese glyphs
    for i in range(16):
        try:
            f = ImageFont.truetype(AVENIR, size, index=i)
        except OSError:
            break
        if f.getname()[1] == style:
            return f
    return ImageFont.truetype(AVENIR, size)


def zh(size, weight=11):  # PingFang SC Semibold
    return ImageFont.truetype(ZH, size, index=weight)


def cjk(c):
    return ord(c) >= 0x2E80  # Vietnamese letters sit below (U+1EA0-1EF9)


def runs(text):
    out = []
    for c in text:
        if out and cjk(out[-1][1][-1]) == cjk(c):
            out[-1][1] += c
        else:
            out.append([cjk(c), c])
    return out


def mlen(text, f):
    """width of mixed Vietnamese/Chinese text: hanzi in PingFang, the rest in f"""
    return sum((zh(f.size) if k else f).getlength(t) for k, t in runs(text))


def mdraw(d, x, y, text, f, **kw):
    for k, t in runs(text):
        g = zh(f.size) if k else f
        d.text((x, y - (f.size * 0.12 if k else 0)), t, font=g, **kw)
        x += g.getlength(t)


def fit(make, size, text, width):
    while size > 18 and mlen(text, make(size)) > width:
        size -= 2
    return make(size)


def star(d, cx, cy, r, fill):
    pts = [(cx + (r if i % 2 == 0 else r * 0.4) * math.sin(i * math.pi / 5),
            cy - (r if i % 2 == 0 else r * 0.4) * math.cos(i * math.pi / 5)) for i in range(10)]
    d.polygon(pts, fill=fill)


def flag(d, x, y, w, kind):
    h = int(w * 2 / 3)
    d.rounded_rectangle((x, y, x + w, y + h), 6, fill=(218, 37, 29))
    if kind == "VN":
        star(d, x + w / 2, y + h / 2, h * 0.36, (255, 222, 0))
    else:
        star(d, x + w * 0.22, y + h * 0.3, h * 0.2, (255, 222, 0))
        for dx, dy in ((0.42, 0.12), (0.5, 0.25), (0.5, 0.42), (0.42, 0.55)):
            star(d, x + w * dx, y + h * dy, h * 0.07, (255, 222, 0))
    return h


def shadowed(layer, blur=14, alpha=110):
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sh.paste((0, 0, 0, alpha), mask=layer.split()[3])
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    out.alpha_composite(sh, (0, 8))
    out.alpha_composite(layer)
    return out


def pinyin_line(d, x, y, text, f):
    """tone-coloured pinyin, the same scheme as muse-video burn_subs.py"""
    for word in text.split(" "):
        t = next((TONES[c] for c in word if c in TONES), 0)
        d.text((x, y), word, font=f, fill=TONE_COLORS[t], stroke_width=4, stroke_fill=(0, 0, 0))
        x += f.getlength(word + " ")


def tag(t, left):
    """character intro lower third: flag, name, role; white card with a coloured edge"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    nf = fit(lambda z: avenir(z), 50, t["name"], 330)
    rf = avenir(30, "Demi Bold")
    w = int(max(nf.getlength(t["name"]), rf.getlength(t["role"]))) + 150
    x = 48 if left else W - 48 - w
    y = 940
    edge = RED if t["flag"] == "CN" else GOLD
    d.rounded_rectangle((x, y, x + w, y + 130), 26, fill=(255, 255, 255, 240))
    d.rounded_rectangle((x, y, x + 14, y + 130), 7, fill=edge)
    flag(d, x + 34, y + 34, 62, t["flag"])
    d.text((x + 114, y + 16), t["name"], font=nf, fill=INK)
    d.text((x + 114, y + 80), t["role"], font=rf, fill=(110, 110, 120))
    return shadowed(layer)


def stamp_card(s):
    """BẪY HÁN-VIỆT rubber stamp + the misreading card"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    st = Image.new("RGBA", (900, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(st)
    f = fit(lambda z: avenir(z), 120, "BẪY HÁN-VIỆT!", 760)
    d.rounded_rectangle((20, 40, 880, 260), 30, outline=RED, width=16)
    d.rounded_rectangle((44, 64, 856, 236), 18, outline=RED, width=5)
    tw = f.getlength("BẪY HÁN-VIỆT!")
    d.text(((900 - tw) / 2, 82), "BẪY HÁN-VIỆT!", font=f, fill=RED)
    st = st.rotate(-8, resample=Image.BICUBIC, expand=True)
    layer.alpha_composite(st, ((W - st.width) // 2, 330))
    d = ImageDraw.Draw(layer)
    x0, y0, x1 = 120, 760, W - 120
    d.rounded_rectangle((x0, y0, x1, y0 + 420), 40, fill=(255, 255, 255, 245))
    big = zh(150)
    tw = big.getlength(s["zh"])
    d.text(((W - tw) / 2 - 60, y0 + 40), s["zh"], font=big, fill=INK)
    d.text(((W + tw) / 2 - 20, y0 + 70), "≠", font=avenir(120), fill=RED)
    hv = fit(lambda z: avenir(z), 84, s["hv"], x1 - x0 - 200)
    hw = hv.getlength(s["hv"])
    hy = y0 + 250
    d.text(((W - hw) / 2, hy), s["hv"], font=hv, fill=RED)
    d.line(((W - hw) / 2 - 16, hy + 60, (W + hw) / 2 + 16, hy + 50), fill=RED, width=10)
    d.text((x0 + 36, y0 + 30), "Hán-Việt", font=avenir(36, "Demi Bold"), fill=(150, 150, 160))
    return shadowed(layer)


def truth(t):
    """the real meaning: compact green check card above the heads, the misreading crossed out under it"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0, x1, y1 = 90, 60, W - 90, 330
    d.rounded_rectangle((x0, y0, x1, y1), 36, fill=(255, 255, 255, 245))
    d.rounded_rectangle((x0, y0, x1, y0 + 14), 7, fill=GREEN)
    big = zh(96)
    d.text((x0 + 44, y0 + 26), t["zh"], font=big, fill=INK)
    d.text((x0 + 64 + big.getlength(t["zh"]), y0 + 66), t["py"], font=avenir(48, "Demi Bold"), fill=(90, 90, 100))
    d.ellipse((x0 + 44, y0 + 164, x0 + 100, y0 + 220), fill=GREEN)
    d.line(((x0 + 57, y0 + 193), (x0 + 69, y0 + 207), (x0 + 89, y0 + 178)), fill="white", width=8)
    real = fit(lambda z: avenir(z), 60, t["real"], x1 - x0 - 160)
    d.text((x0 + 118, y0 + 158), t["real"], font=real, fill=GREEN)
    no = fit(lambda z: avenir(z, "Medium"), 34, "không phải: " + t["assumed"], x1 - x0 - 160)
    d.text((x0 + 118, y0 + 226), "không phải: " + t["assumed"], font=no, fill=(160, 160, 168))
    return shadowed(layer)


def poll(p):
    """ending quiz as an A/B poll above the bottom UI band, the comment prompt under it"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    x0, y0, x1 = 80, 1040, W - 80
    d.rounded_rectangle((x0, y0, x1, y0 + 470), 40, fill=(255, 255, 255, 245))
    q = fit(lambda z: zh(z), 92, p["zh"], x1 - x0 - 80)
    qw = q.getlength(p["zh"])
    d.text(((W - qw) / 2, y0 + 30), p["zh"], font=q, fill=INK)
    pf = avenir(44, "Demi Bold")
    pinyin_line(d, (W - pf.getlength(p["py"])) / 2, y0 + 150, p["py"], pf)
    for i, (k, v, c) in enumerate((("A", p["a"], RED), ("B", p["b"], (40, 120, 230)))):
        bx = x0 + 30 + i * ((x1 - x0 - 60) // 2 + 10)
        bw = (x1 - x0 - 60) // 2 - 10
        d.rounded_rectangle((bx, y0 + 240, bx + bw, y0 + 340), 50, fill=c)
        f = fit(lambda z: avenir(z), 50, f"{k}. {v}", bw - 50)
        d.text((bx + (bw - f.getlength(f"{k}. {v}")) / 2, y0 + 262), f"{k}. {v}", font=f, fill="white")
    cf = avenir(46)
    c = "Comment A hay B nhé"
    d.text(((W - cf.getlength(c)) / 2, y0 + 380), c, font=cf, fill=INK)
    return shadowed(layer)


def teaser(text):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = avenir(50)
    w = int(mlen(text, f)) + 80
    x, y = (W - w) // 2, 1560
    d.rounded_rectangle((x, y, x + w, y + 96), 48, fill=(*GOLD, 250))
    mdraw(d, x + 40, y + 18, text, f, fill=INK)
    return shadowed(layer, 10, 90)


def hook_band(text):
    """what muse-video hook.py burns from frame 0 (preview only: the video uses hook.py itself)"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = fit(lambda z: avenir(z), 64, text, 860)
    tw = mlen(text, f)
    x = (W - tw) / 2
    d.rounded_rectangle((x - 30, 150, x + tw + 30, 260), 22, fill=RED)
    mdraw(d, x, 166, text, f, fill="white")
    sub = "Cuối video có câu hỏi cho bạn!"
    sf = avenir(38, "Demi Bold")
    d.text(((W - sf.getlength(sub)) / 2, 278), sub, font=sf, fill=GOLD, stroke_width=4, stroke_fill=(0, 0, 0))
    return layer


def caption(line):
    """three-line zh / pinyin / vi caption as burn_subs.py draws it (preview only)"""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    _, z, p, v = line
    zf = fit(lambda s: zh(s), 104, z, 880)
    d.text(((W - zf.getlength(z)) / 2, 1200), z, font=zf, fill="white", stroke_width=8, stroke_fill=(0, 0, 0))
    pf = fit(lambda s: ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", s), 60, p, 880)
    pinyin_line(d, (W - pf.getlength(p)) / 2, 1340, p, pf)
    vf = fit(lambda s: ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", s), 56, v, 900)
    mdraw(d, (W - mlen(v, vf)) / 2, 1430, v, vf, fill="white", stroke_width=6, stroke_fill=(0, 0, 0))
    return layer


def placeholder_set(solo=False):
    """warm blurred restaurant and two soft figures, for a board made before any still exists"""
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H
        d.line(((0, y), (W, y)), fill=(int(120 - 70 * k), int(46 - 20 * k), int(38 - 18 * k)))
    for cx, cy, r in ((180, 260, 70), (520, 180, 55), (880, 300, 80), (700, 520, 40)):
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 140, 60))
    im = im.filter(ImageFilter.GaussianBlur(40))
    d = ImageDraw.Draw(im)
    people = [(W // 2, (250, 250, 255))] if solo else [(330, (250, 250, 255)), (760, (150, 40, 40))]
    for cx, dress in people:
        d.ellipse((cx - 115, 470, cx + 115, 740), fill=(236, 200, 176))
        d.ellipse((cx - 135, 420, cx + 135, 620), fill=(28, 22, 22))
        d.rounded_rectangle((cx - 190, 760, cx + 190, 1920), 140, fill=dress)
    return im.filter(ImageFilter.GaussianBlur(3))


def frame(bg, *layers):
    im = bg.convert("RGBA")
    for lay in layers:
        im.alpha_composite(lay)
    return im


def stamp_frame(base, k):
    """k in [0, 1] over the freeze: slow push-in, red-tinted dim, stamp pops in over the first 0.2 s"""
    z = 1 + 0.06 * k
    im = base.resize((int(W * z), int(H * z)), Image.BICUBIC)
    im = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))
    im = Image.blend(im.convert("RGB"), Image.new("RGB", (W, H), (60, 0, 8)), 0.45).convert("RGBA")
    return im


def board(plan, out, still=None):
    bg = Image.open(still).convert("RGB").resize((W, H)) if still else placeholder_set()
    # clip C is Linh alone: on a real two-shot still, a 9:16 crop around screen-left
    solo = bg.crop((60, 250, 660, 1317)).resize((W, H), Image.LANCZOS) if still else placeholder_set(solo=True)
    cues = plan["cues"]
    first = cues[0] if plan["speaker"] == "partner" else cues[1]
    misread = cues[1] if plan["speaker"] == "partner" else cues[2]
    explain = next(c for c in cues if plan["truth"]["zh"] in c[1] and c is not first and c is not misread)
    st = stamp_frame(frame(bg, caption(misread)), 0.5)
    st.alpha_composite(stamp_card(plan["stamp"]))
    panels = [
        ("0.0s HOOK + NHÂN VẬT", frame(bg, caption(first), tag(plan["tags"][0], True), tag(plan["tags"][1], False),
                                       hook_band(plan["hook"]))),
        ("2.5s HIỂU NHẦM", frame(bg, caption(misread))),
        ("4.5s FREEZE + STAMP", st),
        ("6.5s NGHĨA THẬT", frame(bg, caption(explain), truth(plan["truth"]))),
        ("ENDING: ĐỐ VUI", frame(solo, poll(plan["poll"]), teaser(plan["teaser"]) if plan["teaser"] else
                                  Image.new("RGBA", (W, H)))),
    ]
    pw, ph, gap, top = 432, 768, 24, 90
    sheet = Image.new("RGB", (len(panels) * (pw + gap) + gap, ph + top + gap), (24, 24, 30))
    d = ImageDraw.Draw(sheet)
    lf = avenir(34)
    for i, (label, im) in enumerate(panels):
        x = gap + i * (pw + gap)
        sheet.paste(im.convert("RGB").resize((pw, ph), Image.LANCZOS), (x, top))
        d.text((x, 30), label, font=lf, fill=(240, 240, 240))
    sheet.save(out)
    for i, (_, im) in enumerate(panels):
        im.convert("RGB").save(Path(out).with_name(f"{Path(out).stem}_{i + 1}.png"))
    print(f"wrote {out} + {len(panels)} full-size panels")


def run(*a):
    subprocess.run(a, check=True, capture_output=True)


def probe_fps(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "csv=p=0", video], capture_output=True, text=True, check=True).stdout.strip()
    n, d = r.split("/")
    return float(n) / float(d)


def apply(video, plan, out, tags, stamp, truth_w, poll_w, teaser_at):
    tmp = Path(tempfile.mkdtemp())
    fps = probe_fps(video)
    # 1. the freeze: still frames with the stamp, a scratch + boom under them
    run("ffmpeg", "-y", "-v", "error", "-ss", f"{stamp}", "-i", video, "-frames:v", "1", str(tmp / "f.png"))
    base = Image.open(tmp / "f.png").convert("RGB").resize((W, H))
    card = stamp_card(plan["stamp"])
    n = int(STAMP * fps)
    pop = int(0.2 * fps)
    for i in range(n):
        im = stamp_frame(base, i / n)
        s = 1.8 - 0.8 * min(1, i / pop) if pop else 1
        c = card.resize((int(W * s), int(H * s)), Image.BICUBIC).crop(
            (int((W * s - W) / 2), int((H * s - H) / 2), int((W * s - W) / 2) + W, int((H * s - H) / 2) + H))
        im.alpha_composite(c)
        im.convert("RGB").save(tmp / f"s{i:03d}.png")
    sfx = ("(0.35*sin(2*PI*(900*t-1500*t*t))+0.2*(random(0)*2-1))*exp(-8*t)*lt(t,0.3)"
           "+0.7*sin(2*PI*55*t)*exp(-3*(t-0.15))*gt(t,0.15)")
    run("ffmpeg", "-y", "-v", "error", "-framerate", f"{fps}", "-i", str(tmp / "s%03d.png"),
        "-f", "lavfi", "-t", f"{STAMP}", "-i", f"aevalsrc='{sfx}':s=48000:c=stereo",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(tmp / "stamp.mp4"))
    for name, args in (("a", ["-t", f"{stamp}"]), ("b", ["-ss", f"{stamp}"])):
        run("ffmpeg", "-y", "-v", "error", "-i", video, *args, "-vf", f"scale={W}:{H}", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-ac", "2", str(tmp / f"{name}.mp4"))
    (tmp / "list.txt").write_text("".join(f"file '{tmp / x}.mp4'\n" for x in ("a", "stamp", "b")))
    run("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
        "-c", "copy", str(tmp / "joined.mp4"))

    # 2. overlays on the joined timeline (windows after the freeze move by STAMP)
    def shift(t):
        return t + STAMP if t >= stamp else t

    layers = [(tag(plan["tags"][0], True), tags), (tag(plan["tags"][1], False), tags),
              (truth(plan["truth"]), truth_w), (poll(plan["poll"]), poll_w)]
    if plan.get("teaser") and teaser_at is not None:
        layers.append((teaser(plan["teaser"]), (teaser_at, 1e4)))
    inputs, chain, last = [], [], "0:v"
    for i, (im, (a, b)) in enumerate(layers):
        p = tmp / f"o{i}.png"
        im.save(p)
        inputs += ["-loop", "1", "-i", str(p)]
        a, b = shift(a), shift(b)
        # slide 60 px up and fade in over 0.25 s
        chain.append(f"[{i + 1}:v]format=rgba,fade=in:st={a}:d=0.25:alpha=1,fade=out:st={b - 0.2}:d=0.2:alpha=1[l{i}]")
        chain.append(f"[{last}][l{i}]overlay=0:'if(lt(t,{a}+0.25),60*(1-(t-{a})/0.25),0)':"
                     f"enable='between(t,{a},{b})':shortest=1[v{i}]")
        last = f"v{i}"
    run("ffmpeg", "-y", "-v", "error", "-i", str(tmp / "joined.mp4"), *inputs, "-filter_complex", ";".join(chain),
        "-map", f"[{last}]", "-map", "0:a", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p",
        "-c:a", "copy", out)
    print(f"wrote {out} (+{STAMP}s freeze at {stamp}s; later cue times move by {STAMP}s)")


def window(s):
    a, b = s.split(",")
    return float(a), float(b)


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "board":
        board(json.loads(Path(sys.argv[2]).read_text()), sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    elif cmd == "apply":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("video"), ap.add_argument("plan"), ap.add_argument("out")
        ap.add_argument("--tags", type=window, required=True)
        ap.add_argument("--stamp", type=float, required=True)
        ap.add_argument("--truth", type=window, required=True)
        ap.add_argument("--poll", type=window, required=True)
        ap.add_argument("--teaser", type=float)
        a = ap.parse_args(sys.argv[2:])
        apply(a.video, json.loads(Path(a.plan).read_text()), a.out, a.tags, a.stamp, a.truth, a.poll, a.teaser)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
