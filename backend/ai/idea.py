"""Step 2: brief + 3 presentation variants from the source transcript (only step allowed to see it).

Call: generate_idea(llm, transcript, language=..., ctx=..., source_title=..., source_minutes=...,
source_views=...) -> brief.schema.json document.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from app.providers.interfaces import CallContext, ILLM
from ai.prompts import LANGUAGE_NAMES, load_prompt
from ai.schemas import IdeaOut, validate_doc
from ai.textnorm_kk import fix_homoglyphs

log = logging.getLogger("ai.idea")
NGRAM = 5
MAX_TRIES = 3
_TOK = re.compile(r"[^\W\d_]+", re.U)


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOK.findall(text)]


def _ngrams(tokens: list[str], n: int = NGRAM) -> set[tuple[str, ...]]:
    return {tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def copied_phrases(text: str, source_ngrams: set[tuple[str, ...]]) -> list[str]:
    """Phrases of >= NGRAM consecutive words that also occur in the source."""
    return sorted({" ".join(g) for g in _ngrams(_tokens(text)) if g in source_ngrams})


def _all_text(out: IdeaOut) -> str:
    b = out.brief
    parts = [b.topic, b.core_question, *b.structure_idea, *(f"{k.term} {k.gloss}" for k in b.key_concepts)]
    for a in out.angles:
        parts += [a.title, a.pitch, *a.hook_words]
    return "\n".join(parts)


def demand_score(views: int | None) -> int:
    """D (0-5) from source views (topics_backlog R3)."""
    if views is None:
        return 3
    for limit, d in ((300_000, 1), (1_000_000, 2), (3_000_000, 3), (10_000_000, 4)):
        if views < limit:
            return d
    return 5


def _clip(s: str, n: int) -> str:
    s = fix_homoglyphs(s.strip())
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _to_doc(out: IdeaOut, language: str, d: int) -> dict[str, Any]:
    b = out.brief
    brief = {
        "topic": _clip(b.topic, 200), "core_question": _clip(b.core_question, 200),
        "structure_idea": [_clip(s, 120) for s in b.structure_idea][:8],
        "key_concepts": [{"term": fix_homoglyphs(k.term), "gloss": _clip(k.gloss, 120)} for k in b.key_concepts],
        "category": b.category, "risk": max(0, min(3, b.risk)),
        "sensitive_topics": b.sensitive_topics, "operator_summary": b.operator_summary.strip(),
    }
    angles = []
    for a in out.angles[:3]:
        score = 2 * d + 3 * a.k + 1.5 * a.v + 1.5 * a.f - 3 * a.r
        angles.append({
            "title": _clip(a.title, 60), "pitch": _clip(a.pitch, 600),
            "why_it_works": _clip(a.why_it_works, 400),
            "hook_words": [fix_homoglyphs(w) for w in a.hook_words][:5],
            "suggested_hook_type": a.suggested_hook_type,
            "score": max(0.0, min(40.0, float(score))),
        })
    return {"language": language, "brief": brief, "angles": angles}


def generate_idea(llm: ILLM, transcript: str, *, language: str, ctx: CallContext, model: str,
                  source_title: str = "", source_minutes: float = 0, source_views: int | None = None,
                  operator_hint: str | None = None, target_seconds: int = 240, wpm: float = 110) -> dict[str, Any]:
    prompt = load_prompt("idea")
    src_ngrams = _ngrams(_tokens(transcript + "\n" + source_title))
    banned: list[str] = []
    last_copied: list[str] = []
    for attempt in range(MAX_TRIES):
        text = prompt.render(
            language_name=LANGUAGE_NAMES[language], source_title=source_title or "-",
            source_minutes=f"{source_minutes:.0f}", transcript=transcript,
            target_minutes=f"{target_seconds / 60:g}", target_words=str(round(wpm * target_seconds / 60)),
            operator_hint=f"\nOperator hint: {operator_hint}" if operator_hint else "",
            banned_phrases=("- These phrases were copied in a previous attempt and are forbidden: "
                            + "; ".join(f'"{p}"' for p in banned)) if banned else "")
        out = llm.generate_json(prompt=text, response_model=IdeaOut, model=model, ctx=ctx).value
        if len(out.angles) < 3:
            log.warning("idea: %d angles, retrying", len(out.angles))
            continue
        last_copied = copied_phrases(_all_text(out), src_ngrams)
        if not last_copied:
            doc = _to_doc(out, language, demand_score(source_views))
            validate_doc("brief", doc)
            return doc
        log.warning("idea attempt %d copied %d phrases from source, retrying", attempt + 1, len(last_copied))
        banned += last_copied
    raise RuntimeError(f"idea: could not produce a quote-free brief after {MAX_TRIES} tries "
                       f"(copied: {last_copied[:5]})")
