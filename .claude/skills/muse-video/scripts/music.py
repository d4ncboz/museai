# /// script
# requires-python = ">=3.10,<3.13"
# dependencies = ["torch", "transformers>=4.40", "librosa", "soundfile", "numpy", "scipy"]
# ///
"""Generate the music for a reel from a pick.py plan: the template's BPM, tags and lyrics, cut to
exactly the reel's beats, plus a beat file (<out>.beats.json) compose.py cuts on.

Usage:
  python3 ../../scenic-drop-reel/scripts/pick.py --place "Amalfi Coast" ... > plan.json
  uv run --no-project scripts/music.py --plan plan.json --out track.m4a [--engine ace|musicgen] [--seed 7]
  uv run --no-project scripts/music.py --style "tropical house, marimba" --bpm 100 --intro-beats 5 \
      --body-beats 15 --out track.m4a          # without a plan

Engines: ace = ACE-Step (sings the template's lyrics; Apache-2.0; needs the install in ../SKILL.md "Music", run
through its own venv by ace_song.py), musicgen = MusicGen instrumental (CC-BY-NC 4.0 weights:
personal reels only). ace is used when installed, else musicgen.
Steps: render ~2x the needed length → librosa finds the tempo → MusicGen is time-stretched to exactly
the BPM; an ACE song keeps its own tempo (a stretch makes the voice robotic) and the beat file follows it →
body = the loudest, cleanest beat-aligned stretch → card templates (countdown / black-title /
coords) get an intro of intro.beats before the body: low-passed 300→7000 Hz sweep, -14→-4 dB swell
and a noise whoosh that stops dead on the drop → tanh drive to phone loudness (-13 dB mean).
"""
import argparse
import contextlib
import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf
import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration

SCRIPTS = Path(__file__).resolve().parent
ACE_PY = Path(os.environ.get("ACE_STEP_HOME", Path.home() / ".local/share/ace-step")) / "venv/bin/python"
CARD_INTROS = ("countdown", "black-title", "coords")


def song_tempo(y, sr, bpm):
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr, start_bpm=bpm)
    tempo = float(np.atleast_1d(tempo)[0])
    if tempo <= 0:  # no pulse found (ACE ambient drone, Bran Castle episode): keep the template tempo
        print(f"no beat detected in the raw track, keeping the template {bpm:.0f} BPM", file=sys.stderr)
        return bpm
    return min((tempo * k for k in (0.5, 1, 2)), key=lambda t: abs(t - bpm))  # half/double-time guesses


def generate_ace(tags, lyrics, bpm, seconds, seed, wav):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(lyrics or "[instrumental]")
    # duets and negated words ("no autotune") pull ACE toward the robotic, pitched voice the user rejected
    tags = re.sub(r"\b(male and female|female and male) vocals\b", "female vocals", tags)
    # ACE reads "no autotune" as "autotune": drop negated phrases (Zhangjiajie reel, 2026-10-31, pitched voice)
    tags = re.sub(r"(^|,)\s*(no|without|not|never)\b[^,]*", "", tags, flags=re.I).strip(" ,")
    # "hushed"/"airy"/"whispered" pushed ACE into a thin head voice (Fuji reel, 2026-11-02: "hushed male vocal"
    # sang at a median 259 Hz, pitch-snapped like autotune; the user heard a pitched robot)
    tags = re.sub(r"\b(hushed|airy|whispered|breathy|falsetto)\s+", "", tags, flags=re.I)
    if female_voice(tags):
        voice = "one alto female singer in a relaxed chest voice"
    else:
        voice = "one baritone male singer in a relaxed chest voice, singing in the range of his speaking voice"
    # the user wants the voice low and warm, never shrill (Zhangjiajie reel, 2026-10-31), and a real person,
    # never a pitched robot (Fuji reel, 2026-11-02)
    tags = (f"{tags}, {bpm:.0f} bpm, {voice}, natural human voice with slight natural vibrato and small human pitch "
            "drift, raw unprocessed live vocal take, clear diction, warm dry vocal sitting in balance with the "
            "instruments, mellow low and mid-range sound, organic live studio mix")
    subprocess.run([str(ACE_PY), str(SCRIPTS / "ace_song.py"), "--tags", tags,
                    "--lyrics-file", f.name, "--duration", f"{seconds:.0f}", "--seed", str(seed), "--out", str(wav)],
                   check=True)
    return librosa.load(wav, sr=None, mono=True)


@contextlib.contextmanager
def ace_lock():
    # one ACE render per machine: two at once share the GPU and both crawl (Svalbard + Vatnajokull reels,
    # 2026-10-28: model load 40 s -> 285 s, 1.5 s/step -> 100+ s/step); later ones wait here.
    # Held for all takes of one track: released between takes, other sessions took it and the Fuji reel
    # waited 40 min between take 1 and take 2 (2026-11-02)
    with open(ACE_PY.parent.parent.parent / "render.lock", "w") as lf:
        try:
            fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("another ACE render is running on this machine; waiting for it", file=sys.stderr)
            fcntl.flock(lf, fcntl.LOCK_EX)
        yield


def female_voice(tags):
    return bool(re.search(r"\b(female|woman|girl)\b", tags, re.I))


# a real singer drifts off the semitone grid; ACE's robotic voice snaps to it like hard autotune
# (Fuji reel, 2026-11-02, rejected: median 259 Hz for a "male" voice, median 9.2 cents off the nearest semitone)
MAX_VOICE_HZ = {"male": 180, "female": 300}
MIN_DRIFT_CENTS = 14


def voice_check(wav, tags):
    """Median pitch and pitch drift of the lead vocal (demucs stem): (ok, summary)."""
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run(["uv", "run", "--no-project", "--python", "3.11", "--with", "demucs", "--with", "soundfile",
                            "python", "-m", "demucs", "--two-stems=vocals", "-n", "htdemucs", "-o", tmp, str(wav)],
                           capture_output=True, text=True)
        stem = Path(tmp) / "htdemucs" / Path(wav).stem / "vocals.wav"
        if r.returncode or not stem.exists():
            return True, "voice not checked (demucs failed)"
        v, sr = librosa.load(stem, sr=16000, mono=True)
    f0, voiced, _ = librosa.pyin(v, fmin=65, fmax=800, sr=sr)
    f = f0[voiced & ~np.isnan(f0)]
    if len(f) < 0.1 * len(f0):
        return True, "no lead vocal found"
    hz = float(np.median(f))
    cents = 1200 * np.log2(f / 440)
    drift = float(np.median(np.abs((cents + 50) % 100 - 50)))
    kind = "female" if female_voice(tags) else "male"
    why = []
    if hz > MAX_VOICE_HZ[kind]:
        why.append(f"too high for a {kind} voice (> {MAX_VOICE_HZ[kind]} Hz)")
    if drift < MIN_DRIFT_CENTS:
        why.append(f"pitch-snapped like autotune (< {MIN_DRIFT_CENTS} cents)")
    return not why, f"voice median {hz:.0f} Hz, {drift:.1f} cents off the semitone" + (": " + ", ".join(why) if why else "")


def generate(style, bpm, seconds, model_id, seed):
    proc = AutoProcessor.from_pretrained(model_id)
    model = MusicgenForConditionalGeneration.from_pretrained(model_id)
    style = ", ".join(t for t in style.split(",") if "vocal" not in t and "sing" not in t)  # MusicGen can't sing
    text = [f"{style}, {bpm:.0f} bpm, steady beat, catchy hook, instrumental, no vocals"]
    for dev in (["mps"] if torch.backends.mps.is_available() else []) + ["cpu"]:
        torch.manual_seed(seed)
        try:
            inputs = proc(text=text, padding=True, return_tensors="pt").to(dev)
            out = model.to(dev).generate(**inputs, do_sample=True, guidance_scale=3.0,
                                         max_new_tokens=int(seconds * 50))
            return out[0, 0].float().cpu().numpy(), model.config.audio_encoder.sampling_rate
        except (RuntimeError, NotImplementedError) as e:  # MPS lacks some ops on older torch
            if dev == "cpu":
                raise
            print(f"{dev} failed ({e}); retrying on cpu", file=sys.stderr)


def sweep_lowpass(y, sr, f0, f1, n_fft=2048, hop=256):
    """Low-pass whose cutoff rises exponentially from f0 to f1 over the clip (STFT mask)."""
    S = librosa.stft(y, n_fft=n_fft, hop_length=hop)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)[:, None]
    cut = f0 * (f1 / f0) ** np.linspace(0, 1, S.shape[1])[None, :]
    mask = 1 / (1 + (freqs / cut) ** 8)
    return librosa.istft(S * mask, hop_length=hop, length=len(y))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", help="pick.py output (JSON file): bpm, tags, lyrics, intro and shot beats")
    ap.add_argument("--style", help="no plan: genre/instruments/mood")
    ap.add_argument("--lyrics", default="", help="no plan: lyrics with [verse]/[chorus] tags (ace only)")
    ap.add_argument("--bpm", type=float, default=100)
    ap.add_argument("--intro-beats", type=int, default=0, help="riser length before the drop (0 = start on the beat)")
    ap.add_argument("--body-beats", type=int, default=16)
    ap.add_argument("--out", required=True)
    ap.add_argument("--engine", choices=["ace", "musicgen"], help="default: ace if installed, else musicgen")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--model", default="facebook/musicgen-medium")
    ap.add_argument("--raw", help="reuse an already generated wav instead of rendering")
    a = ap.parse_args()

    if a.plan:
        plan = json.loads(Path(a.plan).read_text())
        m = plan["music"]
        style, lyrics, bpm = m["tags"], m.get("lyrics", ""), float(m["bpm"])
        intro_beats = plan["intro"].get("beats", 0) if plan["intro"]["type"] in CARD_INTROS else 0
        body_beats = sum(s["beats"] for s in plan["shots"]) + 1
    else:
        style, lyrics, bpm = a.style or ap.error("--plan or --style"), a.lyrics, a.bpm
        intro_beats, body_beats = a.intro_beats, a.body_beats
    beat = 60 / bpm
    intro_s, body_s = intro_beats * beat, body_beats * beat
    engine = a.engine or ("ace" if ACE_PY.exists() else "musicgen")
    raw = Path(a.out).with_suffix(".raw.wav")
    seconds = max(24, 2 * (intro_s + body_s))

    if a.raw:
        y, sr = librosa.load(a.raw, sr=None, mono=True)
    elif engine == "ace":
        # ACE ignores the BPM tag (asked 112: 120 and 134; asked 100: 94 and 128) and sometimes sings in a
        # pitched robot voice: re-render on the next seed until the tempo is within 10 % and the voice passes
        # voice_check; of 4 takes keep a natural voice first, then the closest tempo
        best = None
        with ace_lock():
          for seed in range(a.seed, a.seed + 4):
              y, sr = generate_ace(style, lyrics, bpm, max(seconds, 40), seed, raw)
              got = song_tempo(y, sr, bpm)
              off = abs(got - bpm) / bpm
              natural, voice = voice_check(raw, style) if lyrics else (True, "instrumental")
              print(f"seed {seed}: song at {got:.0f} BPM (asked {bpm:.0f}), {voice}", file=sys.stderr)
              rank = (not natural, off)
              if best is None or rank < best[0]:
                  best = (rank, y, sr)
                  raw.with_suffix(".best.wav").write_bytes(raw.read_bytes())
              if natural and off <= 0.1:
                  break
        if best[0][0]:
            print("warning: no take had a natural voice; kept the closest tempo. Listen before composing", file=sys.stderr)
        _, y, sr = best
        raw.with_suffix(".best.wav").replace(raw)
    else:
        if engine == "musicgen" and lyrics and not a.engine:
            print("ACE-Step not installed: instrumental MusicGen track, lyrics skipped", file=sys.stderr)
        y, sr = generate(style, bpm, min(seconds, 30), a.model, a.seed)
        sf.write(raw, y, sr)

    tempo = song_tempo(y, sr, bpm)
    if engine == "ace":
        # a phase-vocoder stretch makes the singer sound robotic and pitched (Kirkjufell reel,
        # 134→108 BPM); keep the song as sung and cut the reel on its own tempo instead
        target, bpm = bpm, tempo
        beat = 60 / bpm
        intro_s, body_s = intro_beats * beat, body_beats * beat
    else:
        target = bpm
        y = librosa.effects.time_stretch(y, rate=bpm / tempo)
    _, beats = librosa.beat.beat_track(y=y, sr=sr, start_bpm=bpm, tightness=400, units="samples")
    if len(beats) == 0:  # beatless track: candidate body starts on an even grid at the kept tempo
        beats = np.arange(0, len(y), int(60 / bpm * sr))

    body_len = int((body_s + 0.3) * sr)
    intro_len = int(intro_s * sr)
    hop = 512
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    rms = rms / rms.max()
    level = np.convolve(rms, np.ones(sr // 2 // hop) / (sr // 2 // hop), mode="same")  # 0.5 s loudness
    flat = librosa.feature.spectral_flatness(y=y, hop_length=hop)[0]
    if engine == "ace":  # sustained harmonic energy in the voice band: where the singing is
        S = np.abs(librosa.stft(y, hop_length=hop))
        H, P = librosa.decompose.hpss(S)
        band = slice(*np.searchsorted(librosa.fft_frequencies(sr=sr), [200, 4000]))
        voice = H[band].sum(0) / (H[band].sum(0) + P[band].sum(0) + 1e-9)
        # a pad-only stretch scores high on voice too, so the slice must also keep the drums going
        punch = librosa.onset.onset_strength(S=librosa.amplitude_to_db(P, ref=np.max), sr=sr)
        punch = punch / punch.max()
    valid = [b for b in beats if b >= max(intro_len, int(0.5 * sr)) and b + body_len <= len(y)]
    if not valid:
        sys.exit(f"generated track ({len(y) / sr:.1f}s) too short for {intro_s:.1f}s intro + {body_s:.1f}s body")

    def body_score(b):  # loud, even groove; MusicGen's noisy swells (high flatness) read as hiss on a phone
        i, j = b // hop, (b + body_len) // hop
        k = i + sr // hop  # the first second after the drop must be clean groove, not the tail of a swell
        score = rms[i:j].mean() - 0.5 * rms[i:j].std() - flat[i:j].mean() - flat[i:k].mean()
        # a breakdown inside the reel reads as the music stopping (Iceland ACE track: 1.5 s near-silence)
        score -= 2 * max(0.0, 0.5 - level[i:j].min() / np.median(level[i:j]))
        if engine == "ace":
            score += 0.5 * voice[i:j].mean() + 2 * punch[i:j].mean()
            h = i + 3 * sr // hop  # the first 3 s decide whether a viewer stays: start on the sung hook
            score += voice[i:h].mean() + punch[i:h].mean()
        return score

    b0 = max(valid, key=body_score)
    body = y[b0:b0 + body_len].copy()
    fade = int(0.3 * sr)
    body[-fade:] *= np.linspace(1, 0, fade)

    parts = [body]
    if intro_len:
        intro = sweep_lowpass(y[b0 - intro_len:b0], sr, 300, 7000)
        t = np.linspace(0, 1, intro_len)
        intro *= 10 ** ((-14 + 10 * t) / 20)  # -14 dB → -4 dB swell
        noise = np.random.default_rng(a.seed).standard_normal(intro_len)
        intro = intro + sweep_lowpass(noise, sr, 500, 12000) * 0.08 * t ** 3  # whoosh up to the drop
        intro[-int(0.02 * sr):] *= np.linspace(1, 0.2, int(0.02 * sr))  # tiny gap so the drop hits
        parts.insert(0, intro)
    track = np.concatenate(parts)
    # no saturation drive: tanh clipping made the singer harsh and loud over the band (Svalbard reel);
    # loudnorm brings it to phone level instead
    track = track / np.abs(track).max() * 10 ** (-1 / 20)

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "t.wav"
        sf.write(wav, track, sr)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-af", "loudnorm=I=-14:TP=-1.5:LRA=9", "-ar", "44100", "-ac", "2",
                        "-c:a", "aac", "-b:a", "192k", a.out], check=True)
    drop = intro_len / sr
    grid = [round(drop + k * beat, 4) for k in range(-intro_beats, body_beats + 1)]
    Path(a.out).with_suffix(".beats.json").write_text(json.dumps(
        {"bpm": bpm, "beats": grid, "drop": round(drop, 4) if intro_len else None, "engine": engine}))
    kept = " (kept, no stretch)" if engine == "ace" else ""
    print(f"{a.out} ({engine}): body from {b0 / sr:.2f}s of the raw track, tempo {tempo:.1f}→{bpm:.0f} BPM{kept}"
          f" (template {target:.0f}), "
          f"drop {drop:.3f}s, length {len(track) / sr:.2f}s")


if __name__ == "__main__":
    main()
