"""mkshots.py -> single-person shot prompts jinxiu-0N/sXX.txt/.script/.lines (listener never on screen)."""

from pathlib import Path

M = Path.home() / "Movies/museai"
VOICE = (
    "VOICE: Natural Standard Mandarin (Putonghua, Beijing-standard pronunciation, no regional or Taiwanese accent, correct tone sandhi: 不 before a 4th tone is bú, 一 before a 4th tone is yì), accurate tones, every syllable crisp and complete, warm everyday "
    "intonation, about 4.5 syllables per second for every line. Clean close-mic voice, only this one person speaks in the whole clip. "
    "Spontaneous, emotional, human acting voice like a real person talking to a friend: pitch rises and falls, natural stress, small breaths and smiles in the voice, feeling that matches each line; never flat, never robotic, never reading aloud. "
    "NO music, no humming, no instrument and no sound effect at all: only the voice and faint room tone."
)
EMO = {
    "清寒,来碗牛肉面,不要香菜。": "cheerful, playful, warm smile, ordering casually",
    "药店没人,我饿了。": "a little pouty and honest, tired and hungry, soft sigh",
    "嗯……今天的汤有点淡。": "thoughtful and puzzled after tasting, gentle frown",
    "当然,我天天来吃。": "proud and teasing, bright smile",
    "好,不要香菜。今天这么早?": "friendly, pleasantly surprised, smiling",
    "你尝出来了?": "startled and a bit embarrassed, half a laugh",
    "骨头贵了,我少放了一点。": "sheepish and apologetic, voice getting lower",
    "贵了多少?": "curious and concerned",
    "你爸知道吗?": "worried, lowering her voice",
    "我不说,可是他会尝出来。": "gentle warning, a worried half-smile",
    "贵了一半。": "helpless sigh, tired",
    "不知道,别告诉他。": "anxious, pleading, quick and low",
    "清寒,这汤怎么这么淡?": "stern, disappointed",
    "所以你就少放了?": "hard, disbelieving",
    "一点也是骗人。": "firm, heavy",
    "爸,骨头贵了一半。": "nervous, explaining",
    "就少放了一点。": "defensive, small voice",
    "那怎么办?钱不够啊。": "anxious, worried",
    "钱不够,我们少赚一点。": "calm, deciding, warm but firm",
    "少赚一点?": "surprised, uncertain",
    "对。宁可少赚,不能骗人。": "serious, kind, deliberate, a teacher's weight",
    "爸,我错了。": "ashamed, sincere, quiet",
    "明天一早去买骨头。": "softening, fatherly, a faint smile",
    "好,我跟您一起去。": "relieved, grateful, warm",
}
CAST = {
    "W": (
        "YUEYAO",
        "beautiful 24-year-old Chinese woman, elegant updo with a white jade hairpin, delicate pearl earrings, natural makeup, elegant pale-pink silk hanfu with embroidered cuffs; soft clear young female voice",
        "her",
        "female",
        "right",
    ),
    "Q": (
        "QINGHAN",
        "handsome 30-year-old Chinese man, neat topknot with a jade-green hairpin, fine indigo robe with a clean white apron, smooth clean face; low calm male voice",
        "his",
        "male",
        "left",
    ),
    "L": (
        "LAODIE",
        "stout 63-year-old Chinese man, broad square face, grey-streaked brows, short grey stubble, neat dark cloth cap, crisp blue-grey cotton robe; low, hoarse, slightly raspy voice of a 70-year-old grandfather, clearly older than QINGHAN",
        "his",
        "male",
        "right",
    ),
}
HALL = "SETTING: the clean, bright dining hall of a small ancient Chinese noodle house in soft afternoon light: polished dark wooden table, whitewashed walls, paper lanterns, a vase of plum blossom, latticed window."
KIT = "SETTING: the clean, bright kitchen of a small ancient Chinese noodle house: big iron pot on a brick stove with gentle steam, hanging copper ladles, scrubbed wooden counter, warm daylight."
PART = {  # video -> shot key -> (setting, who, partner-side note, lines)
    "01": {
        "sW1": (
            HALL,
            "W",
            "YUEYAO sits at the table, a bowl of beef noodles in front of her, spoon resting in the bowl.",
            ["清寒,来碗牛肉面,不要香菜。", "药店没人,我饿了。"],
        ),
        "sW1b": (
            HALL,
            "W",
            "YUEYAO sits at the table, a bowl of beef noodles in front of her, spoon resting in the bowl.",
            ["嗯……今天的汤有点淡。", "当然,我天天来吃。"],
        ),
        "sW2": (
            HALL,
            "W",
            "YUEYAO sits at the table, a bowl of beef noodles in front of her.",
            ["贵了多少?", "你爸知道吗?", "我不说,可是他会尝出来。"],
        ),
        "sM1": (
            HALL,
            "Q",
            "QINGHAN stands beside the table in his white apron.",
            ["好,不要香菜。今天这么早?", "你尝出来了?", "骨头贵了,我少放了一点。"],
        ),
        "sM2": (
            HALL,
            "Q",
            "QINGHAN stands beside the table in his white apron.",
            ["贵了一半。", "不知道,别告诉他。"],
        ),
    },
    "02": {
        "sL1": (
            KIT,
            "L",
            "LAODIE stands in the kitchen holding a small white soup bowl at chest height.",
            ["清寒,这汤怎么这么淡?", "所以你就少放了?", "一点也是骗人。"],
        ),
        "sL2": (
            KIT,
            "L",
            "LAODIE stands in the kitchen holding a small white soup bowl at chest height.",
            ["钱不够,我们少赚一点。", "对。宁可少赚,不能骗人。", "明天一早去买骨头。"],
        ),
        "sQ1": (
            KIT,
            "Q",
            "QINGHAN stands by the stove.",
            ["爸,骨头贵了一半。", "就少放了一点。", "那怎么办?钱不够啊。"],
        ),
        "sQ2": (
            KIT,
            "Q",
            "QINGHAN stands by the stove.",
            ["少赚一点?", "爸,我错了。", "好,我跟您一起去。"],
        ),
    },
}
for v, shots in PART.items():
    for key, (setting, k, pose, lines) in shots.items():
        n, desc, pos, sex, side = CAST[k]
        # start 0.6 s, each line then 1.6 s pause (listening, lips closed)
        RATE, PAUSE = (5.8, 0.7) if v == "02" else (4.5, 1.6)
        VOICE_V = VOICE.replace(
            "about 4.5 syllables per second for every line",
            "fast natural conversational speed of about 5.8 syllables per second, the brisk relaxed pace of two people chatting at home, never never drawn out, the reply follows almost at once",
        )
        if v != "02":
            VOICE_V = VOICE
        t = 0.6
        sc = []
        for ln in lines:
            syl = sum(1 for ch in ln if "一" <= ch <= "鿿")
            e = t + syl / RATE + 0.2
            sc.append(
                f'{t:.1f}-{e:.1f} s: {n} speaks, {EMO.get(ln, "natural")} (only {pos} lips move, {sex} voice): "{ln}"'
            )
            sc.append(
                f"{e:.1f}-{e + PAUSE:.1f} s: {n} is silent and listens to {pos} partner off-screen: lips pressed together, jaw perfectly still, a slight attentive look."
            )
            t = e + PAUSE
        sc.append(f"{min(t, 9.9):.1f}-10.0 s: silent, lips closed, calm resting pose.")
        txt = (
            f"NO TEXT ON SCREEN. Photorealistic live-action footage, real person with natural skin texture, no CGI look. 10 seconds.\n\n"
            f"CAST (keep face, hairstyle, outfit and voice identical):\n{n}: {desc}.\n\n{setting} {pose}\n\n{VOICE_V}\n\n"
            f"CAMERA: One continuous take, steady locked camera, no zoom, no cut, vertical 9:16 waist-up single shot of {n} ALONE. The attached image is the exact first frame: keep the face, angle, framing and camera position. "
            f"The body faces the camera; the head turns slightly toward {pos} conversation partner who is just outside the frame on the {side} (front three-quarter view, both eyes and the whole mouth visible, never side profile). "
            f"Eyes rest on the partner's face off-screen, never on the table, the floor or the lens. Nobody else is ever visible, nobody else speaks, no second voice. Subtle breathing and blinks only; no nodding, no random gestures.\n\n"
            f"LIP SYNC: only {n}'s lips move, and only while {pos} line is spoken; between lines the lips are closed and still. Say every line exactly as written, every syllable.\n\n"
            f"SCRIPT (timed):\n" + "\n".join(sc) + "\n"
        )
        (M / f"jinxiu-{v}" / f"{key}.txt").write_text(txt)
        (M / f"jinxiu-{v}" / f"{key}.script").write_text(
            "".join(f"{'W' if k == 'W' else 'M'}: {ln}\n" for ln in lines)
        )
print("ok")
