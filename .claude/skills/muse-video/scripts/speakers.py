"""Usage: speakers.py video.mp4 cues.json SPEAKERS mouths.jpg
       speakers.py video.mp4 script.txt words.json mouths.jpg   (one clip, before captions)
  uv run --no-project --python 3.12 --with mediapipe==0.10.14 --with opencv-python-headless==4.10.0.84 --with librosa \\
      python scripts/speakers.py video.mp4 cues.json WWMWMWMWMWMW mouths.jpg

Checks that the right person says each line, on screen, and that the listener does not mime it.
SPEAKERS has one letter per cue: W = woman, M = man. script.txt has "W: line" / "M: line" per
line; the line times come from aligning it to words.json (transcribe.py / check_clip.sh output).
Env: FEMALE=W (who has the higher voice), LEFT=W (who stands on screen left).
  voice   median pitch per line (pyin, yin on the loud frames when pyin calls the line unvoiced):
          female > 165 Hz, male < 165 Hz; must fit the speaker.
  face    the speaker's face (frontal or profile) is found on their side of the frame, or alone as
          a punch-in, in >= 50 % of the line. EP08: the woman was filmed from behind; muse gave all
          5 of her lines to the clerk's lips while the voices stayed right (face seen 0 %).
  mouth   every frame, each face is cropped, upscaled and run through face mesh; the lip gap
          (inner lips / face height) is tracked per face. On each line the listener's lip gap
          must stay still: it fails when std > 0.010 and mean frame-to-frame change > 0.004.
          EP09: a closed listener measured std <= 0.004 / change <= 0.001, the man miming the
          woman's lines std 0.016-0.022 / change 0.009 (as much as when he spoke). Punch-in lines
          (one face wider than 55 % of the frame) and solo to-camera shots (one face centred within
          12 % of the middle) have no listener to check.
          Face mesh is noisy on strict profiles, so keep both faces three-quarter to the camera.
  sync    voice without lips: from the line's start until just before the next line, every frame
          with voice (> -32 dB) needs the speaker's lips moving (lip gap range over 7 frames
          >= 0.012). A run of >= 0.45 s of voice over still lips fails SOUND WITHOUT LIPS.
          EP09 v5: muse put the woman's 一起去吃饭吧 on the man's lips (her gap frozen 1 s), and the
          dubbed voice ran 0.4-0.7 s past the closed lips on 3 lines; both were heard, not seen
          on the contact sheet. Talking lips measured ranges 0.03-0.09.
  sheet   writes mouths.jpg (one column per line, 6 frames of the mouth band) to look at the
          flagged lines.
  report  REPORT=report.json writes per line: times, speaker, verdicts, median speaker face box
          [cx, cy, w, h] (fractions of the frame).
Exit 1 when any line fails voice, face, mouth or sync."""
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile

# Face mesh over every frame is minutes of full CPU: on the Colab render queue while it is online (remote.py);
# SPEAKERS_REMOTE=0 keeps it here, and a failed job runs here
if os.environ.get("SPEAKERS_REMOTE", "1") != "0" and len(sys.argv) == 5:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import remote

    if remote.online()[0]:
        print("speakers: remote", file=sys.stderr)
        rc = remote.speakers(sys.argv[1:])
        if rc is not None:
            sys.exit(rc)
        print("speakers: local (remote job failed)", file=sys.stderr)

import cv2  # noqa: E402
import librosa  # noqa: E402
import mediapipe as mp  # noqa: E402
import numpy as np  # noqa: E402

video, sheet = sys.argv[1], sys.argv[-1]
if sys.argv[2].endswith(".json"):  # cues.json SPEAKERS
    cues, who = json.load(open(sys.argv[2])), sys.argv[3].upper()
else:  # script.txt words.json: line times from aligning the script to the transcript
    lines = [t.split(":", 1) for t in open(sys.argv[2], encoding="utf-8") if ":" in t]
    who = "".join(x[0].strip()[0].upper() for x in lines)
    words = json.load(open(sys.argv[3]))
    chars = [(ch, w["s"] + (w["e"] - w["s"]) * k / len(w["w"])) for w in words for k, ch in enumerate(w["w"])]
    han = lambda t: re.findall(r"[一-鿿]", t)  # noqa: E731
    script = [(i, ch) for i, (_, t) in enumerate(lines) for ch in han(t)]
    heard = [(ch, t) for ch, t in chars if han(ch)]
    sm = difflib.SequenceMatcher(None, [c for _, c in script], [c for c, _ in heard], autojunk=False)
    times = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            times.setdefault(script[blk.a + k][0], []).append(heard[blk.b + k][1])
    cues = [[min(times[i]), max(times[i]) + 0.2, t.strip()] if i in times else [0, 0, t.strip()]
            for i, (_, t) in enumerate(lines)]
if len(who) != len(cues):
    sys.exit(f"SPEAKERS has {len(who)} letters for {len(cues)} cues")
female = os.environ.get("FEMALE", "W")
left = os.environ.get("LEFT", "W")
right = next((x for x in sorted(set(who)) if x != left), "?")
SPLIT_HZ = 165
STILL_STD, STILL_MOVE = 0.010, 0.004  # listener lip gap limits
LOUD_DB, LIPS_RANGE, MUTE_RUN = -32, 0.012, 0.45  # sync: voice level, moving-lips range, max voice over still lips
ROWS, BAND = 6, 0.14  # sheet: frames per cue, band height as a fraction of the frame height

# voice
with tempfile.NamedTemporaryFile(suffix=".wav") as wav:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-ac", "1", "-ar", "16000", wav.name], check=True)
    y, sr = librosa.load(wav.name, sr=16000)
f0, voiced, _ = librosa.pyin(y, fmin=70, fmax=400, sr=sr, frame_length=1024)
f0_t = librosa.times_like(f0, sr=sr, hop_length=256)

# lip gap per face, every frame
det = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.3)
profile = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")  # opencv 5 ships none
mesh = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True,
                                 min_detection_confidence=0.2)  # refined lips: unrefined ones missed the miming
cap = cv2.VideoCapture(video)
fps = cap.get(cv2.CAP_PROP_FPS)
gaps = {}  # (frame time, side) -> lip gap; side is the person letter, or "solo" with one face
boxes = {}  # (frame time, side) -> face box [cx, cy, w, h]
mouth_ys, n = [], 0
while True:
    ok, img = cap.read()
    if not ok:
        break
    t, n = n / fps, n + 1
    H, W = img.shape[:2]
    found = [d.location_data.relative_bounding_box for d in det.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).detections or []]
    mouth_ys.append((t, [(b.ymin + 0.78 * b.height) * H for b in found]))
    for b in found:
        x0, y0 = int(max(0, (b.xmin - 0.25 * b.width) * W)), int(max(0, (b.ymin - 0.3 * b.height) * H))
        x1, y1 = int(min(W, (b.xmin + 1.25 * b.width) * W)), int(min(H, (b.ymin + 1.2 * b.height) * H))
        if x1 - x0 < 20 or y1 - y0 < 20:
            continue
        crop = cv2.resize(img[y0:y1, x0:x1], (384, int(384 * (y1 - y0) / (x1 - x0))))
        r = mesh.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
        if not r.multi_face_landmarks:
            continue
        lm = r.multi_face_landmarks[0].landmark
        # punch-in (two-shot faces measure up to ~0.46 wide), or a lone face centred in the frame:
        # a to-camera intro (EP10: cx 0.50, it flipped sides and her own lips counted as the listener's)
        solo = len(found) == 1 and (b.width > 0.55 or abs(b.xmin + b.width / 2 - 0.5) < 0.12)
        side = "solo" if solo else (left if b.xmin + b.width / 2 < 0.5 else right)
        gaps[(t, side)] = abs(lm[13].y - lm[14].y) / max(1e-6, abs(lm[10].y - lm[152].y))
        boxes[(t, side)] = [b.xmin + b.width / 2, b.ymin + b.height / 2, b.width, b.height]


def stillness(person, a, b):
    g = np.array([v for (t, s), v in sorted(gaps.items()) if s == person and a <= t <= b])
    if len(g) < 8:
        return None
    return float(g.std()), float(np.abs(np.diff(g)).mean())


def voice_without_lips(person, a, b):
    """Longest run (s) of voiced frames in [a, b] where the person's lips are still; None without a face."""
    g = {round(t * fps): v for (t, p), v in gaps.items() if p in (person, "solo") and a - 0.2 <= t <= b + 0.2}
    if len(g) < 8:
        return None
    run = best = 0
    for f in range(round(a * fps), round(b * fps)):
        near = [g[k] for k in range(f - 3, f + 4) if k in g]
        if f >= len(frame_db) or frame_db[f] < LOUD_DB:
            run = 0
        elif f in g and len(near) >= 4 and max(near) - min(near) < LIPS_RANGE:
            run += 1
            best = max(best, run)
    return best / fps


def face_seen(a, b, s):
    """Share of 8 frames in [a, b] with the speaker's face: on their half, alone and wide, or in profile."""
    hits = 0
    for t in np.linspace(a, b, 8):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, img = cap.read()
        if not ok:
            continue
        W = img.shape[1]
        on_left = s == left
        r = [d.location_data.relative_bounding_box for d in det.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB)).detections or []]
        if (len(r) == 1 and (r[0].width > 0.55 or abs(r[0].xmin + r[0].width / 2 - 0.5) < 0.12)) or any((x.xmin + x.width / 2 < 0.5) == on_left for x in r):
            hits += 1
            continue
        part = cv2.equalizeHist(cv2.cvtColor(img[:, : W // 2] if on_left else img[:, W // 2:], cv2.COLOR_BGR2GRAY))
        size = (W // 12, W // 12)
        hits += any(len(profile.detectMultiScale(im, 1.05, 2, minSize=size)) for im in (part, cv2.flip(part, 1)))
    return hits / 8


def strip(t):
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, img = cap.read()
    if not ok:
        return None
    H, W = img.shape[:2]
    ys = min(mouth_ys, key=lambda x: abs(x[0] - t) if x[1] else 1e9)[1]
    cy = float(np.mean(ys)) if ys else 0.4 * H
    h = int(BAND * H)
    y0 = int(min(max(cy - h / 2, 0), H - h))
    return cv2.resize(img[y0:y0 + h], (360, int(360 * h / W)))


hop = sr / fps
frame_db = 20 * np.log10(librosa.feature.rms(y=y, frame_length=int(2 * hop), hop_length=int(hop), center=True)[0] + 1e-9)
bad, cols, report = [], [], []
for i, (c, s) in enumerate(zip(cues, who, strict=True)):
    a, b = c[0], c[1]
    sel = (f0_t >= a) & (f0_t <= b) & voiced
    if sel.sum() >= 5:
        hz = float(np.nanmedian(f0[sel]))
    else:  # pyin can call a whole line unvoiced (EP08 好的，谢谢！); then 1-2 frames of the next speaker
        # at the cue edge decide the pitch. yin on the line's loud frames still finds it.
        seg = y[int(a * sr):int(b * sr)]
        f = librosa.yin(seg, fmin=70, fmax=400, sr=sr, frame_length=1024) if len(seg) > 1024 else np.array([])
        rms = librosa.feature.rms(y=seg, frame_length=1024, hop_length=256)[0] if len(f) else np.array([])
        m = min(len(f), len(rms))
        loud = rms[:m] > 0.5 * rms[:m].max() if m else np.array([], bool)
        hz = float(np.median(f[:m][loud])) if loud.any() else float("nan")
    flags = [] if np.isnan(hz) or ((hz > SPLIT_HZ) == (s == female)) else ["WRONG VOICE"]
    seen = face_seen(a, b, s)
    if seen < 0.5:
        flags.append(f"SPEAKER FACE HIDDEN ({seen:.0%})")
    listener = left if s != left else right
    # skip the listener's own mouth closing after their previous line, and the next line's onset
    nxt = cues[i + 1][0] if i + 1 < len(cues) else b
    st = stillness(listener, a + 0.25, min(b, nxt) - 0.1)
    if st and st[0] > STILL_STD and st[1] > STILL_MOVE:
        flags.append(f"LISTENER MOUTH MOVES (std {st[0]:.3f}, move {st[1]:.4f})")
    mute = voice_without_lips(s, a, nxt - 0.05 if i + 1 < len(cues) else b + 0.8)
    if mute is not None and mute >= MUTE_RUN:
        flags.append(f"SOUND WITHOUT LIPS ({mute:.2f} s)")
    lst = "no listener face" if st is None else f"listener std {st[0]:.3f} move {st[1]:.4f}"
    print(f"{i + 1:2d} {a:6.2f}-{b:6.2f} {s} {hz:5.0f}Hz  {lst:32s} {c[2]}" + "".join(f"  <-- {f}" for f in flags))
    if flags:
        bad.append(i + 1)
    bx = [v for (t, p), v in boxes.items() if p in (s, "solo") and a <= t <= b]
    report.append({"line": i + 1, "start": a, "end": b, "speaker": s, "flags": flags,
                   "box": np.median(bx, axis=0).round(3).tolist() if bx else None})
    tiles = [x for t in np.linspace(a + 0.1, max(a + 0.1, b - 0.1), ROWS) if (x := strip(t)) is not None]
    head = np.full((40, 360, 3), 255, np.uint8)
    cv2.putText(head, f"{i + 1} {s}" + (" X" if flags else ""), (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cols.append(np.vstack([head, *tiles]))
h = max(x.shape[0] for x in cols)
cols = [np.vstack([x, np.full((h - x.shape[0], 360, 3), 255, np.uint8)]) for x in cols]
cv2.imwrite(sheet, np.hstack([np.hstack([x, np.full((h, 6, 3), 255, np.uint8)]) for x in cols]))
print(f"mouths: {sheet}")
if os.environ.get("REPORT"):
    json.dump(report, open(os.environ["REPORT"], "w"), ensure_ascii=False, indent=1)
print(f"RESULT {'FAIL lines ' + ','.join(map(str, bad)) if bad else 'ok'}")
sys.exit(1 if bad else 0)
