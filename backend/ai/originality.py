"""Originality check (IOriginalityChecker) + auto-rewrite loop.

Sentence embeddings (script vs source, cross-lingual, gemini-embedding-2) only shortlist the top-k
candidate pairs; an LLM judge decides per pair whether it is copied wording or just a shared fact.
The verdict is based on judge-flagged sentences only (0 -> pass). Flagged sentences are
rewritten by the script writer (max 2 rounds); the writer gets a generic reason, never source text.

Calls:
  checker = GeminiOriginalityChecker(llm, embed_model=..., judge_model=..., judge_fallback=...)
  script, report = run_originality(writer, checker, script, reference, ctx)   # report -> originality.json
"""
from __future__ import annotations

import logging
import re
from typing import Any, Mapping

import numpy as np

from app.providers.interfaces import CallContext, ILLM, IScriptWriter, OriginalityReference
from ai.gemini import ModelUnavailable
from ai.prompts import load_prompt
from ai.schemas import JudgeOut
from ai.script import script_sentences

log = logging.getLogger("ai.originality")
MAX_REWRITE_ROUNDS = 2


def reference_from_transcript(transcript: str, title: str | None = None) -> OriginalityReference:
    """For app.pipeline.originality_feed: cleaned transcript -> sentence tuple."""
    flat = re.sub(r"\s+", " ", transcript).strip()
    sentences = tuple(s.strip() for s in re.split(r"(?<=[.!?])\s+", flat) if s.strip())
    return OriginalityReference(sentences=sentences, title=title or None)


class GeminiOriginalityChecker:
    def __init__(self, llm: ILLM, *, embed_model: str, judge_model: str, judge_fallback: str,
                 shortlist_k: int = 15):
        self.llm = llm
        self.embed_model = embed_model
        self.judge_model = judge_model
        self.judge_fallback = judge_fallback
        # Cross-lingual cosine (kk script vs en source, same topic) is high for almost every sentence
        # (pilot: 35/39 >= 0.8), so it is NOT a gate: it only picks the top-k pairs for the judge.
        self.shortlist_k = shortlist_k

    def _embed(self, texts: list[str], ctx: CallContext) -> np.ndarray:
        m = np.asarray(self.llm.embed(texts, model=self.embed_model, ctx=ctx), dtype=np.float32)
        return m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-9)

    def check(self, script: Mapping[str, Any], reference: OriginalityReference,
              ctx: CallContext) -> Mapping[str, Any]:
        ours = [s for _, s in script_sentences(script)]
        src = [s for s in reference.sentences if len(s.split()) >= 3]
        if reference.title:
            src.append(reference.title)
        sim = self._embed(ours, ctx) @ self._embed(src, ctx).T
        best_j = sim.argmax(axis=1)
        best = sim[np.arange(len(ours)), best_j]

        order = [int(i) for i in np.argsort(-best)][: self.shortlist_k]
        judged: dict[int, tuple[bool, str]] = {}
        if order:
            pairs = [{"index": i, "ours": ours[i], "source": src[int(best_j[i])],
                      "similarity": round(float(best[i]), 3)} for i in order]
            prompt = load_prompt("originality_judge").render(pairs_json=pairs)
            try:
                out = self.llm.generate_json(prompt=prompt, response_model=JudgeOut, model=self.judge_model, ctx=ctx)
            except ModelUnavailable:
                out = self.llm.generate_json(prompt=prompt, response_model=JudgeOut, model=self.judge_fallback, ctx=ctx)
            judged = {it.index: (it.copied, it.reason) for it in out.value.items if it.index in order}

        # Verdict = LLM judge only: a sentence is flagged iff the judge says it is translated/paraphrased.
        flagged = [{"index": i, "text": ours[i], "similarity": round(float(best[i]), 3),
                    "source_index": int(best_j[i])} for i in order if judged.get(i, (False, ""))[0]]
        return {
            "verdict": "fail" if flagged else "pass",
            "gate": "llm_judge_on_top_k_embedding_pairs",
            "flagged_sentences": flagged,
            "max_similarity": round(float(best.max()) if len(best) else 0.0, 3),  # informational only
            "sentences_checked": len(ours), "source_sentences": len(src), "shortlist_k": len(order),
            "judged": [{"index": i, "similarity": round(float(best[i]), 3), "copied": judged.get(i, (False, ""))[0],
                        "reason": judged.get(i, (False, ""))[1]} for i in order],
            "models": {"embed": self.embed_model, "judge": self.judge_model},
        }


def run_originality(writer: IScriptWriter, checker: GeminiOriginalityChecker, script: Mapping[str, Any],
                    reference: OriginalityReference, ctx: CallContext,
                    max_rounds: int = MAX_REWRITE_ROUNDS) -> tuple[Mapping[str, Any], dict[str, Any]]:
    """Check, auto-rewrite flagged sentences (<= max_rounds), re-check.
    Returns (final script, report) with verdict pass | pass_after_rewrite | fail."""
    report = dict(checker.check(script, reference, ctx))
    history = []
    rounds = 0
    while report["flagged_sentences"] and rounds < max_rounds:
        rounds += 1
        idx = [f["index"] for f in report["flagged_sentences"]]
        history.append({"round": rounds, "flagged": report["flagged_sentences"]})
        reason = (f"{len(idx)} sentence(s) were judged to be a translation or close paraphrase of the "
                  "distinctive wording or imagery of a source video. Say the same thing in your own way.")
        log.info("originality round %d: rewriting %s", rounds, idx)
        script = writer.rewrite_sentences(script, idx, reason, ctx)
        report = dict(checker.check(script, reference, ctx))
    if not report["flagged_sentences"]:
        report["verdict"] = "pass_after_rewrite" if rounds else "pass"
    else:
        report["verdict"] = "fail"
    report["rewrite_rounds"] = rounds
    report["history"] = history
    return script, report
