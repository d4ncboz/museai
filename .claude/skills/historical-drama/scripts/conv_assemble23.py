#!/usr/bin/env python3
"""Conversation scene: A (sample) + B + C, 16:9, subtitles zh/pinyin/vi, music bed. Usage: conv_assemble.py OUT.mp4"""

import sys
import tempfile
from pathlib import Path

import assemble169 as a

M = Path.home() / "Movies/museai"
CLIPS = [(M / "dr-conv-D.mp4", 10), (M / "dr-conv-E.mp4", 10), (M / "dr-conv-F.mp4", 10)]
CUES = [
    (
        0,
        0.6,
        3.0,
        "骨头呢?你的骨头呢?",
        "Gǔtou ne? Nǐ de gǔtou ne?",
        "Xương đâu? Xương của con đâu?",
    ),
    (
        0,
        4.3,
        6.4,
        "贵了,爸。贵了很多。",
        "Guì le, bà. Guì le hěn duō.",
        "Đắt lên rồi bố. Đắt lên nhiều lắm.",
    ),
    (0, 6.5, 7.9, "贵也不能骗人!", "Guì yě bù néng piàn rén!", "Đắt cũng không được lừa người!"),
    (
        0,
        8.0,
        10.0,
        "我没骗人,只是少放了点。",
        "Wǒ méi piàn rén, zhǐshì shǎo fàng le diǎn.",
        "Con không lừa ai, chỉ bỏ ít đi chút thôi.",
    ),
    (1, 0.8, 2.3, "一点儿也是骗!", "Yìdiǎnr yě shì piàn!", "Dù chỉ một chút cũng là lừa!"),
    (
        1,
        2.8,
        5.8,
        "那您说怎么办?钱呢?",
        "Nà nín shuō zěnme bàn? Qián ne?",
        "Vậy bố nói làm sao? Tiền đâu?",
    ),
    (
        1,
        5.9,
        7.6,
        "钱的事,你不用管。",
        "Qián de shì, nǐ búyòng guǎn.",
        "Chuyện tiền, con không cần lo.",
    ),
    (
        1,
        8.1,
        10.0,
        "您总是这样,什么都不说!",
        "Nín zǒngshì zhèyàng, shénme dōu bù shuō!",
        "Bố lúc nào cũng vậy, chẳng nói gì cả!",
    ),
    (
        2,
        1.1,
        4.4,
        "小意,对不起,吓到你了。",
        "Xiǎoyì, duìbuqǐ, xiàdào nǐ le.",
        "Tiểu Ý, xin lỗi, bố làm con sợ rồi.",
    ),
    (2, 4.4, 6.5, "爷爷不要生气。", "Yéye búyào shēngqì.", "Ông nội đừng giận."),
    (
        2,
        6.5,
        8.7,
        "爷爷没生气,他累了。",
        "Yéye méi shēngqì, tā lèi le.",
        "Ông nội không giận, ông mệt thôi.",
    ),
    (
        2,
        8.7,
        10.0,
        "妈妈在,爷爷不这样。",
        "Māma zài, yéye bú zhèyàng.",
        "Có mẹ ở đây, ông nội sẽ không thế.",
    ),
]
out = sys.argv[1]
tmp = Path(tempfile.mkdtemp())
parts = []
for i, (p, _d) in enumerate(CLIPS):
    o = tmp / f"{i}.mp4"
    a.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(p),
            "-vf",
            f"scale={a.W}:{a.H}:force_original_aspect_ratio=increase,crop={a.W}:{a.H},fps=24,format=yuv420p",
            "-af",
            "aresample=48000,loudnorm=I=-18:TP=-2,aformat=channel_layouts=stereo",
            "-ar",
            "48000",
            "-c:v",
            "libx264",
            "-crf",
            "17",
            "-c:a",
            "aac",
            str(o),
        ]
    )
    parts.append(o)
(tmp / "l.txt").write_text("".join(f"file '{p}'\n" for p in parts))
a.run(
    [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(tmp / "l.txt"),
        "-c",
        "copy",
        str(tmp / "j.mp4"),
    ]
)
a.run([sys.executable, str(Path(__file__).parent / "musicbed.py"), "30", str(tmp / "bed.wav")])
ins, filt, last = ["-i", str(tmp / "j.mp4"), "-i", str(tmp / "bed.wav")], [], "0:v"
for n, (ci, s, e, zh, py, vi) in enumerate(CUES, 2):
    a.sub_png(tmp / f"s{n}.png", zh, py, vi)
    ins += ["-i", str(tmp / f"s{n}.png")]
    filt.append(
        f"[{last}][{n}:v]overlay=enable='between(t,{ci * 10 + s:.2f},{ci * 10 + e:.2f})'[v{n}]"
    )
    last = f"v{n}"
filt.append(
    "[1:a]volume=0.5,aformat=channel_layouts=stereo[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]"
)
a.run(
    [
        "ffmpeg",
        "-y",
        *ins,
        "-filter_complex",
        ";".join(filt),
        "-map",
        f"[{last}]",
        "-map",
        "[a]",
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        out,
    ]
)
print(out)
