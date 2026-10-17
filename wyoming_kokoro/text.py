"""Split text into pieces short enough for Kokoro's non-English G2P."""
import re
from typing import Iterator

# Kokoro truncates long inputs for espeak-based languages; keep each call well under the 510-token limit.
MAX_CHARS = 250

_CLAUSE_SPLIT = re.compile(r"(?<=[,;:])\s+")


def clean(text: str) -> str:
    return " ".join(text.split())


def _wrap_words(text: str, max_chars: int) -> Iterator[str]:
    line = ""
    for word in text.split(" "):
        candidate = f"{line} {word}".strip()
        if len(candidate) > max_chars and line:
            yield line
            line = word
        else:
            line = candidate
    if line:
        yield line


def split_long(sentence: str, max_chars: int = MAX_CHARS) -> Iterator[str]:
    """Yield the sentence whole, or packed clauses (words as a last resort) of at most max_chars."""
    sentence = clean(sentence)
    if len(sentence) <= max_chars:
        if sentence:
            yield sentence
        return

    piece = ""
    for clause in _CLAUSE_SPLIT.split(sentence):
        for chunk in _wrap_words(clause, max_chars):
            candidate = f"{piece} {chunk}".strip()
            if len(candidate) > max_chars and piece:
                yield piece
                piece = chunk
            else:
                piece = candidate
    if piece:
        yield piece
