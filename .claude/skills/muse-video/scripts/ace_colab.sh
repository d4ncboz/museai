#!/usr/bin/env bash
# Usage (inside a muse-renderer job on Colab, via remote.py ace): ace_colab.sh SCRIPT ARGS...
# Installs ACE-Step once per runtime (no venv: Colab's own torch has CUDA), then runs museai's SCRIPT
# (path relative to $MUSEAI) with ARGS. The checkpoints (~7.7 GB) download on the first render of a runtime.
set -euo pipefail
script=$1; shift
if [ ! -f /content/.ace-ready ]; then
  [ -d /content/ace-step ] || git clone -q --depth 1 https://github.com/ace-step/ACE-Step /content/ace-step
  # --no-deps for the package itself: its torch pins would replace Colab's CUDA torch. Its other pins
  # matter: py3langid 0.4 has no LanguageIdentifier.from_pickled_model (2026-11-19)
  pip install -q --no-deps -e /content/ace-step
  pip install -q diffusers loguru "pypinyin==0.53.0" "py3langid==0.3.0" hangul-romanize num2words cutlet \
    "fugashi[unidic-lite]" "transformers==4.50.0" "accelerate==1.6.0" "pytorch_lightning==2.5.1" soundfile librosa spacy peft
  touch /content/.ace-ready
fi
python3 -W ignore "$MUSEAI/$script" "$@"
