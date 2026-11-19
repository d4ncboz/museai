"""Instrumental ACE-Step render, optionally guided by a reference recording (audio2audio). Runs in the
ACE-Step venv; `scripts/music` calls it under the shared render.lock.
  ~/.local/share/ace-step/venv/bin/python scripts/ace_piano.py --tags "..." --duration 30 --seed 7 \
      [--ref ref.wav --ref-strength 0.3] --out piano.wav
With --ref the output takes the reference's length, so loop or trim it to the length first. Keep the
strength low (0.25-0.35): it borrows the feel (instrument, register, pace), not the tune; a higher one
rebuilds the reference's own melody, which is someone else's music.
"""

import argparse
import os
from pathlib import Path

import soundfile
import torch
import torchaudio
from acestep.pipeline_ace_step import ACEStepPipeline


def _save(path, wav, sample_rate, format=None, backend=None, **_):
    # torchaudio >= 2.9 saves only through torchcodec, which the venv lacks (as in muse-video ace_song.py)
    soundfile.write(str(path), wav.detach().cpu().float().numpy().T, sample_rate)


def _load(path, *_, **__):
    # same for load (the --ref audio): soundfile, as (channels, frames) float tensor
    data, sr = soundfile.read(str(path), dtype="float32", always_2d=True)
    return torch.from_numpy(data.T.copy()), sr


torchaudio.save = _save
torchaudio.load = _load


def _straight_to_gpu():
    # Colab (muse-renderer) has 12.7 GB RAM: loading the checkpoints on the CPU first was OOM-killed at
    # 11.6 GB RSS (2026-11-19). Every model loads its weights onto the GPU directly instead.
    from diffusers import ModelMixin
    from transformers import PreTrainedModel

    for cls in (ModelMixin, PreTrainedModel):
        orig = cls.from_pretrained.__func__

        def from_pretrained(c, *args, _orig=orig, **kw):
            kw.setdefault("low_cpu_mem_usage", True)
            kw.setdefault("device_map", "cuda")
            return _orig(c, *args, **kw)

        cls.from_pretrained = classmethod(from_pretrained)


if torch.cuda.is_available():
    _straight_to_gpu()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tags", required=True)
    ap.add_argument("--duration", type=float, default=30)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--steps", type=int, default=100)
    ap.add_argument("--guidance", type=float, default=10.0)
    ap.add_argument("--ref")
    ap.add_argument("--ref-strength", type=float, default=0.3)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    mps = torch.backends.mps.is_available()
    # a T4 (Colab, through muse-renderer) has no bfloat16 in hardware: float16 there
    half = (
        "bfloat16"
        if not torch.cuda.is_available() or torch.cuda.is_bf16_supported(including_emulation=False)
        else "float16"
    )
    if half == "float16":
        # ACEStepPipeline reads any dtype but "bfloat16" as float32 (14.5 GB: CUDA OOM on the T4); its env override
        os.environ.setdefault("ACE_PIPELINE_DTYPE", "float16")
    pipe = ACEStepPipeline(
        checkpoint_dir=str(Path.home() / ".cache/ace-step/checkpoints"),
        dtype="float32" if mps else half,
        torch_compile=False,
        cpu_offload=False,
    )
    ref = (
        dict(
            audio2audio_enable=True,
            ref_audio_input=str(Path(a.ref).resolve()),
            ref_audio_strength=a.ref_strength,
        )
        if a.ref
        else {}
    )
    pipe(
        audio_duration=a.duration,
        prompt=a.tags,
        lyrics="[instrumental]",
        infer_step=a.steps,
        guidance_scale=a.guidance,
        scheduler_type="euler",
        cfg_type="apg",
        omega_scale=10.0,
        manual_seeds=str(a.seed),
        guidance_interval=0.5,
        guidance_interval_decay=0.0,
        min_guidance_scale=3.0,
        use_erg_tag=True,
        use_erg_lyric=True,
        use_erg_diffusion=True,
        oss_steps="",
        guidance_scale_text=0.0,
        guidance_scale_lyric=0.0,
        save_path=str(Path(a.out).resolve()),
        format="wav",
        **ref,
    )


if __name__ == "__main__":
    main()
