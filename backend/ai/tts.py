"""Step 5 text for the operator's "Copy for ElevenLabs" button.

Call: export_tts(script_doc) -> TtsExport. ``text`` is exactly what must be voiced (the aligner
tokenizes it); ``note`` is shown next to the button, never put into the text.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ai.script import split_sentences
from ai.textnorm_kk import normalize_kk, tts_issues

MAX_CHARS = 5000  # eleven_v3 per-request limit (tools_costs R10)
NOTES = {"kk": "Model: Eleven v4 (or Eleven v3). Multilingual v2 / Flash / Turbo do not support Kazakh."}


@dataclass(frozen=True)
class TtsExport:
    text: str
    chars: int
    parts: list[str]                 # > 1 only if text exceeds MAX_CHARS (split at sentence ends)
    note: str
    issues: list[str] = field(default_factory=list)   # must be empty before the operator voices it


def _split(text: str, limit: int) -> list[str]:
    parts, cur = [], ""
    for para in text.split("\n\n"):
        for s in split_sentences(para):
            if cur and len(cur) + 1 + len(s) > limit:
                parts.append(cur.strip())
                cur = ""
            cur += s + " "
        cur = cur.rstrip() + "\n\n"
    if cur.strip():
        parts.append(cur.strip())
    return parts


def export_tts(script: Mapping[str, Any]) -> TtsExport:
    lang = script["language"]
    paragraphs = [b["text"] for b in script["beats"]]  # blank line between beats = natural pause
    text = "\n\n".join(normalize_kk(p) if lang == "kk" else p.strip() for p in paragraphs)
    issues = tts_issues(text) if lang == "kk" else []
    parts = [text] if len(text) <= MAX_CHARS else _split(text, MAX_CHARS)
    return TtsExport(text=text, chars=len(text), parts=parts, issues=issues,
                     note=NOTES.get(lang, "Model: Eleven v4."))
