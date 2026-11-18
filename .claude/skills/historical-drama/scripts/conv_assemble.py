#!/usr/bin/env python3
"""Conversation scene: A (sample) + B + C, 16:9, subtitles zh/pinyin/vi, music bed. Usage: conv_assemble.py OUT.mp4"""

import sys
import tempfile
from pathlib import Path

import assemble169 as a

M = Path.home() / "Movies/museai"
CLIPS = [(M / "dr-ep1-sample.mp4", 10), (M / "dr-conv-B.mp4", 10), (M / "dr-conv-C.mp4", 10)]
CUES = [
    (
        0,
        0.5,
        3.2,
        "清寒,来碗面,不要香菜,你知道的。",
        "Qīnghán, lái wǎn miàn, búyào xiāngcài, nǐ zhīdào de.",
        "Thanh Hàn, cho bát mì, không rau mùi, anh biết mà.",
    ),
    (
        0,
        3.6,
        5.5,
        "知道。今天怎么这么早?",
        "Zhīdào. Jīntiān zěnme zhème zǎo?",
        "Biết rồi. Sao hôm nay em đến sớm thế?",
    ),
    (0, 5.9, 7.6, "药铺没人,我饿了。", "Yàopù méi rén, wǒ è le.", "Tiệm thuốc vắng, em đói rồi."),
    (0, 8.0, 9.3, "坐吧,马上好。", "Zuò ba, mǎshàng hǎo.", "Ngồi đi, xong ngay."),
    (
        1,
        1.0,
        2.9,
        "小意今天吃了多少?",
        "Xiǎoyì jīntiān chī le duōshao?",
        "Hôm nay Tiểu Ý ăn được bao nhiêu?",
    ),
    (1, 4.2, 5.7, "只吃了一口包子。", "Zhǐ chī le yì kǒu bāozi.", "Chỉ ăn một miếng bánh bao."),
    (
        1,
        6.3,
        7.8,
        "她最近吃得太少了。",
        "Tā zuìjìn chī de tài shǎo le.",
        "Dạo này con bé ăn quá ít.",
    ),
    (
        1,
        8.1,
        9.9,
        "我知道,她不肯跟我说。",
        "Wǒ zhīdào, tā bù kěn gēn wǒ shuō.",
        "Anh biết, con bé không chịu nói.",
    ),
    (
        2,
        0.6,
        3.0,
        "别担心,小孩子都这样。",
        "Bié dānxīn, xiǎoháizi dōu zhèyàng.",
        "Đừng lo, trẻ con đều vậy mà.",
    ),
    (2, 4.4, 5.7, "谢谢你,月瑶。", "Xièxie nǐ, Yuèyáo.", "Cảm ơn em, Nguyệt Dao."),
    (
        2,
        6.2,
        8.5,
        "这碗汤,今天有点淡哦。",
        "Zhè wǎn tāng, jīntiān yǒudiǎn dàn o.",
        "Bát canh hôm nay hơi nhạt đấy nhé.",
    ),
    (
        2,
        9.0,
        10.0,
        "你尝出来了?别告诉我爸。",
        "Nǐ cháng chūlái le? Bié gàosu wǒ bà.",
        "Em nếm ra rồi à? Đừng nói với cha anh.",
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
