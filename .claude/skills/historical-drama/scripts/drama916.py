#!/usr/bin/env python3
"""9:16 conversation episode: 6 x 10 s two-person clips (16:9 renders) on a blurred 1080x1920 frame,
title band on top, one vocabulary card at a time under the picture (gold glow on its spoken word),
zh / pinyin / vi subtitles, guzheng bed, then a slow flashcard review of the new words (word spoken by TTS,
about 2 s pause with its card up) - the EVERYDAY CHINESE rules (muse-video SKILL.md step 5).
Usage: uv run --with pillow --with numpy --with edge-tts python drama916.py WORKDIR OUT.mp4
WORKDIR/clips/{A..F}.mp4 expected (or edit CLIPS)."""

import asyncio
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
VY, VH = 250, 608  # picture box y, height
ZH = "/System/Library/Fonts/STHeiti Medium.ttc"
LAT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
TITLE = ("锦绣人生 · 第一集", "Tập 1 · Bát mì cuối cùng")
VOICE = "zh-CN-XiaoxiaoNeural"
SLOT = 3.0  # review: seconds per word (word + ~2 s pause)

# (clip index, start, end, zh, pinyin, vi)
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
    (
        3,
        0.6,
        3.0,
        "骨头呢?你的骨头呢?",
        "Gǔtou ne? Nǐ de gǔtou ne?",
        "Xương đâu? Xương của con đâu?",
    ),
    (
        3,
        4.3,
        6.4,
        "贵了,爸。贵了很多。",
        "Guì le, bà. Guì le hěn duō.",
        "Đắt lên rồi bố. Đắt lên nhiều lắm.",
    ),
    (3, 6.5, 7.9, "贵也不能骗人!", "Guì yě bù néng piàn rén!", "Đắt cũng không được lừa người!"),
    (
        3,
        8.0,
        10.0,
        "我没骗人,只是少放了点。",
        "Wǒ méi piàn rén, zhǐshì shǎo fàng le diǎn.",
        "Con không lừa ai, chỉ bỏ ít đi chút thôi.",
    ),
    (4, 0.8, 2.3, "一点儿也是骗!", "Yìdiǎnr yě shì piàn!", "Dù chỉ một chút cũng là lừa!"),
    (
        4,
        2.8,
        5.8,
        "那您说怎么办?钱呢?",
        "Nà nín shuō zěnme bàn? Qián ne?",
        "Vậy bố nói làm sao? Tiền đâu?",
    ),
    (
        4,
        5.9,
        7.6,
        "钱的事,你不用管。",
        "Qián de shì, nǐ búyòng guǎn.",
        "Chuyện tiền, con không cần lo.",
    ),
    (
        4,
        8.1,
        10.0,
        "您总是这样,什么都不说!",
        "Nín zǒngshì zhèyàng, shénme dōu bù shuō!",
        "Bố lúc nào cũng vậy, chẳng nói gì cả!",
    ),
    (
        5,
        1.1,
        4.4,
        "小意,对不起,吓到你了。",
        "Xiǎoyì, duìbuqǐ, xiàdào nǐ le.",
        "Tiểu Ý, xin lỗi, bố làm con sợ rồi.",
    ),
    (5, 4.4, 6.5, "爷爷不要生气。", "Yéye búyào shēngqì.", "Ông nội đừng giận."),
    (
        5,
        6.5,
        8.7,
        "爷爷没生气,他累了。",
        "Yéye méi shēngqì, tā lèi le.",
        "Ông nội không giận, ông mệt thôi.",
    ),
    (
        5,
        8.7,
        10.0,
        "妈妈在,爷爷不这样。",
        "Māma zài, yéye bú zhèyàng.",
        "Có mẹ ở đây, ông nội sẽ không thế.",
    ),
]
# (clip, show from, show until, zh, pinyin, vi): shown from the line that says it; also the review list order
CARDS = [
    (0, 1.6, 5.4, "香菜", "xiāngcài", "rau mùi"),
    (0, 5.9, 9.8, "药铺", "yàopù", "tiệm thuốc"),
    (3, 0.6, 4.2, "骨头", "gǔtou", "xương"),
    (3, 4.3, 6.45, "贵", "guì", "đắt"),
    (3, 6.5, 9.9, "骗人", "piàn rén", "lừa người"),
    (5, 4.4, 8.7, "生气", "shēngqì", "giận, tức giận"),
]


def fnt(p, s):
    return ImageFont.truetype(p, s)


def fit(p, s, text, maxw):
    while s > 20 and fnt(p, s).getlength(text) > maxw:
        s -= 2
    return fnt(p, s)


def ctr(d, y, text, f, fill, stroke=0, cx=W / 2):
    d.text(
        (cx - d.textlength(text, font=f) / 2, y),
        text,
        font=f,
        fill=fill,
        stroke_width=stroke,
        stroke_fill=(0, 0, 0),
    )


def title_png(path, zh, vi):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ctr(d, 80, zh, fnt(ZH, 78), (255, 255, 255), 4)
    ctr(d, 170, vi, fnt(LAT, 40), (255, 214, 120), 3)
    im.save(path)


def sub_png(path, zh, py, vi):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ctr(d, 1130, zh, fit(ZH, 62, zh, 980), (255, 255, 255), 5)
    ctr(d, 1215, py, fit(LAT, 36, py, 980), (255, 214, 120), 4)
    ctr(d, 1270, vi, fit(LAT, 38, vi, 980), (255, 255, 255), 4)
    im.save(path)


def vocab_png(path, zh, py, vi, lit):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fz, fp, fv = fnt(ZH, 84), fnt(LAT, 40), fnt(LAT, 36)
    w = int(
        max(
            d.textlength(zh, font=fz)
            + 60
            + max(d.textlength(py, font=fp), d.textlength(vi, font=fv))
            + 80,
            560,
        )
    )
    box = ((W - w) // 2, 880, (W + w) // 2, 1060)
    if lit:
        d.rounded_rectangle(
            (box[0] - 8, box[1] - 8, box[2] + 8, box[3] + 8), 36, fill=(255, 200, 60, 255)
        )
    d.rounded_rectangle(box, 30, fill=(255, 250, 240, 245))
    zx = box[0] + 40
    d.text((zx, box[1] + 42), zh, font=fz, fill=(25, 25, 35))
    tx = zx + d.textlength(zh, font=fz) + 40
    d.text((tx, box[1] + 36), py, font=fp, fill=(190, 60, 70))
    d.text((tx, box[1] + 98), vi, font=fv, fill=(55, 55, 70))
    im.save(path)


def review_png(path, i, n, zh, py, vi, lit):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    box = (90, 600, 990, 1200)
    if lit:
        d.rounded_rectangle(
            (box[0] - 10, box[1] - 10, box[2] + 10, box[3] + 10), 50, fill=(255, 200, 60, 255)
        )
    d.rounded_rectangle(box, 44, fill=(255, 250, 240, 250))
    ctr(d, 650, zh, fit(ZH, 230, zh, 800), (25, 25, 35))
    ctr(d, 940, py, fit(LAT, 80, py, 800), (190, 60, 70))
    ctr(d, 1050, vi, fit(LAT, 56, vi, 800), (55, 55, 70))
    ctr(d, 1230, f"{i}/{n}", fnt(LAT, 44), (255, 255, 255), 4)
    im.save(path)


def head_png(path, zh, vi):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    ctr(d, 250, zh, fnt(ZH, 96), (255, 255, 255), 5)
    ctr(d, 370, vi, fnt(LAT, 50), (255, 214, 120), 4)
    im.save(path)


def run(a):
    r = subprocess.run(a, capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr[-1800:])


def tts(words, tmp):
    import edge_tts

    async def go():
        for i, w in enumerate(words):
            await edge_tts.Communicate(w, VOICE, rate="-10%").save(str(tmp / f"w{i}.mp3"))

    asyncio.run(go())


def main(work, out):
    work, tmp = Path(work), Path(tempfile.mkdtemp())
    names = "ABCDEF"
    segs = []
    for i, n in enumerate(names):
        o = tmp / f"s{i}.mp4"
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(work / "clips" / f"{n}.mp4"),
                "-filter_complex",
                f"[0:v]fps=24,split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:6,eq=brightness=-0.18[bg];"
                f"[b]scale={W}:{VH}[fg];[bg][fg]overlay=0:{VY},format=yuv420p[v]",
                "-map",
                "[v]",
                "-map",
                "0:a",
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
        segs.append(o)
    # review segment: last frame of F blurred, words by TTS
    n_rev = len(CARDS)
    rev_len = SLOT * n_rev + 1.0
    run(
        [
            "ffmpeg",
            "-y",
            "-sseof",
            "-0.2",
            "-i",
            str(work / "clips" / "F.mp4"),
            "-frames:v",
            "1",
            str(tmp / "last.png"),
        ]
    )
    words = [c[3] for c in CARDS]
    tts(words, tmp)
    ins, fl = [], []
    for i in range(n_rev):
        ins += ["-i", str(tmp / f"w{i}.mp3")]
        fl.append(
            f"[{i}:a]adelay={int((0.45 + i * SLOT) * 1000)}|{int((0.45 + i * SLOT) * 1000)},aformat=channel_layouts=stereo,volume=2.2[w{i}]"
        )
    fl.append(
        "".join(f"[w{i}]" for i in range(n_rev))
        + f"amix=inputs={n_rev}:normalize=0,apad=whole_dur={rev_len},aresample=48000[a]"
    )
    run(
        [
            "ffmpeg",
            "-y",
            *ins,
            "-filter_complex",
            ";".join(fl),
            "-map",
            "[a]",
            "-t",
            str(rev_len),
            str(tmp / "rev.wav"),
        ]
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-framerate",
            "24",
            "-t",
            str(rev_len),
            "-i",
            str(tmp / "last.png"),
            "-i",
            str(tmp / "rev.wav"),
            "-vf",
            f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=40:6,eq=brightness=-0.3,format=yuv420p",
            "-c:v",
            "libx264",
            "-crf",
            "17",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-shortest",
            str(tmp / "rev.mp4"),
        ]
    )
    segs.append(tmp / "rev.mp4")
    (tmp / "l.txt").write_text("".join(f"file '{p}'\n" for p in segs))
    run(
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
    total = 60 + rev_len
    run(
        [
            sys.executable,
            str(Path(__file__).parent / "musicbed.py"),
            f"{total:.1f}",
            str(tmp / "bed.wav"),
        ]
    )

    ins, filt, last, n = ["-i", str(tmp / "j.mp4"), "-i", str(tmp / "bed.wav")], [], "0:v", 2

    def add(png, a, b):
        nonlocal ins, last, n
        ins += ["-i", str(png)]
        filt.append(f"[{last}][{n}:v]overlay=enable='between(t,{a:.2f},{b:.2f})'[v{n}]")
        last, n = f"v{n}", n + 1

    title_png(tmp / "title.png", *TITLE)
    add(tmp / "title.png", 0, 60)
    for k, (ci, s, e, zh, py, vi) in enumerate(CUES):
        sub_png(tmp / f"sub{k}.png", zh, py, vi)
        add(tmp / f"sub{k}.png", ci * 10 + s, ci * 10 + e)
    for k, (ci, s, e, zh, py, vi) in enumerate(CARDS):
        vocab_png(tmp / f"vl{k}.png", zh, py, vi, True)
        vocab_png(tmp / f"vn{k}.png", zh, py, vi, False)
        add(tmp / f"vl{k}.png", ci * 10 + s, ci * 10 + s + 0.6)
        add(tmp / f"vn{k}.png", ci * 10 + s + 0.6, ci * 10 + e)
    head_png(tmp / "rh.png", "复习一下", "Ôn lại từ mới")
    add(tmp / "rh.png", 60, total)
    for k, (_ci, _s, _e, zh, py, vi) in enumerate(CARDS):
        t0 = 60 + k * SLOT
        review_png(tmp / f"rl{k}.png", k + 1, n_rev, zh, py, vi, True)
        review_png(tmp / f"rn{k}.png", k + 1, n_rev, zh, py, vi, False)
        add(tmp / f"rl{k}.png", t0, t0 + 1.2)
        add(tmp / f"rn{k}.png", t0 + 1.2, t0 + SLOT)
    filt.append(
        "[1:a]volume=0.5,aformat=channel_layouts=stereo[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]"
    )
    run(
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
    print(out, round(total, 1), "s")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
