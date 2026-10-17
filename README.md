# wyoming-kokoro

[Wyoming protocol](https://github.com/OHF-Voice/wyoming) text-to-speech server for Home Assistant, using
[Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M). Built for Brazilian Portuguese, but any Kokoro
language works through `--lang-code`.

- **Blended voices.** `--voice NAME=VOICE[:WEIGHT],...` defines a named voice as a weighted average of
  Kokoro voice packs, e.g. `santa_adam=pm_santa:0.7,am_adam:0.3`. Repeat the flag for more voices; the
  first one is the default. Stock voice ids (`pf_dora`, `pm_alex`, ...) can also be requested directly.
- **Text streaming.** Supports `synthesize-start` / `synthesize-chunk` / `synthesize-stop`, so Home
  Assistant can stream an LLM answer and audio starts after the first sentence.
- **Sentence by sentence.** Plain `synthesize` requests are also split per sentence and audio is sent as
  soon as each sentence is ready. Long sentences are split at clause punctuation, because Kokoro truncates
  long inputs for espeak-based languages such as Portuguese.
- **CPU friendly.** The 82M model runs faster than real time on a desktop CPU.
- **Offline, any UID.** The model and voice packs are baked into the image (`HF_HUB_OFFLINE=1`); no volume
  or download at runtime, and it runs as any non-root user.

## Run

```shell
docker run --rm -p 10200:10200 --user 3016:3017 ghcr.io/lfventura/wyoming-kokoro:latest \
  --voice santa_adam=pm_santa:0.7,am_adam:0.3 \
  --voice dora_heart=pf_dora:0.5,af_heart:0.5
```

Then add a **Wyoming Protocol** integration in Home Assistant pointing at the host and port `10200`.

`truenas-custom-app.yaml` is a ready-to-paste file for TrueNAS SCALE (Apps -> Discover -> Custom App ->
Install via YAML).

## Options

| Flag | Default | Description |
|---|---|---|
| `--voice NAME=VOICE[:WEIGHT],...` | `pm_santa=pm_santa` | named voice (repeatable) |
| `--default-voice NAME` | first `--voice` | voice used when the client does not choose one |
| `--lang-code` | `p` | Kokoro language code (`p` = Brazilian Portuguese) |
| `--language` | `pt_BR` | language advertised to clients |
| `--speed` | `1.0` | speech speed |
| `--threads` | torch default | CPU threads |
| `--device` | `cpu` | torch device |
| `--no-streaming` | off | disable text streaming |
| `--uri` | `tcp://0.0.0.0:10200` | listen address |
| `--debug` | off | debug logging |

Kokoro voices: https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md

## Images

`.github/workflows/ghcr.yml` publishes `ghcr.io/lfventura/wyoming-kokoro:latest`, `:<version>` (from
`wyoming_kokoro/VERSION`) and `:sha-<commit>` on every push to `main` that touches the image.

## License

Apache-2.0. Kokoro-82M weights are Apache-2.0 by hexgrad.
