#!/usr/bin/env python3
"""Recap/quiz tail music, offline numpy synth. Usage: recap_bed.py LEN_SEC OUT.wav [lofi|dream]
lofi : warm Rhodes-style 7th chords, soft kick/brush, round bass, tape hiss, reverb (default)
dream: slow strings-like pad + glassy bell melody, big reverb"""

import sys
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(11)


def N(m):
    return 440 * 2 ** ((m - 69) / 12)


# Cmaj9 - Am9 - Dm9 - G13 (midi)
CHORDS = [[48, 55, 59, 62, 64], [45, 52, 59, 60, 64], [50, 57, 60, 64, 65], [43, 53, 59, 62, 64]]


def tt(d):
    return np.arange(int(SR * d)) / SR


def rhodes(f, d, a):
    t = tt(d)
    y = np.sin(2 * np.pi * f * t) + 0.5 * np.sin(
        2 * np.pi * 2 * f * t + 0.5 * np.sin(2 * np.pi * f * t) * np.exp(-4 * t)
    ) * np.exp(-2.5 * t)
    y *= 1 + 0.12 * np.sin(2 * np.pi * 4.5 * t)
    return y * np.exp(-1.3 * t) * np.minimum(1, t / 0.01) * a


def bell(f, d, a):
    t = tt(d)
    y = (
        np.sin(2 * np.pi * f * t)
        + 0.4 * np.sin(2 * np.pi * 2.76 * f * t) * np.exp(-3 * t)
        + 0.2 * np.sin(2 * np.pi * 5.4 * f * t) * np.exp(-7 * t)
    )
    return y * np.exp(-1.6 * t) * np.minimum(1, t / 0.004) * a


def pad(f, d, a):
    t = tt(d)
    y = sum(
        np.sin(2 * np.pi * f * (1 + c) * t + p)
        for c, p in [(0, 0), (0.004, 1), (-0.004, 2), (0.008, 3)]
    )
    env = np.minimum(1, np.minimum(t / 1.2, (d - t) / 1.2))
    return y * env * a / 4


def reverb(y, sec, mix):
    n = int(SR * sec)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 6, n))
    ir[: int(0.012 * SR)] *= np.linspace(0, 1, int(0.012 * SR))
    L = len(y) + n
    w = np.fft.irfft(np.fft.rfft(y, L) * np.fft.rfft(ir, L), L)[: len(y)]
    return y * (1 - mix) + w / (np.abs(w).max() + 1e-9) * np.abs(y).max() * mix * 1.6


def put(y, x, t):
    i = int(t * SR)
    if i < len(y):
        y[i : i + len(x)] += x[: len(y) - i]


def lofi(length):
    bpm = 74
    beat = 60 / bpm
    y = np.zeros(int(SR * (length + 5)))
    t = 0.0
    bar = 0
    while t < length:
        ch = CHORDS[bar % 4]
        for k, m in enumerate(ch[1:]):  # gentle rolled chord
            put(y, rhodes(N(m + 12), 3.6, 0.22), t + k * 0.035)
        put(y, rhodes(N(ch[0]), 3.8, 0.3), t)  # bass
        for b in range(4):
            if b in (0, 2):  # soft kick
                tk = tt(0.35)
                put(
                    y,
                    np.sin(2 * np.pi * (55 + 90 * np.exp(-25 * tk)) * tk) * np.exp(-9 * tk) * 0.5,
                    t + b * beat,
                )
            if b in (1, 3):  # brush snare
                tk = tt(0.2)
                put(y, rng.standard_normal(len(tk)) * np.exp(-18 * tk) * 0.1, t + b * beat)
            for h in (0, 0.5):  # hat
                tk = tt(0.06)
                put(y, rng.standard_normal(len(tk)) * np.exp(-60 * tk) * 0.035, t + (b + h) * beat)
        for _k, (st, m) in enumerate(
            [(1.5, 76), (2.25, 79), (3.0, 81)]
            if bar % 2 == 0
            else [(0.5, 74), (1.75, 72), (3.25, 76)]
        ):
            put(
                y, rhodes(N(m + (0 if bar % 4 < 2 else -2)), 1.6, 0.16), t + st * beat
            )  # sparse melody
        bar += 1
        t += 4 * beat
    y += rng.standard_normal(len(y)) * 0.004
    return reverb(y, 1.6, 0.28)


def dream(length):
    y = np.zeros(int(SR * (length + 6)))
    bar = 0
    t = 0.0
    d = 4.5
    mel = [[79, 76, 72, 76], [81, 76, 72, 69], [77, 74, 69, 74], [79, 74, 71, 67]]
    while t < length:
        ch = CHORDS[bar % 4]
        for m in ch:
            put(y, pad(N(m + (12 if m < 50 else 0)), d + 1.5, 0.3), t)
        for k, m in enumerate(mel[bar % 4]):
            put(y, bell(N(m + 12), 3.0, 0.22), t + 0.6 + k * 1.0)
        bar += 1
        t += d
    return reverb(y, 3.2, 0.45)


def main():
    length = float(sys.argv[1])
    out = sys.argv[2]
    style = sys.argv[3] if len(sys.argv) > 3 else "lofi"
    y = (lofi if style == "lofi" else dream)(length)[: int(SR * length)]
    idx = np.arange(len(y))
    y *= np.minimum(1, np.minimum(idx / (SR * 1.0), (len(y) - idx) / (SR * 1.5)))
    y = y / (np.abs(y).max() + 1e-9) * 0.9
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((y * 32767).astype(np.int16).tobytes())


main()
