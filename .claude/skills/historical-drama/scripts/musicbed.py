#!/usr/bin/env python3
"""Offline guzheng-style music bed (Karplus-Strong plucks on a pentatonic scale + soft drone), no downloads.
Usage: musicbed.py LEN_SEC OUT.wav  [--tense T0,T1 ...]  (windows where it turns low/sparse/tense)
Part 1 hook: sparse bright plucks; tense windows: low drone, slow minor-ish plucks."""

import sys
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(7)


def pluck(f, dur, amp):
    n = int(SR * dur)
    p = int(SR / f)
    buf = rng.uniform(-1, 1, p)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * 0.996
    env = np.exp(-np.linspace(0, 4, n))
    return out * env * amp


def main():
    length = float(sys.argv[1])
    out = sys.argv[2]
    tense = [tuple(map(float, a.split(","))) for a in sys.argv[3:]]
    y = np.zeros(int(SR * (length + 3)))
    bright = [293.66, 329.63, 369.99, 440.0, 493.88, 587.33]  # D pentatonic
    dark = [146.83, 174.61, 220.0, 246.94, 293.66]  # D minor-ish, low
    t = 0.5
    while t < length:
        is_t = any(a <= t < b for a, b in tense)
        scale = dark if is_t else bright
        f = rng.choice(scale)
        note = pluck(f, 2.5, 0.5 if not is_t else 0.6)
        i = int(t * SR)
        y[i : i + len(note)] += note[: len(y) - i]
        t += rng.choice([1.1, 1.6, 2.2]) if not is_t else rng.choice([2.4, 3.2])
    # drone under tense windows
    tt = np.arange(len(y)) / SR
    for a, b in tense:
        env = np.clip(np.minimum(tt - a, b - tt) / 1.5, 0, 1)
        y += 0.12 * env * (np.sin(2 * np.pi * 73.42 * tt) + 0.5 * np.sin(2 * np.pi * 110 * tt))
    y = y[: int(SR * length)]
    fade = np.minimum(
        1, np.minimum(np.arange(len(y)) / (SR * 1.5), (len(y) - np.arange(len(y))) / (SR * 2.0))
    )
    y = y * fade
    y = y / (np.abs(y).max() + 1e-9) * 0.9
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((y * 32767).astype(np.int16).tobytes())


main()
