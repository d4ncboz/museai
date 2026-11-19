#!/usr/bin/env bash
# Usage: upscale.sh in.mp4 out.mp4
# Makes the delivered video 4K UHD: 2160x3840 (9:16), 3840x2160 (16:9) or 2160x2160 (1:1).
# muse returns at most 1080p (1080x1920, 2026-10-27, 4K asked). A lanczos resize only made the
# file bigger: the user called the Positano 4K "a bit vague". So every frame goes through
# Real-ESRGAN (realesrgan-x4plus, ncnn-vulkan build in $ESRGAN_DIR, default ~/Work/tools/realesrgan):
# frames are first shrunk to a quarter of the target size and enlarged 4x. From the soft 1080p
# render that came out crisper and less painterly than 1080p -> 4x (and 4x faster: ~10 s per
# 9:16 frame on an M1 Pro, ~1 h for 15 s). A temporal-only atadenoise then calms the shimmer
# the per-frame detail adds on still buildings (frame diff 1.44 -> 1.04, source 0.69).
# Tile 1024 (ESRGAN_TILE): 9.8 s per frame vs 11.8 s with the auto tile on an M1 Pro (Goloritze, 2026-10-27).
# Without the binary (or ESRGAN=0) it falls back to lanczos + light unsharp and says so.
# Audio is copied untouched and the frame count does not change, so lip sync and captions stay.
# A file already 4K is copied as it is.
set -euo pipefail
in=$1 out=$2
read -r w h < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "$in" | tr x ' ')
if [ "$w" -gt "$h" ]; then W=3840 H=2160; elif [ "$w" -lt "$h" ]; then W=2160 H=3840; else W=2160 H=2160; fi
if [ "$w" -ge "$W" ] && [ "$h" -ge "$H" ]; then
  cp "$in" "$out"; echo "UHD $out already ${w}x${h}"; exit 0
fi
enc=(-c:v libx264 -preset slow -crf 16 -profile:v high -level 5.1 -pix_fmt yuv420p -movflags +faststart)
esr=${ESRGAN_DIR:-$HOME/Work/tools/realesrgan}
# On an NVIDIA GPU (Colab via muse-renderer) the same model runs in PyTorch (esrgan_cuda.py): Colab has
# no Vulkan driver, so the ncnn build exited 255 there (2026-11-18). Needs $esr/RealESRGAN_x4plus.pth.
cuda=0
if [ "${ESRGAN:-1}" != 0 ] && [ -f "$esr/RealESRGAN_x4plus.pth" ] && command -v nvidia-smi >/dev/null \
  && python3 -c 'import torch; assert torch.cuda.is_available()' 2>/dev/null; then cuda=1; fi
if [ "${ESRGAN:-1}" != 0 ] && { [ "$cuda" = 1 ] || [ -x "$esr/realesrgan-ncnn-vulkan" ]; }; then
  tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
  mkdir "$tmp/q" "$tmp/x4"
  fps=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$in")
  ffmpeg -v error -i "$in" -vf "scale=$((W/4)):$((H/4)):flags=area" "$tmp/q/%05d.png"
  if [ "$cuda" = 1 ]; then
    echo "ESRGAN $(ls "$tmp/q" | wc -l | tr -d ' ') frames on CUDA..."
    python3 "$(dirname "$0")/esrgan_cuda.py" "$tmp/q" "$tmp/x4" "$esr/RealESRGAN_x4plus.pth"
  else
    echo "ESRGAN $(ls "$tmp/q" | wc -l | tr -d ' ') frames (~10 s each)..."
    "$esr/realesrgan-ncnn-vulkan" -i "$tmp/q" -o "$tmp/x4" -n realesrgan-x4plus -s 4 -f png -m "$esr/models" -t "${ESRGAN_TILE:-1024}" >/dev/null 2>&1
  fi
  ffmpeg -v error -y -framerate "$fps" -i "$tmp/x4/%05d.png" -i "$in" -map 0:v -map 1:a? \
    -vf "atadenoise=0a=0.04:0b=0.08:s=9,setsar=1" "${enc[@]}" -c:a copy "$out"
  how="Real-ESRGAN$([ "$cuda" = 1 ] && echo ' CUDA' || true)"
else
  echo "no Real-ESRGAN in $esr: lanczos only (no new detail)" >&2
  ffmpeg -v error -y -i "$in" \
    -vf "scale=${W}:${H}:flags=lanczos+accurate_rnd+full_chroma_int,unsharp=5:5:0.6:5:5:0.0,setsar=1" \
    "${enc[@]}" -c:a copy "$out"
  how="lanczos"
fi
read -r ow oh < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "$out" | tr x ' ')
[ "$ow" = "$W" ] && [ "$oh" = "$H" ] || { echo "upscale gave ${ow}x${oh}, wanted ${W}x${H}" >&2; exit 1; }
echo "UHD $out ${w}x${h} -> ${W}x${H} ($how)"
