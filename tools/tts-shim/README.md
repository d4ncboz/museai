# tts-shim

OpenAI-compatible text-to-speech (`POST /v1/audio/speech`) on top of the museai video route, for clients that
want speech (word pronunciations, listening passages) from a free muse.ai account.

muse.ai has no speech endpoint, so each request renders a short still video in which a narrator reads the
text exactly; ffmpeg keeps the audio (mono WAV, 24 kHz) and trims silence. Results are cached by
(voice, text), so retries and re-runs are free. A render takes about 1-3 minutes.

## Run

Needs a running museai gateway with at least one account, and `ffmpeg` on PATH.

```bash
python3 tools/tts-shim/tts_shim.py            # listens on 127.0.0.1:18620
python3 tools/tts-shim/tts_shim.py --concurrency 6 --port 18621
```

| Flag / env | Default | Meaning |
| --- | --- | --- |
| `--gateway` / `MUSE_TTS_GATEWAY` | `http://127.0.0.1:18610` | museai gateway |
| `MUSE_TTS_API_KEY` or `--key-file` | `data/api_key` of this checkout | gateway bearer key |
| `--port` / `MUSE_TTS_PORT` | `18620` | listen port (`--host` defaults to `127.0.0.1`) |
| `--concurrency` / `MUSE_TTS_CONCURRENCY` | `3` | parallel renders; set to the number of accounts |
| `--cache-dir` / `MUSE_TTS_CACHE` | `~/.cache/museai-tts` | WAV cache |

Check: `curl -s http://127.0.0.1:18620/v1/models`, then

```bash
curl -s http://127.0.0.1:18620/v1/audio/speech -H 'Content-Type: application/json' \
  -d '{"input":"Hello there.","voice":"nova"}' -o hello.wav
```

Voices: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer` (British narrators; unknown names fall back to
`alloy`). Point an OpenAI-compatible client at `http://127.0.0.1:18620/v1` with any API key.

## As a login service

macOS: a launchd agent running `python3 <checkout>/tools/tts-shim/tts_shim.py` with `RunAtLoad` and
`KeepAlive`. Linux: a systemd user unit with `Restart=always` and `loginctl enable-linger $USER`.
