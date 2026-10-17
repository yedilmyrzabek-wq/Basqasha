"""Step 4: the script writer (IScriptWriter) + helpers shared with originality and TTS export.

ScriptWriter(llm, model, check_model, check_fallback, wpm): write(req, ctx) -> script.schema.json doc;
rewrite_sentences(script, idx, reason, ctx) -> doc. The llm is GeminiLLM or ClaudeCodeLLM (settings mode).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Mapping, Sequence, TypeVar

from pydantic import BaseModel

from app.providers.interfaces import CallContext, ILLM, ScriptRequest
from ai.gemini import ModelUnavailable
from ai.prompts import LANGUAGE_NAMES, language_rules, load_prompt
from ai.schemas import PolicyOut, RewriteOut, ScriptOut, validate_doc
from ai.textnorm_kk import fix_homoglyphs, normalize_kk

log = logging.getLogger("ai.script")
M = TypeVar("M", bound=BaseModel)

BEATS8 = [("hook", 0.06), ("context", 0.08), ("beat_a", 0.19), ("beat_b", 0.19),
          ("beat_c", 0.195), ("twist", 0.125), ("payoff", 0.10), ("outro", 0.06)]
TOLERANCE = 0.08
MAX_ADJUST_ROUNDS = 2
_SENT = re.compile(r"(?<=[.!?…])\s+")


# ------------------------------------------------------------------ text helpers
def count_words(text: str) -> int:
    """script.schema.json rule: whitespace tokens after stripping punctuation."""
    return sum(1 for t in text.split() if re.search(r"\w", t))


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT.split(text.strip()) if s.strip()]


def script_sentences(script: Mapping[str, Any]) -> list[tuple[int, str]]:
    """(beat_index, sentence) in reading order; the global index is the list position."""
    return [(bi, s) for bi, b in enumerate(script["beats"]) for s in split_sentences(b["text"])]


def word_range(target: int) -> tuple[int, int]:
    return round(target * (1 - TOLERANCE)), round(target * (1 + TOLERANCE))


def beat_targets(target_words: int) -> dict[str, int]:
    return {b: round(target_words * p) for b, p in BEATS8}


def _norm_text(text: str, language: str) -> str:
    return normalize_kk(text) if language == "kk" else fix_homoglyphs(text).strip()


def build_doc(out: ScriptOut, *, language: str, target_words: int, wpm: float,
              writer_kind: str, model: str, fact_ids: set[str]) -> dict[str, Any]:
    beats = []
    for b in out.beats:
        item: dict[str, Any] = {"beat": b.beat.strip().lower(), "text": _norm_text(b.text, language)}
        ids = [i for i in b.fact_ids if i in fact_ids]
        if ids:
            item["fact_ids"] = ids
        beats.append(item)
    text = "\n\n".join(b["text"] for b in beats)
    wc = count_words(text)
    sentences = split_sentences(text)
    doc = {
        "language": language, "title": _norm_text(out.title, language)[:60], "text": text,
        "word_count": wc, "target_words": target_words, "wpm_voice": wpm,
        "est_seconds": round(wc / wpm * 60, 1), "hook_type": out.hook_type, "structure_id": "beats8",
        "beats": beats, "writer": {"kind": writer_kind, "model": model},
        "checks": {"max_sentence_words": max((count_words(s) for s in sentences), default=0),
                   "hook_words": count_words(beats[0]["text"]) if beats else 0},
    }
    validate_doc("script", doc)
    return doc


def _rebuild(script: Mapping[str, Any], beat_texts: list[str]) -> dict[str, Any]:
    doc = json.loads(json.dumps(script))
    for b, t in zip(doc["beats"], beat_texts):
        b["text"] = t
    doc["text"] = "\n\n".join(beat_texts)
    doc["word_count"] = count_words(doc["text"])
    doc["est_seconds"] = round(doc["word_count"] / doc.get("wpm_voice", 110) * 60, 1)
    sents = split_sentences(doc["text"])
    doc.setdefault("checks", {})["max_sentence_words"] = max((count_words(s) for s in sents), default=0)
    doc["checks"]["hook_words"] = count_words(beat_texts[0])
    validate_doc("script", doc)
    return doc


def policy_check(llm: ILLM, text: str, *, sensitive_topics: Sequence[str], ctx: CallContext,
                 model: str, fallback_model: str) -> PolicyOut:
    prompt = load_prompt("policy_check").render(text=text, sensitive_topics=", ".join(sensitive_topics) or "none")
    try:
        return llm.generate_json(prompt=prompt, response_model=PolicyOut, model=model, ctx=ctx).value
    except ModelUnavailable:
        return llm.generate_json(prompt=prompt, response_model=PolicyOut, model=fallback_model, ctx=ctx).value


# ------------------------------------------------------------------ writers
class ScriptWriter:
    def __init__(self, llm: ILLM, *, model: str, check_model: str, check_fallback: str, wpm: float = 110):
        self.llm = llm
        self.model = model
        self.check_model = check_model
        self.check_fallback = check_fallback
        self.wpm = wpm
        self.last_policy: PolicyOut | None = None
        self.last_model = ""

    def _complete(self, prompt: str, response_model: type[M], ctx: CallContext) -> M:
        res = self.llm.generate_json(prompt=prompt, response_model=response_model, model=self.model, ctx=ctx)
        self.last_model = res.model
        return res.value

    @property
    def kind(self) -> str:
        """script.data.writer.kind: ClaudeCodeLLM reports models as "claude-code-cli:<model>"."""
        return "claude_code" if self.last_model.startswith("claude-code-cli") else "gemini"

    def write(self, req: ScriptRequest, ctx: CallContext) -> Mapping[str, Any]:
        lang = req.language
        lo, hi = word_range(req.target_words)
        targets = beat_targets(req.target_words)
        # req.facts: verified facts; "conflicting" ones (if the caller passes them) become caveats only.
        facts = [{"id": f["id"], "claim": f["claim"], "value": f.get("value")}
                 for f in req.facts if f.get("status", "verified") == "verified"]
        caveats = [{"id": f["id"], "claim": f["claim"], "note": f.get("note", "")}
                   for f in req.facts if f.get("status") == "conflicting"]
        fact_ids = {f["id"] for f in facts}
        rules = language_rules(lang)
        prompt = load_prompt("script").render(
            language_name=LANGUAGE_NAMES[lang], target_seconds=str(round(req.target_words / self.wpm * 60)),
            wpm=str(self.wpm), target_words=str(req.target_words), min_words=str(lo), max_words=str(hi),
            hook_max_words=str(round(28 * self.wpm / 110)),
            beat_table="\n".join(f"  - {b}: ~{n}" for b, n in targets.items()),
            avoid_hook_types=", ".join(req.avoid_hook_types) or "(none)",
            brief_json=dict(req.brief), angle_json=dict(req.angle), facts_json=facts,
            caveats_json=caveats or "(none)", operator_notes=req.operator_notes or "(none)", language_rules=rules)
        out = self._complete(prompt, ScriptOut, ctx)
        doc = build_doc(out, language=lang, target_words=req.target_words, wpm=self.wpm,
                        writer_kind=self.kind, model=self.last_model, fact_ids=fact_ids)

        for rnd in range(MAX_ADJUST_ROUNDS):
            if lo <= doc["word_count"] <= hi:
                break
            report = "\n".join(
                f"  - {b['beat']}: {count_words(b['text'])} words (target ~{targets.get(b['beat'], '?')})"
                for b in doc["beats"])
            log.info("script length %d not in %d-%d, adjust round %d", doc["word_count"], lo, hi, rnd + 1)
            adj = load_prompt("script_adjust").render(
                language_name=LANGUAGE_NAMES[lang], target_words=str(req.target_words), min_words=str(lo),
                max_words=str(hi), current_words=str(doc["word_count"]), beat_report=report,
                script_json={"title": doc["title"], "hook_type": doc["hook_type"],
                             "beats": [{"beat": b["beat"], "text": b["text"], "fact_ids": b.get("fact_ids", [])}
                                       for b in doc["beats"]]},
                facts_json=facts, language_rules=rules)
            out = self._complete(adj, ScriptOut, ctx)
            doc = build_doc(out, language=lang, target_words=req.target_words, wpm=self.wpm,
                            writer_kind=self.kind, model=self.last_model, fact_ids=fact_ids)

        self.last_policy = policy_check(self.llm, doc["text"], sensitive_topics=req.brief.get("sensitive_topics", []),
                                        ctx=ctx, model=self.check_model, fallback_model=self.check_fallback)
        doc["checks"]["no_advice"] = self.last_policy.no_advice
        validate_doc("script", doc)
        return doc

    def rewrite_sentences(self, script: Mapping[str, Any], sentence_indexes: Sequence[int],
                          reason: str, ctx: CallContext) -> Mapping[str, Any]:
        sents = script_sentences(script)
        wanted = {i: sents[i][1] for i in sentence_indexes if 0 <= i < len(sents)}
        if not wanted:
            return script
        prompt = load_prompt("script_rewrite").render(
            language_name=LANGUAGE_NAMES[script["language"]], reason=reason,
            sentences_json={str(i): s for i, s in wanted.items()}, context_text=script["text"],
            language_rules=language_rules(script["language"]))
        out = self._complete(prompt, RewriteOut, ctx)
        new = {it.index: _norm_text(it.text, script["language"]) for it in out.items if it.index in wanted}
        per_beat: list[list[str]] = [[] for _ in script["beats"]]
        for i, (bi, s) in enumerate(sents):
            per_beat[bi].append(new.get(i, s))
        return _rebuild(script, [" ".join(p) for p in per_beat])
