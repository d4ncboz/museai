#!/usr/bin/env python3
"""Usage: esrgan_cuda.py IN_DIR OUT_DIR WEIGHTS.pth [TILE]

Real-ESRGAN x4plus on an NVIDIA GPU with PyTorch: every PNG in IN_DIR comes out 4x larger in OUT_DIR
under the same name. upscale.sh uses it where the ncnn-vulkan build cannot run: Colab has CUDA but no
Vulkan driver, so realesrgan-ncnn-vulkan exited 255 on every muse-renderer job (2026-11-18).
The network is RRDBNet as in xinntao/Real-ESRGAN, written out here because basicsr no longer imports
with current torchvision. Weights: RealESRGAN_x4plus.pth (key params_ema). fp16, tiles of TILE px
(default 512, 0 = whole frame) with a 10 px overlap so seams do not show.
"""

import sys
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.nn import functional as F


class RDB(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
        self.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
        self.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
        self.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
        self.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        return self.conv5(torch.cat((x, x1, x2, x3, x4), 1)) * 0.2 + x


class RRDB(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.rdb1, self.rdb2, self.rdb3 = RDB(nf, gc), RDB(nf, gc), RDB(nf, gc)

    def forward(self, x):
        return self.rdb3(self.rdb2(self.rdb1(x))) * 0.2 + x


class RRDBNet(nn.Module):
    def __init__(self, nf=64, nb=23, gc=32):
        super().__init__()
        self.conv_first = nn.Conv2d(3, nf, 3, 1, 1)
        self.body = nn.Sequential(*[RRDB(nf, gc) for _ in range(nb)])
        self.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_last = nn.Conv2d(nf, 3, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, True)

    def forward(self, x):
        feat = self.conv_first(x)
        feat = feat + self.conv_body(self.body(feat))
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode="nearest")))
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode="nearest")))
        return self.conv_last(self.lrelu(self.conv_hr(feat)))


def upscale(net, img, tile, pad=10):
    """img: 1x3xHxW in [0, 1]. Tiles overlap by pad px and only their inner part is kept."""
    if not tile:
        return net(img)
    _, _, h, w = img.shape
    out = img.new_zeros((1, 3, h * 4, w * 4))
    for y in range(0, h, tile):
        for x in range(0, w, tile):
            y0, x0, y1, x1 = (
                max(y - pad, 0),
                max(x - pad, 0),
                min(y + tile + pad, h),
                min(x + tile + pad, w),
            )
            part = net(img[:, :, y0:y1, x0:x1])
            ty, tx = (y - y0) * 4, (x - x0) * 4
            th, tw = (min(y + tile, h) - y) * 4, (min(x + tile, w) - x) * 4
            out[:, :, y * 4 : y * 4 + th, x * 4 : x * 4 + tw] = part[
                :, :, ty : ty + th, tx : tx + tw
            ]
    return out


def main(src, dst, weights, tile="512"):
    if not torch.cuda.is_available():
        sys.exit("esrgan_cuda: no CUDA GPU")
    state = torch.load(weights, map_location="cpu")
    net = RRDBNet()
    net.load_state_dict(state.get("params_ema", state.get("params", state)), strict=True)
    net = net.eval().half().cuda()
    Path(dst).mkdir(parents=True, exist_ok=True)
    frames = sorted(Path(src).glob("*.png"))
    with torch.inference_mode():
        for i, p in enumerate(frames, 1):
            a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float32) / 255
            t = torch.from_numpy(a).permute(2, 0, 1)[None].half().cuda()
            o = upscale(net, t, int(tile)).clamp_(0, 1)[0].permute(1, 2, 0).float().cpu().numpy()
            Image.fromarray((o * 255).round().astype(np.uint8)).save(
                Path(dst) / p.name, compress_level=1
            )
            if i % 50 == 0 or i == len(frames):
                print(f"ESRGAN {i}/{len(frames)}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:])
