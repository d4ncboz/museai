"""Assemble a healing video: short calm shots cut in order, soft small serif text, music over the
clips' own ambience (rain, birds, river).

Usage:
  python3 scripts/compose.py --idea idea.json --music track.m4a --out healing-<slug>.mp4 s1.mp4 s2.mp4@1.5 ...
  [--shot 1.2] [--text "override caption"] [--no-text] [--ambience 0.35]

Concepts (idea["concept"]):
  postcard (reference 1): 8 shots x 1.2 s, ONE caption on every shot ("the way I want to live:").
  ode      (reference 2): 6 shots x 1.6 s, one phrase of idea["lines"] per shot, the sentence runs on.
--shot overrides the seconds per shot (3-4 s for a slower, longer video). clip@start picks where in
the clip the window starts (default 1.0 s: muse's first second often settles). Hard cuts like both
references; the last shot fades out 0.5 s so the loop back to shot 1 is soft.
"""
import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Georgia.ttf"
XF = 0.35  # ambience cross-fade between shots (s)
AMB_LUFS = -30  # every clip's ambience is levelled to this before --ambience scales the bed
# Real recorded ambience beds. muse's own rain is spectrally flat hiss with no droplets (hv-0001:
# "not natural raining sounds"), so when the idea's sound has a recording here, the recording replaces
# the clips' sound. ~/.config/museai/ambience/<name>.(wav|mp3|m4a|flac) wins over the built-ins, so
# better field recordings can be dropped in. iMovie's sound effects are royalty-free in your own videos.
IMOVIE = Path("/Applications/iMovie.app/Contents/Resources/iMovie Sound Effects")
BEDS = {  # name: (words in idea["sound"], built-in file, usable start, usable end (s), filter)
    "rain": (("rain", "drizzle", "shower"), IMOVIE / "Hard Rain.mp3", 0.3, 8.6,
             "highpass=f=200,lowpass=f=3200,lowpass=f=3200,stereotools=slev=0.35,aecho=0.8:0.5:28|61:0.22|0.12"),
    # as a phone hears rain from inside a room: far, muffled (refs have almost nothing above 2.5 kHz),
    # narrow (one small mic) with the room's own short reflections
    "water": (("river", "stream", "brook", "lake", "water", "creek"), IMOVIE / "Water Lake.mp3", 0.5, 29.0,
              "highpass=f=80"),
    "crickets": (("cricket", "night"), IMOVIE / "Crickets.mp3", 0.2, None, "highpass=f=200"),
}
BED_XF = 1.0  # cross-fade when a recording loops to cover a longer video


def text_png(text, w, h, path):
    """Small white serif line slightly below centre with a soft shadow (both references)."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    font = ImageFont.truetype(FONT, int(w * 0.036))
    d = ImageDraw.Draw(img)
    tw = d.textlength(text, font=font)
    x, y = (w - tw) / 2, h * 0.55
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).text((x, y + 2), text, font=font, fill=(0, 0, 0, 150))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(4)))
    ImageDraw.Draw(img).text((x, y), text, font=font, fill=(255, 255, 255, 240))
    img.save(path)


def loudness(clip):
    """Integrated loudness (LUFS) of a clip's sound, None when it has none or is silent."""
    if not has_audio(clip):
        return None
    err = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", clip, "-map", "0:a", "-af", "ebur128",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    i = float(err.rsplit("I:", 1)[1].split("LUFS")[0])
    return i if i > -70 else None


def has_audio(clip):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                        "-of", "csv=p=0", clip], capture_output=True, text=True)
    return bool(r.stdout.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("clips", nargs="+", help="shot.mp4 or shot.mp4@start_seconds, in shot order")
    ap.add_argument("--idea", required=True, help="idea JSON (ideas.py next/show output)")
    ap.add_argument("--music", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shot", type=float, help="seconds per shot (default: 1.2 postcard, 1.6 ode)")
    ap.add_argument("--text", help="postcard: override the caption")
    ap.add_argument("--no-text", action="store_true")
    ap.add_argument("--ambience", type=float, default=0.35, help="clip ambience level under the music")
    ap.add_argument("--bed", help=f"ambience recording: {', '.join(BEDS)} or a file; 'clips' = the clips' own "
                    "sound (default: picked from the idea's sound)")
    ap.add_argument("--size", default="1080x1920")
    ap.add_argument("--dissolve", type=float, default=0, help="cross-dissolve seconds between shots (reference 4: 0.5); 0 = hard cuts")
    a = ap.parse_args()

    idea = json.loads(Path(a.idea).read_text())
    ode = idea.get("concept") == "ode"
    shot = a.shot or (1.6 if ode else 1.2)
    w, h = map(int, a.size.split("x"))
    n = len(a.clips)
    total = shot * n
    tmp = Path(tempfile.mkdtemp())
    # keep the clips' own frame rate (muse: 24): resampling to 30 repeats every 4th frame (qa smooth 13 %)
    fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=r_frame_rate",
                          "-of", "csv=p=0", path_of(a.clips[0])], capture_output=True, text=True).stdout.strip()

    if a.no_text:
        texts = [None] * n
    elif ode:
        lines = idea["lines"]
        texts = [lines[i] if i < len(lines) else None for i in range(n)]
    else:
        texts = [a.text or idea["caption"]] * n

    args, vf, af = ["ffmpeg", "-v", "error", "-y"], [], []
    for c in a.clips:
        path, _, start = c.partition("@")
        args += ["-ss", start or "1.0", "-t", f"{shot + a.dissolve:.3f}", "-i", path]
    bed = make_bed(a.bed, idea, total, tmp)
    if bed:
        args += ["-i", str(bed)]
    else:
        # the clips' own sound brought to one level and cross-faded into ONE continuous bed. Hard-cutting
        # it per shot made the level jump 10 dB every 1.2 s, which felt like stuttering / lagging.
        for c in a.clips:
            path, _, start = c.partition("@")
            args += ["-ss", start or "1.0", "-t", f"{shot + XF:.3f}", "-i", path]
    args += ["-i", a.music]
    mi = n + (1 if bed else n)
    pngs = []
    for i, t in enumerate(texts):
        if t:
            p = tmp / f"t{i}.png"
            text_png(t, w, h, p)
            args += ["-i", str(p)]
            pngs.append(mi + len(pngs) + 1)
        else:
            pngs.append(None)
    for i in range(n):
        # soft, muted grade: a little less contrast and saturation, faint warmth (both references)
        v = (f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps={fps},setsar=1,"
             f"eq=contrast=0.96:saturation=0.92:brightness=0.01,colorbalance=rm=0.02:bm=-0.02,"
             f"trim=duration={shot + a.dissolve:.3f},setpts=PTS-STARTPTS[v{i}]")
        vf.append(v)
        if pngs[i] is not None:
            vf.append(f"[v{i}][{pngs[i]}:v]overlay=0:0[w{i}]")
        else:
            vf.append(f"[v{i}]null[w{i}]")
    if bed:
        af.append(f"[{n}:a]anull[x0]")
        prev, denoise = "x0", ""
    else:
        for i, c in enumerate(a.clips):
            lu = loudness(path_of(c))
            if lu is None:
                af.append(f"anullsrc=r=44100:cl=stereo,atrim=duration={shot + XF:.3f}[a{i}]")
            else:
                af.append(f"[{n + i}:a]aresample=44100,aformat=channel_layouts=stereo,"
                          f"volume={AMB_LUFS - lu:.1f}dB,asetpts=PTS-STARTPTS[a{i}]")
        prev = "a0"
        for i in range(1, n):
            af.append(f"[{prev}][a{i}]acrossfade=d={XF}:c1=qsin:c2=qsin[x{i}]")
            prev = f"x{i}"
        denoise = "afftdn=nf=-30,"  # only muse's sound: a real recording's rain IS the noise
    if a.dissolve:
        # each shot runs `dissolve` longer and the next one fades in over that tail: shot k starts at k*shot
        vp = "w0"
        for i in range(1, n):
            vf.append(f"[{vp}][w{i}]xfade=transition=fade:duration={a.dissolve}:offset={i * shot:.3f}[d{i}]")
            vp = f"d{i}"
        chain = f"[{vp}]trim=duration={total:.3f},"
    else:
        chain = "".join(f"[w{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,"
    graph = vf + af + [
        f"{chain}fade=t=in:d=0.3,fade=t=out:st={total - 0.5:.3f}:d=0.5,format=yuv420p[vout]",
        f"[{prev}]atrim=duration={total:.3f},{denoise}volume={a.ambience},"
        f"afade=in:d=0.3,afade=out:st={total - 1.2:.3f}:d=1.2[amb]",
        f"[{mi}:a]atrim=duration={total:.3f},afade=in:d=0.2,afade=out:st={total - 1.2:.3f}:d=1.2[mus]",
        "[mus][amb]amix=inputs=2:normalize=0[aout]",
    ]
    args += ["-filter_complex", ";".join(graph), "-map", "[vout]", "-map", "[aout]",
             "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "pcm_s16le", str(tmp / "mix.mov")]
    subprocess.run(args, check=True)
    # one fixed gain to -16 LUFS (single-pass loudnorm pumps), then mux
    lnorm = Path(__file__).with_name("lnorm.py")
    subprocess.run(["python3", str(lnorm), str(tmp / "mix.mov"), str(tmp / "mix.m4a"), "-16"], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp / "mix.mov"), "-i", str(tmp / "mix.m4a"),
                    "-map", "0:v", "-map", "1:a", "-c", "copy", "-movflags", "+faststart", a.out], check=True)
    print(f"{a.out}: {n} shots x {shot:.2f} s = {total:.1f} s")


def make_bed(choice, idea, total, tmp):
    """Real ambience recording covering `total` s at AMB_LUFS (looped with cross-fades), or None
    to use the clips' own sound."""
    if choice == "clips":
        return None
    if choice and Path(choice).is_file():
        src, s0, s1, filt = Path(choice), 0.0, None, ""
    else:
        name = choice or next((k for k, (words, *_) in BEDS.items()
                               if any(w in (idea.get("sound") or "").lower() for w in words)), None)
        if name not in BEDS:
            return None
        _, src, s0, s1, filt = BEDS[name]
        own = sorted((Path.home() / ".config/museai/ambience").glob(f"{name}.*"))
        if own:
            src, s0, s1, filt = own[0], 0.0, None, ""
        if not src.is_file():
            print(f"no {name} recording ({src}); using the clips' own sound")
            return None
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(src)], capture_output=True, text=True).stdout)
    s1 = min(s1 or dur, dur)
    seg = s1 - s0
    copies = 1 if seg >= total else int((total - BED_XF) // (seg - BED_XF)) + 1
    raw = tmp / "bed_raw.wav"
    if copies > 1:
        graph = f"[0:a]asplit={copies}" + "".join(f"[s{k}]" for k in range(copies)) + ";" + "".join(
            f"[s{k}]atrim={s0}:{s1},asetpts=PTS-STARTPTS[c{k}];" for k in range(copies))
        prev = "c0"
        for k in range(1, copies):
            graph += f"[{prev}][c{k}]acrossfade=d={BED_XF}:c1=qsin:c2=qsin[l{k}];"
            prev = f"l{k}"
        graph += f"[{prev}]"
    else:
        graph = f"[0:a]atrim={s0}:{s1},asetpts=PTS-STARTPTS,"
    graph += ",".join(filter(None, ["aresample=44100", "aformat=channel_layouts=stereo", filt])) + "[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex", graph, "-map", "[out]",
                    str(raw)], check=True)
    lu = loudness(str(raw)) or AMB_LUFS
    bed = tmp / "bed.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", f"volume={AMB_LUFS - lu:.1f}dB", str(bed)],
                   check=True)
    print(f"ambience: {src.name} {s0}-{s1:.1f} s x{copies}")
    return bed


def path_of(c):
    return c.partition("@")[0]


if __name__ == "__main__":
    main()
