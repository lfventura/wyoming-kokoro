"""Wyoming event handler: plain and streaming synthesis with Kokoro."""
import argparse
import asyncio
import logging
from typing import Dict, Optional

import numpy as np
from sentence_stream import SentenceBoundaryDetector
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.error import Error
from wyoming.event import Event
from wyoming.info import Describe, Info
from wyoming.server import AsyncEventHandler
from wyoming.tts import (
    Synthesize,
    SynthesizeChunk,
    SynthesizeStart,
    SynthesizeStop,
    SynthesizeStopped,
    SynthesizeVoice,
)

from .text import split_long

_LOGGER = logging.getLogger(__name__)

RATE, WIDTH, CHANNELS = 24000, 2, 1
SAMPLES_PER_CHUNK = 1024


class KokoroEventHandler(AsyncEventHandler):
    def __init__(
        self,
        wyoming_info: Info,
        cli_args: argparse.Namespace,
        pipeline,
        voices: Dict[str, object],
        lock: asyncio.Lock,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.wyoming_info_event = wyoming_info.event()
        self.cli_args = cli_args
        self.pipeline = pipeline
        self.voices = voices
        self.lock = lock
        self.is_streaming = False
        self.stream_voice: Optional[SynthesizeVoice] = None
        self.sbd = SentenceBoundaryDetector()

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.wyoming_info_event)
            return True

        try:
            if Synthesize.is_type(event.type):
                if self.is_streaming:
                    # Sent only for compatibility; the text already arrived as synthesize-chunk events.
                    return True
                synthesize = Synthesize.from_event(event)
                await self._speak(synthesize.text, synthesize.voice)
                return True

            if self.cli_args.no_streaming:
                return True

            if SynthesizeStart.is_type(event.type):
                self.is_streaming = True
                self.stream_voice = SynthesizeStart.from_event(event).voice
                self.sbd = SentenceBoundaryDetector()
                return True

            if SynthesizeChunk.is_type(event.type):
                for sentence in self.sbd.add_chunk(SynthesizeChunk.from_event(event).text):
                    await self._speak(sentence, self.stream_voice)
                return True

            if SynthesizeStop.is_type(event.type):
                rest = self.sbd.finish()
                if rest.strip():
                    await self._speak(rest, self.stream_voice)
                await self.write_event(SynthesizeStopped().event())
                self.is_streaming = False
                return True
        except Exception as err:
            await self.write_event(Error(text=str(err), code=err.__class__.__name__).event())
            raise

        return True

    def _resolve_voice(self, voice: Optional[SynthesizeVoice]):
        name = voice.name if voice and voice.name else self.cli_args.default_voice
        if name in self.voices:
            return name, self.voices[name]
        # Any stock Kokoro voice id (or "a,b" blend) also works, e.g. "pf_dora"
        return name, name

    async def _speak(self, text: str, voice: Optional[SynthesizeVoice]) -> None:
        """Synthesize one utterance, streaming audio as each piece is generated."""
        name, voice_pack = self._resolve_voice(voice)
        sbd = SentenceBoundaryDetector()
        sentences = [*sbd.add_chunk(" ".join(text.splitlines())), sbd.finish()]
        pieces = [p for sentence in sentences for p in split_long(sentence)]
        _LOGGER.debug("speak voice=%s pieces=%s", name, pieces)

        await self.write_event(AudioStart(rate=RATE, width=WIDTH, channels=CHANNELS).event())
        for piece in pieces:
            async with self.lock:
                audio = await asyncio.to_thread(self._generate, piece, voice_pack)
            for i in range(0, len(audio), SAMPLES_PER_CHUNK * WIDTH):
                await self.write_event(
                    AudioChunk(
                        rate=RATE, width=WIDTH, channels=CHANNELS,
                        audio=audio[i : i + SAMPLES_PER_CHUNK * WIDTH],
                    ).event()
                )
        await self.write_event(AudioStop().event())

    def _generate(self, text: str, voice_pack) -> bytes:
        segments = [
            result.audio.cpu().numpy() if hasattr(result.audio, "cpu") else np.asarray(result.audio)
            for result in self.pipeline(text, voice=voice_pack, speed=self.cli_args.speed)
            if result.audio is not None
        ]
        if not segments:
            return b""
        audio = np.clip(np.concatenate(segments), -1.0, 1.0)
        return (audio * 32767).astype("<i2").tobytes()
