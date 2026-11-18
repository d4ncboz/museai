#!/usr/bin/env python3
"""Shot list for ep1 parts 1 + 5 (hook + cliffhanger) -> scene-still jobs and muse-video prompts.

  shots.py prompts OUTDIR     write OUTDIR/<id>.txt (video prompt) + <id>.dlg (dialogue for budget.py)
  shots.py stills             print the scene lines (id|keys|text) to feed bank.py scene
Edit SHOTS to change a shot; the shared blocks (look, voice, camera) live once below.
"""

import sys
from pathlib import Path

LOOK = (
    "NO TEXT ON SCREEN. Photorealistic live-action footage, 16:9, filmed on a real cinema camera, warm natural "
    "colour. Real people with natural skin texture; no plastic, waxy or CGI look. Elegant, clean, tidy, well-kept set."
)
VOICE = (
    "Natural Standard Mandarin (Putonghua), accurate tones, every syllable crisp and separate, everyday pace "
    "about 4.5 syllables per second. Clean close-mic voice. Very quiet guzheng and flute music far below the "
    "voices; no other background noise."
)
CAM = (
    "Steady locked camera, no zoom, no pull-out, no cut. The attached image is the exact first frame: keep faces, "
    "angles, framing and camera position. Faces stay front three-quarter toward the camera, never side profile. "
    "Each person's eyes rest on the other person's face. Nobody else enters the frame. Fluid natural motion; "
    "subtle breathing and blinks only; no repetitive nodding or random gestures."
)
LIP = (
    "Only the speaking person's lips move; everyone else keeps lips gently closed and still. The voice comes only "
    "from the labelled speaker's own lips. Speak the lines exactly as written."
)

CAST = {
    "L": "LAODIE (顾老爹): 63-year-old stout Chinese man, broad square face, grey-streaked brows, short grey stubble, white at the temples, neat dark cloth cap, clean crisp blue-grey cotton robe with dark trim; deep gruff male voice.",
    "Q": "QINGHAN (顾清寒): 30-year-old handsome Chinese man, neat topknot with a jade-green hairpin, small pale scar through his left eyebrow, fine deep-indigo robe with tonal cloud embroidery and jade pendant (kitchen apron over it); low calm male voice.",
    "X": "XIAOYI (顾小意): 6-year-old Chinese girl, two neat hair buns with pink silk flower pins, clean pink cotton hanfu with tiny flower cuffs, a small cloth rabbit in her sash.",
}
SET_HALL = (
    "Setting: the dining hall of the 归味楼 noodle house in late afternoon light: clean polished wooden tables and "
    "stools, spotless blue-and-white bowls, whitewashed walls, paper lanterns, a vase of fresh plum blossom, "
    "latticed windows. Tidy and bright."
)
SET_KITCHEN = (
    "Setting: the clean, bright kitchen of the 归味楼 noodle house: a big iron pot on a brick stove, hanging "
    "copper ladles, scrubbed wooden counters, steam, warm daylight from a high window."
)
SET_NIGHT = (
    "Setting: the same kitchen at night, only one small oil lamp lit on the counter, warm dim amber light, "
    "clean and tidy, brick stove, scrubbed wood."
)
SET_DOOR = (
    "Setting: the front door of the noodle house at night: inside, warm dim lamplight; outside, a quiet "
    "stone lane lit by one red paper lantern."
)

# id, duration s, keys, still text, action/script, dialogue lines [(speaker, text)]
SHOTS = [
    (
        "p1-01",
        8,
        "L",
        f"{SET_KITCHEN} A stout 63-year-old man in a cloth cap stands at the big pot holding a spoon, front three-quarter view, tasting expression. Medium shot.",
        "0-3 s: LAODIE lifts a spoonful of soup from the big pot, blows on it, tastes it. 3-6 s: his face changes slowly: brows draw together, eyes narrow, a hard stillness. 6-8 s: he lowers the spoon and stares into the pot. No dialogue, no speech.",
        [],
    ),
    (
        "p1-02",
        6,
        "L Q",
        f"{SET_HALL} On the right, a stout 63-year-old man in a cloth cap holds a white bowl of soup; on the left, a handsome 30-year-old man in an indigo robe with an apron wipes his hands on a cloth. They face each other across a table, both front three-quarter toward the camera. Mid two-shot.",
        "0.4-1.5 s: LAODIE speaks (his lips move, deep voice), holding the bowl out; QINGHAN listens, lips closed, wiping his hands.\n2.0-3.1 s: QINGHAN speaks (his lips move), calm; LAODIE listens, lips closed, jaw set.\n3.6-5.2 s: LAODIE speaks (his lips move), firmer, stern; QINGHAN listens, lips closed.\n5.2-6.0 s: both still.",
        [("L", "这是什么?"), ("Q", "爸,是汤。"), ("L", "这不是我们的汤!")],
    ),
    (
        "p1-03",
        8,
        "L Q",
        f"{SET_HALL} On the right, a stout 63-year-old man in a cloth cap holds a white bowl; on the left, a handsome 30-year-old man in an indigo robe stands silent. Mid two-shot, front three-quarter.",
        "0-1.5 s: LAODIE grips the bowl, QINGHAN stands still, lips closed. 1.5-3 s: LAODIE lifts the bowl and dashes it to the floor; it shatters; both freeze. 3.5-5.5 s: LAODIE speaks (his lips move, deep, loud, angry): the line; QINGHAN lips closed, stunned. 5.5-8 s: silence, both still.",
        [("L", "今天关门!")],
    ),
    (
        "p1-04",
        5,
        "X",
        f"{SET_HALL} A 6-year-old girl with two hair buns and pink flower pins stands in the corner by a table holding a pair of chopsticks, front view, wide frightened eyes. Close medium shot.",
        "0-1.5 s: XIAOYI stands still, eyes wide, lips closed. 1.5-2.5 s: the chopsticks slip from her fingers and fall. 2.5-5 s: she stares ahead, lips closed. No dialogue.",
        [],
    ),
    (
        "p1-05",
        5,
        "Q",
        f"{SET_HALL} A handsome 30-year-old man in an indigo robe, front three-quarter, close medium shot, among tables.",
        "0-5 s: QINGHAN stands frozen, lips slightly parted as if to speak but no words come, eyes glistening, a slow breath. No dialogue, no speech.",
        [],
    ),
    (
        "p5-01",
        8,
        "L",
        f"{SET_NIGHT} A stout 63-year-old man in a cloth cap kneels in front of the brick stove, hand on the stove wall, front three-quarter, lit by a single oil lamp.",
        "0-3 s: LAODIE strokes the brick wall of the stove. 3-6 s: he pulls out one loose brick and takes out a thick folded paper. 6-8 s: he holds the paper, looks at it. No dialogue.",
        [],
    ),
    (
        "p5-02",
        8,
        "L",
        f"{SET_NIGHT} A stout 63-year-old man in a cloth cap sits holding an unfolded paper by the oil lamp, front three-quarter view, sad.",
        "0-3 s: LAODIE reads the paper, lips closed, eyes moving. 3-5 s: he folds the paper slowly. 5-7 s: LAODIE speaks (his lips move), low, hoarse but clearly audible, not whispering: the line. 7-8 s: he tucks the paper away.",
        [("L", "对不起,周婉……")],
    ),
    (
        "p5-03",
        6,
        "L",
        f"{SET_NIGHT} A stout 63-year-old man in a cloth cap by the oil lamp, front three-quarter, looking toward a door off-screen.",
        "0-1.5 s: LAODIE sits still. 1.5-3.5 s: three slow knocks on a door; LAODIE lifts his head and turns it toward the door, lips closed. 3.5-5 s: he stands and blows out the lamp. No dialogue.",
        [],
    ),
    (
        "p5-04",
        6,
        "L",
        f"{SET_DOOR} Inside the open door crack, a stout 63-year-old man in a cloth cap, front three-quarter; outside, in the lantern light, only the black sleeves embroidered with gold thread of a person standing with their back to the camera at the edge of the frame, face never seen.",
        "0-2 s: LAODIE opens the door a crack, lips closed, wary. 2.5-4.2 s: the STRANGER speaks from outside (calm, low male voice, mouth never visible, back to the camera): the line. 4.2-6 s: LAODIE's face goes pale, lips closed, frozen.",
        [("S", "老先生,日子到了。")],
    ),
    (
        "p5-05",
        5,
        "L",
        f"{SET_DOOR} Close medium shot of a stout 63-year-old man in a cloth cap at a door in warm dim lamplight, front three-quarter, pale and stricken.",
        "0-5 s: LAODIE stands frozen, lips closed, eyes wide and unblinking, the red lantern light flickering faintly on his face, a slow breath. No dialogue.",
        [],
    ),
]


def prompt(shot):
    sid, dur, keys, still, action, dlg = shot
    cast = "\n".join(CAST[k] for k in keys.split())
    if sid == "p5-04":
        cast += "\nSTRANGER: only black sleeves embroidered with gold thread; stays at the edge of the frame, back to the camera, face never seen; calm low male voice."
    lines = "\n".join(f'{s}: "{t}"' for s, t in dlg)
    return (
        f"{LOOK}\n\nPART {sid} - {dur} seconds.\n\nCAST (keep faces, hair, outfits and voices identical):\n{cast}\n\n"
        f"{still.split('. ')[0] if False else ''}"
        f"{[SET_HALL, SET_KITCHEN, SET_NIGHT, SET_DOOR][[SET_HALL in still, SET_KITCHEN in still, SET_NIGHT in still, SET_DOOR in still].index(True)]}\n\n"
        f"VOICE: {VOICE}\n\nCAMERA: {CAM}\n\nLIP SYNC: {LIP}\n\nACTION AND SCRIPT (timed):\n{action}\n"
        + (f"\nDIALOGUE:\n{lines}\n" if lines else "\nNo dialogue: nobody speaks in this shot.\n")
    )


if __name__ == "__main__":
    if sys.argv[1] == "stills":
        for s in SHOTS:
            print(f"{s[0]}|{s[2]}|{s[3]}")
    else:
        out = Path(sys.argv[2])
        out.mkdir(parents=True, exist_ok=True)
        for s in SHOTS:
            (out / f"{s[0]}.txt").write_text(prompt(s), encoding="utf-8")
            (out / f"{s[0]}.dlg").write_text(
                "\n".join(f"{a}: {b}" for a, b in s[5]) + ("\n" if s[5] else ""), encoding="utf-8"
            )
        print(len(SHOTS), "shots ->", out)
