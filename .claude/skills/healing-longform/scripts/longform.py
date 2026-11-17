"""Compose a 5-15 min 16:9 healing day: one shot per beat (or per cut), sparse voice-over, chapter cards, 1 s dissolves,
the clips' own sound as a continuous bed, a real rain bed under rainy beats, soft piano ducked under the voice.

  python3 longform.py story.json --music music.m4a --out healing-<slug>.mp4 [--dry]

Per beat: sN.mp4 when it exists, else stills/sN.png as a slow push-in (so a cut can be watched while
clips are still missing). A beat lasts LEAD + voice + GAP (a beat with no voice: HOLD s: the breathing
shots). Chapter beats (`"chapter": true`) carry the chapter card; the first one also the film's title.
Subtitles, grade and the stem levels come from ../healing-video/scripts/story169.py.

Fast cutting (field-to-table): story `xf` sets the dissolve (0.3-0.5 s); a beat's `cuts`
[[start, secs, zoom, x, y], ...] cuts one take into several shots (zoom 1.3 at x/y = a punch-in, like a second
camera); story `teaser` {"text", "text_secs", "shots": [[beat, start, secs, zoom?, x?, y?], ...]} is a cold open
of the best moments with a hook line, before the first chapter card. A beat with `cuts` has no voice.
"""
import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HV = Path(__file__).resolve().parents[2] / "healing-video" / "scripts"
sys.path.insert(0, str(HV))
from story169 import FPS, LNORM, H, W, chunks, dur, has_audio, luma, run, sub_png  # noqa: E402

XF = 1.0  # dissolve: longer than story mode's 0.6 s, the long form never hurries
LEAD, HOOK_LEAD, GAP, HOLD, TAIL = 1.4, 0.4, 2.6, 8.0, 4.0
CARD_IN, CARD_HOLD = 0.9, 4.2  # chapter card fades in after 0.9 s and stays 4.2 s
ITALIC = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
REGULAR = "/System/Library/Fonts/Supplemental/Georgia.ttf"
RAIN = Path("/Applications/iMovie.app/Contents/Resources/iMovie Sound Effects/Hard Rain.mp3")
RAIN_FILTER = "highpass=f=200,lowpass=f=3200,lowpass=f=3200,stereotools=slev=0.35,aecho=0.8:0.5:28|61:0.22|0.12"


def card_png(lines, path):
    """Chapter card: small cream italic serif, centred a little above the middle, soft shadow, no band."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sizes = [(ITALIC, 64), (REGULAR, 40), (ITALIC, 34)][-len(lines):] if len(lines) == 3 else [(REGULAR, 40), (ITALIC, 34)]
    fonts = [ImageFont.truetype(f, s) for f, s in sizes]
    heights = [int(s * 1.5) for _, s in sizes]
    y0 = int(H * 0.40) - sum(heights) // 2
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    y = y0
    for ln, f, h in zip(lines, fonts, heights, strict=True):
        ds.text(((W - ds.textlength(ln, font=f)) / 2, y + 2), ln, font=f, fill=(0, 0, 0, 170))
        y += h
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(img)
    y = y0
    for ln, f, h in zip(lines, fonts, heights, strict=True):
        d.text(((W - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=(250, 244, 230, 255))
        y += h
    img.save(path)


def hook_png(text, path):
    """Cold-open line: one or two lines of cream italic in the lower third, like a vlogger's own caption."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    f = ImageFont.truetype(ITALIC, 52)
    d = ImageDraw.Draw(img)
    lines, cur = [], ""
    for w_ in text.split():
        t_ = f"{cur} {w_}".strip()
        if d.textlength(t_, font=f) > W * 0.62 and cur:
            lines.append(cur)
            cur = w_
        else:
            cur = t_
    lines.append(cur)
    y0 = int(H * 0.74) - 36 * (len(lines) - 1)
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ds = ImageDraw.Draw(sh)
    for k, ln in enumerate(lines):
        ds.text(((W - ds.textlength(ln, font=f)) / 2, y0 + k * 72 + 2), ln, font=f, fill=(0, 0, 0, 190))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(6)))
    d = ImageDraw.Draw(img)
    for k, ln in enumerate(lines):
        d.text(((W - d.textlength(ln, font=f)) / 2, y0 + k * 72), ln, font=f, fill=(250, 244, 230, 255))
    img.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("story")
    ap.add_argument("--music", required=True, help="track, or 'none'")
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--fresh", action="store_true", help="rebuild every segment (else segments on disk are reused)")
    a = ap.parse_args()
    sp = Path(a.story).resolve()
    root = sp.parent
    story = json.loads(sp.read_text())
    beats, chapters = story["beats"], {c["n"]: c for c in story["chapters"]}
    tmp = root / "build"
    tmp.mkdir(exist_ok=True)

    global XF
    XF = float(story.get("xf", XF))  # a fast-cut film (field-to-table) uses 0.3-0.5 s
    teaser = story.get("teaser")
    # one shot per entry: the cold open (teaser shots), then each beat, or each of its `cuts`
    # (cuts: [[start, secs, zoom, x, y], ...]: one take cut twice, wide then a punch-in, like a two-camera edit)
    shots = [(bn, dict(start=st, hold=secs, zoom=(rest or [1.0])[0], x=(rest[1:] or [0.5])[0],
                       y=(rest[2:] or [0.5])[0]), True) for bn, st, secs, *rest in (teaser or {}).get("shots", [])]
    for bn, b in enumerate(beats, 1):
        cuts = b.get("cuts") or [[b.get("start", 0.4), b.get("hold", HOLD)]]
        shots += [(bn, dict(start=c[0], hold=c[1], zoom=(c[2:] or [1.0])[0], x=(c[3:] or [0.5])[0],
                            y=(c[4:] or [0.5])[0], first=k == 0), False) for k, c in enumerate(cuts)]
    plan, t, first_card = [], 0.0, True
    for i, (bn, cut, tease) in enumerate(shots, 1):
        b = beats[bn - 1]
        own = not tease and cut.get("first") and not b.get("cuts")  # voice only on an uncut beat
        vo = root / "vo" / f"b{bn}.wav"
        vd = dur(vo) if own and b.get("vo") else 0.0
        lead = HOOK_LEAD if i == 1 else LEAD
        L = (lead + vd + GAP) if vd else float(cut["hold"])
        L += TAIL if i == len(shots) else 0
        clip = root / b.get("clip", f"s{bn}.mp4")
        src = clip if clip.exists() else root / "stills" / f"s{bn}.png"
        card = None
        if b.get("chapter") and not tease and cut.get("first"):
            c = chapters[b["ch"]]
            card = ([story["title"]] if first_card else []) + [c["title"], c["sub"]]
            first_card = False
        plan.append(dict(i=i, bn=bn, b=b, src=src, still=src.suffix == ".png", vo=vo if vd else None, vd=vd,
                         lead=lead, L=L, T=t, card=card, cut=cut, foley_db=float(b.get("foley_db", 0))))
        t += L
    total = t
    stills = [p["i"] for p in plan if p["still"]]
    print(f"{len(plan)} beats, {total:.1f} s ({total / 60:.2f} min); stills for beats: {stills or '-'}")
    missing = [p["src"] for p in plan if not p["src"].exists()]
    if a.dry or missing:
        for p in plan:
            print(f"{p['i']:>3} b{p['bn']:>2} ch{p['b']['ch']} T={p['T']:6.1f} L={p['L']:4.1f} vo={p['vd']:4.1f} "
                  f"{'STILL' if p['still'] else 'clip '} {'CARD' if p['card'] else ''}")
        if missing:
            sys.exit(f"missing: {', '.join(map(str, missing))}")
        return

    # 1. one graded segment per beat (+ subtitles, + chapter card), and its own sound
    for p in plan:
        i, need = p["i"], p["L"] + (XF if p["i"] < len(plan) else 0)
        seg, fol = tmp / f"seg{i}.mp4", tmp / f"fol{i}.wav"
        key = tmp / f"seg{i}.key"
        stamp = f"{p['src']}:{p['src'].stat().st_mtime}:{need:.3f}:{p['b'].get('vo')}:{p['card']}:{p['cut']}"
        if not a.fresh and seg.exists() and fol.exists() and key.exists() and key.read_text() == stamp:
            p["seg"], p["fol"] = seg, fol
            continue
        overlays, inputs = [], []
        if p["vo"]:
            pages = chunks(p["b"]["vo"])
            total_c = sum(len(x) for x in pages)
            t0, span = p["lead"] - 0.1 + (XF / 2 if i > 1 else 0), p["vd"] + 0.2
            for k, pg in enumerate(pages):
                png = tmp / f"sub{i}_{k}.png"
                sub_png(pg, png)
                d = span * len(pg) / total_c
                overlays.append((png, t0, t0 + d, 0.25))
                t0 += d
        if p["card"]:
            png = tmp / f"card{i}.png"
            card_png(p["card"], png)
            c0 = CARD_IN + (XF / 2 if i > 1 else 0)
            overlays.append((png, c0, min(c0 + CARD_HOLD, p["L"] - 0.2), 0.9))  # a short cut ends the card early
        for png, *_ in overlays:
            inputs += ["-loop", "1", "-t", f"{need:.3f}", "-i", str(png)]
        grade = "eq=gamma={g:.3f}:saturation=0.96:contrast=1.01,colorbalance=rs=0.015:gs=0.01:bs=-0.02,noise=alls=4:allf=t"
        cz = p["cut"]
        zoom = "" if cz["zoom"] <= 1.0 else (
            f"crop=iw/{cz['zoom']}:ih/{cz['zoom']}:'min(max(0,{cz['x']}*iw-iw/{cz['zoom']}/2),iw-iw/{cz['zoom']})'"
            f":'min(max(0,{cz['y']}*ih-ih/{cz['zoom']}/2),ih-ih/{cz['zoom']})',scale={W}:{H}:flags=lanczos,")
        if p["still"]:
            # slow push-in from a 4K upscale (no zoompan jitter): 1.00 -> 1.05 over the beat
            frames = int(need * FPS) + 1
            vf = (f"[0:v]scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,"
                  f"zoompan=z='1+0.05*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},{zoom}"
                  f"{grade.format(g=1.0)},trim=duration={need:.3f}[v0]")
            src_in = ["-loop", "1", "-t", f"{need + 0.5:.3f}", "-i", str(p["src"])]
            f = 1.0
        else:
            cd = dur(p["src"])
            st = min(float(p["cut"]["start"]), max(0.0, cd - need))
            f = max(1.0, need / (cd - st))
            if f > 1.45:  # never slower than ~0.7x: the clip's head is used whole
                st, f = 0.0, need / cd
            y = luma(p["src"], st)
            g = min(1.5, math.log(max(y, 20) / 255) / math.log(130 / 255)) if y < 125 else 1.0
            vf = (f"[0:v]trim=start={st:.3f},setpts=(PTS-STARTPTS)*{f:.4f},fps={FPS},"
                  f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{zoom}{grade.format(g=g)},"
                  f"trim=duration={need:.3f}[v0]")
            src_in = ["-i", str(p["src"])]
            p["st"] = st
        last = "v0"
        for k, (_, a0, a1, fd) in enumerate(overlays):
            vf += (f";[{k + 1}:v]format=rgba,fade=in:st={a0:.2f}:d={fd}:alpha=1,"
                   f"fade=out:st={a1 - fd:.2f}:d={fd}:alpha=1[o{k}];[{last}][o{k}]overlay=0:0:"
                   f"enable='between(t,{a0:.2f},{a1:.2f})'[w{k}]")
            last = f"w{k}"
        run(["ffmpeg", "-y", "-hide_banner", *src_in, *inputs, "-filter_complex", vf, "-map", f"[{last}]", "-an",
             "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(seg)])
        p["f"] = f
        p["seg"], p["fol"] = seg, fol
        foley_src(p, plan, need, fol)
        key.write_text(stamp)
        print(f"seg {i} ok ({'still' if p['still'] else f'clip x{1 / f:.2f}'})", flush=True)

    # 2. video with dissolves; a long fade to black at the end
    ins, fc, last, off = [], "", "0:v", 0.0
    for p in plan:
        ins += ["-i", str(p["seg"])]
    for k in range(1, len(plan)):
        off += plan[k - 1]["L"]
        fc += f"[{last}][{k}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[x{k}];"
        last = f"x{k}"
    if teaser and teaser.get("text"):
        # the cold open's hook line: small cream italic over the first teaser shots, then the title card follows
        png = tmp / "hook.png"
        hook_png(teaser["text"], png)
        h1 = float(teaser.get("text_secs", 4.5))
        ins += ["-loop", "1", "-t", f"{h1 + 1:.3f}", "-i", str(png)]
        fc += (f"[{len(plan)}:v]format=rgba,fade=in:st=0.4:d=0.6:alpha=1,fade=out:st={h1 - 0.6:.2f}:d=0.6:alpha=1[hk];"
               f"[{last}][hk]overlay=0:0:enable='between(t,0.4,{h1:.2f})'[hko];")
        last = "hko"
    fc += f"[{last}]fade=out:st={total - 3:.3f}:d=3[vout]"
    video = tmp / "video.mp4"
    run(["ffmpeg", "-y", "-hide_banner", *ins, "-filter_complex", fc, "-map", "[vout]", "-c:v", "libx264",
         "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS), str(video)])

    # 3. audio stems: voice, the clips' sound as one continuous bed, rain under rainy beats, music
    def place(files, delays, out, pre=""):
        if not files:  # a film with no narration (field-to-table): a silent stem, amix needs 1+ inputs
            run(["ffmpeg", "-y", "-hide_banner", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t",
                 f"{total:.3f}", str(out)])
            return
        ins_, fc_ = [], ""
        for k, (f_, d_) in enumerate(zip(files, delays, strict=True)):
            ins_ += ["-i", str(f_)]
            fc_ += f"[{k}:a]aresample=48000,aformat=channel_layouts=stereo,{pre}adelay={int(d_ * 1000)}:all=1[a{k}];"
        fc_ += "".join(f"[a{k}]" for k in range(len(files)))
        fc_ += f"amix=inputs={len(files)}:normalize=0,apad,atrim=duration={total:.3f}[o]"
        # -t caps the output: apad is infinite (story169: a 37-input mix once ran past atrim)
        run(["ffmpeg", "-y", "-hide_banner", *ins_, "-filter_complex", fc_, "-map", "[o]", "-t", f"{total:.3f}", str(out)])

    voiced = [p for p in plan if p["vo"]]
    voice = tmp / "voice.wav"
    place([p["vo"] for p in voiced], [p["T"] + p["lead"] + (XF / 2 if p["i"] > 1 else 0) for p in voiced], voice,
          pre="highpass=f=70,")
    foley = tmp / "foley.wav"
    place([p["fol"] for p in plan], [p["T"] for p in plan], foley)
    stems = [(voice, -19), (foley, -30)]
    rain_beats = [p for p in plan if "rain" in p["b"]["time"]]
    if rain_beats and RAIN.exists():
        r0, r1 = rain_beats[0]["T"], rain_beats[-1]["T"] + rain_beats[-1]["L"] + XF
        rain = tmp / "rain.wav"
        n = int((r1 - r0) // 7.3) + 2
        run(["ffmpeg", "-y", "-hide_banner", "-stream_loop", str(n), "-i", str(RAIN), "-af",
             f"atrim=0.3:{r1 - r0 + 0.3:.3f},asetpts=PTS-STARTPTS,{RAIN_FILTER},afade=in:d=3,"
             f"afade=out:st={r1 - r0 - 4:.3f}:d=4,aresample=48000,aformat=channel_layouts=stereo,"
             f"adelay={int(r0 * 1000)}:all=1,apad,atrim=duration={total:.3f}", "-t", f"{total:.3f}", str(rain)])
        stems.append((rain, -33))
    for stem, lufs in stems:
        if stem == voice and not voiced:  # silence: loudnorm measures -inf and fails; the silent stem is the result
            run(["ffmpeg", "-y", "-hide_banner", "-i", str(voice), str(voice.with_suffix(".n.m4a"))])
            continue
        run(["python3", LNORM, str(stem), str(stem.with_suffix(".n.m4a")), str(lufs)])
    music = tmp / "music.wav"
    if a.music == "none":
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{total:.3f}",
             str(music.with_suffix(".n.m4a"))])
    else:
        run(["ffmpeg", "-y", "-hide_banner", "-stream_loop", "-1", "-i", a.music, "-af",
             f"atrim=duration={total:.3f},afade=in:st=0.8:d=4,afade=out:st={total - 6:.3f}:d=6,aresample=48000,"
             "aformat=channel_layouts=stereo", str(music)])
        run(["python3", LNORM, str(music), str(music.with_suffix(".n.m4a")), "-25"])
    mix = tmp / "mix.wav"
    extra = len(stems) - 2
    ins_ = ["-i", str(foley.with_suffix(".n.m4a")), "-i", str(voice.with_suffix(".n.m4a")),
            "-i", str(music.with_suffix(".n.m4a"))] + (["-i", str(stems[2][0].with_suffix(".n.m4a"))] if extra else [])
    fc = ("[1:a]asplit=3[vsc][vsc2][vmix];[2:a][vsc]sidechaincompress=threshold=0.03:ratio=4:attack=80:release=1200[mduck];"
          "[0:a][vsc2]sidechaincompress=threshold=0.03:ratio=2.5:attack=60:release=900[fduck];"
          f"[fduck][vmix][mduck]{'[3:a]' if extra else ''}amix=inputs={3 + extra}:normalize=0[o]")
    run(["ffmpeg", "-y", "-hide_banner", *ins_, "-filter_complex", fc, "-map", "[o]", str(mix)])
    final_a = tmp / "final.m4a"
    run(["python3", LNORM, str(mix), str(final_a), "-16"])
    run(["ffmpeg", "-y", "-hide_banner", "-i", str(video), "-i", str(final_a), "-map", "0:v", "-map", "1:a", "-c:v",
         "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", a.out])
    print(f"wrote {a.out} ({dur(a.out):.1f} s)")


def foley_src(p, plan, need, out):
    """The beat's own clip sound; a still borrows the sound of the nearest clip of the same place and hour
    (a still has none, and a hole in the bed is heard at once)."""
    src, st, f = (p["src"], p.get("st", 0.0), p.get("f", 1.0)) if not p["still"] else (None, 0.0, 1.0)
    if src is None or not has_audio(src):
        same = [q for q in plan if not q["still"] and q["src"].exists() and q["b"]["where"] == p["b"]["where"]
                and q["b"]["time"] == p["b"]["time"]] or [q for q in plan if not q["still"] and q["src"].exists()]
        same.sort(key=lambda q: abs(q["i"] - p["i"]))
        src = same[0]["src"] if same else None
        st, f = 0.0, max(1.0, need / dur(src)) if src else 1.0
    if src is not None and has_audio(src):
        run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{st:.3f}", "-stream_loop", "2", "-i", str(src), "-af",
             f"atempo={max(1 / f, 0.5):.4f},atrim=duration={need:.3f},highpass=f=80,lowpass=f=9000,"
             f"volume={p['foley_db']:.1f}dB,acompressor=threshold=0.05:ratio=8:attack=5:release=200,"
             f"afade=in:d=0.6,afade=out:st={max(0, need - 0.9):.3f}:d=0.9", "-ar", "48000", "-ac", "2", str(out)])
    else:
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{need:.3f}", str(out)])


if __name__ == "__main__":
    main()
