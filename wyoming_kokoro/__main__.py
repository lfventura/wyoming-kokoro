#!/usr/bin/env python3
import argparse
import asyncio
import logging
from functools import partial

import torch
from kokoro import KPipeline
from wyoming.info import Attribution, Info, TtsProgram, TtsVoice
from wyoming.server import AsyncServer

from . import __version__
from .handler import KokoroEventHandler
from .voices import build_voices, parse_voice_spec

_LOGGER = logging.getLogger(__name__)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", default="tcp://0.0.0.0:10200", help="unix:// or tcp://")
    parser.add_argument(
        "--voice",
        action="append",
        default=[],
        metavar="NAME=VOICE[:WEIGHT],...",
        help="Named voice from a weighted blend of Kokoro voices, e.g. santa_adam=pm_santa:0.7,am_adam:0.3 (repeatable)",
    )
    parser.add_argument("--default-voice", help="Voice used when the client does not pick one (default: first --voice)")
    parser.add_argument("--lang-code", default="p", help="Kokoro language code (p = Brazilian Portuguese)")
    parser.add_argument("--language", default="pt_BR", help="Language advertised to clients")
    parser.add_argument("--speed", type=float, default=1.0, help="Speech speed (1.0 = normal)")
    parser.add_argument("--threads", type=int, default=0, help="CPU threads for torch (0 = torch default)")
    parser.add_argument("--device", default="cpu", help="torch device: cpu, cuda, xpu")
    parser.add_argument("--no-streaming", action="store_true", help="Disable text streaming (synthesize-chunk)")
    parser.add_argument("--debug", action="store_true", help="Log DEBUG messages")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    if args.threads > 0:
        torch.set_num_threads(args.threads)

    specs = [parse_voice_spec(s) for s in args.voice] or [parse_voice_spec("pm_santa=pm_santa")]
    args.default_voice = args.default_voice or specs[0].name
    if args.default_voice not in {s.name for s in specs}:
        parser.error(f"--default-voice {args.default_voice!r} is not one of the --voice names")

    _LOGGER.info("Loading Kokoro (lang_code=%s, device=%s)", args.lang_code, args.device)
    pipeline = KPipeline(lang_code=args.lang_code, device=args.device, repo_id="hexgrad/Kokoro-82M")
    voices = build_voices(pipeline, specs)
    for spec in specs:
        _LOGGER.info("Voice %s = %s%s", spec.name, spec.describe(), " (default)" if spec.name == args.default_voice else "")

    # First inference pays for lazy initialization; do it before accepting clients.
    list(pipeline("ok", voice=voices[args.default_voice]))

    wyoming_info = Info(
        tts=[
            TtsProgram(
                name="kokoro",
                description="Kokoro-82M text to speech",
                attribution=Attribution(name="hexgrad", url="https://huggingface.co/hexgrad/Kokoro-82M"),
                installed=True,
                version=__version__,
                voices=[
                    TtsVoice(
                        name=spec.name,
                        description=spec.describe(),
                        attribution=Attribution(name="hexgrad", url="https://huggingface.co/hexgrad/Kokoro-82M"),
                        installed=True,
                        version=None,
                        languages=[args.language],
                    )
                    for spec in specs
                ],
                supports_synthesize_streaming=not args.no_streaming,
            )
        ],
    )

    server = AsyncServer.from_uri(args.uri)
    _LOGGER.info("Ready")
    await server.run(partial(KokoroEventHandler, wyoming_info, args, pipeline, voices, asyncio.Lock()))


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        pass
