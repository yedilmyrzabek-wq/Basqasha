"""Word counting per script.schema.json: strip punctuation, split on whitespace; a hyphenated
word counts once."""
from __future__ import annotations

import difflib
import re

_PUNCT = re.compile(r"[^\w\s-]", re.UNICODE)


def words(text: str) -> list[str]:
    return [w for w in (t.strip("-") for t in _PUNCT.sub(" ", text or "").split()) if w]


def count_words(text: str) -> int:
    return len(words(text))


def edit_ratio(draft: str, final: str) -> float:
    """Share of draft words changed in the final text (0 = untouched)."""
    a, b = words(draft.lower()), words(final.lower())
    if not a:
        return 0.0
    same = sum(m.size for m in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    return round(1 - same / max(len(a), len(b)), 4)


def within_budget(word_count: int, target: int) -> bool:
    return abs(word_count - target) <= round(target * 0.08)


def sync_beats(data: dict, text: str) -> dict:
    """Operator edits the whole text; beats (used by originality + TTS export) follow it.
    Paragraphs (blank-line separated) map 1:1 onto beats; extra paragraphs join the last beat,
    missing ones drop the trailing beats."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    beats = [dict(b) for b in data.get("beats", [])]
    if not beats:
        beats = [{"beat": f"p{i + 1}", "text": p} for i, p in enumerate(paras)]
    elif len(paras) >= len(beats):
        for b, p in zip(beats, paras):
            b["text"] = p
        beats[-1]["text"] = "\n\n".join(paras[len(beats) - 1:])
    else:
        beats = beats[:len(paras)]
        for b, p in zip(beats, paras):
            b["text"] = p
    wc = count_words(text)
    return {**data, "text": text, "beats": beats, "word_count": wc}
