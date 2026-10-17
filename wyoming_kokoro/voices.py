"""Named voices built from weighted blends of Kokoro voice packs."""
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class VoiceSpec:
    name: str
    parts: Tuple[Tuple[str, float], ...]

    def describe(self) -> str:
        total = sum(w for _, w in self.parts)
        return " + ".join(f"{voice} {round(100 * w / total)}%" for voice, w in self.parts)


def parse_voice_spec(spec: str) -> VoiceSpec:
    """Parse "name=pm_santa:0.7,am_adam:0.3" (weights optional, default 1)."""
    if "=" not in spec:
        raise ValueError(f"Voice spec must look like name=voice[:weight],...: {spec!r}")

    name, blend = (s.strip() for s in spec.split("=", 1))
    parts: List[Tuple[str, float]] = []
    for item in blend.split(","):
        voice, _, weight = item.strip().partition(":")
        parts.append((voice.strip(), float(weight) if weight else 1.0))

    if not name or not parts or any(not v or w <= 0 for v, w in parts):
        raise ValueError(f"Invalid voice spec: {spec!r}")

    return VoiceSpec(name=name, parts=tuple(parts))


def blend(pipeline, spec: VoiceSpec):
    """Weighted average of the voice packs in the spec."""
    total = sum(w for _, w in spec.parts)
    mixed = None
    for voice, weight in spec.parts:
        pack = pipeline.load_voice(voice) * (weight / total)
        mixed = pack if mixed is None else mixed + pack
    return mixed


def build_voices(pipeline, specs: List[VoiceSpec]) -> Dict[str, object]:
    return {spec.name: blend(pipeline, spec) for spec in specs}
