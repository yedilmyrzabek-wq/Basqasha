"""Manual end-to-end run of steps 2-5(text) without the DB (owner rule: verify by running).

uv run python -m ai.smoke --transcript PATH --title "..." --minutes 14.7 --views 3000000 \
    --out ../data/_ai_smoke [--angle 0] [--seconds 240] [--writer gemini|claude_code]
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from app.providers.interfaces import CallContext, ScriptRequest
from ai.facts import verified_facts, writer_facts
from ai.factory import build_ai
from ai.local_ledger import LocalCostLedger
from ai.originality import reference_from_transcript


def script_md(doc: dict, report: dict | None = None) -> str:
    lines = [f"# {doc.get('title', '')}", "",
             f"- words: {doc['word_count']} / target {doc['target_words']} (est {doc['est_seconds']} s at {doc['wpm_voice']} wpm)",
             f"- hook_type: {doc['hook_type']} · structure: {doc['structure_id']} · writer: {doc['writer']}",
             f"- checks: {doc.get('checks')}"]
    if report:
        lines.append(f"- originality: {report['verdict']} (max_similarity {report['max_similarity']}, rewrites {report.get('rewrite_rounds', 0)})")
    lines.append("")
    for b in doc["beats"]:
        lines += [f"## {b['beat']}" + (f"  ({', '.join(b['fact_ids'])})" if b.get("fact_ids") else ""), "", b["text"], ""]
    lines += ["---", "```json", json.dumps(doc, ensure_ascii=False, indent=1), "```", ""]
    return "\n".join(lines)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--minutes", type=float, default=0)
    ap.add_argument("--views", type=int, default=None)
    ap.add_argument("--out", required=True)
    ap.add_argument("--angle", type=int, default=-1, help="-1 = highest score")
    ap.add_argument("--seconds", type=int, default=240)
    ap.add_argument("--language", default="kk")
    ap.add_argument("--writer", default=None)
    ap.add_argument("--reuse", action="store_true", help="reuse brief.json / facts.json from --out")
    a = ap.parse_args()

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ledger = LocalCostLedger()
    ai = build_ai(ledger, script_writer=a.writer)
    transcript = Path(a.transcript).read_text(encoding="utf-8")
    t0 = time.time()

    # step 2 — the only step that sees the transcript
    if a.reuse and (out / "brief.json").exists():
        brief_doc = json.loads((out / "brief.json").read_text(encoding="utf-8"))
    else:
        brief_doc = ai.idea(transcript, language=a.language, ctx=CallContext(None, "idea"),
                            source_title=a.title, source_minutes=a.minutes, source_views=a.views)
    (out / "brief.json").write_text(json.dumps(brief_doc, ensure_ascii=False, indent=1), encoding="utf-8")
    angles = brief_doc["angles"]
    pick = a.angle if a.angle >= 0 else max(range(3), key=lambda i: angles[i].get("score", 0))
    angle = angles[pick]
    print(f"[idea] angle #{pick}: {angle['title']}  (${ledger.total():.4f})")

    # step 3
    if a.reuse and (out / "facts.json").exists():
        from ai.facts import FactsResult
        fr = FactsResult(doc=json.loads((out / "facts.json").read_text(encoding="utf-8")), method="reused")
    else:
        fr = ai.facts(brief_doc["brief"], angle, language=a.language, ctx=CallContext(None, "facts"))
    (out / "facts.json").write_text(json.dumps(fr.doc, ensure_ascii=False, indent=1), encoding="utf-8")
    vf = verified_facts(fr.doc)
    print(f"[facts] method={fr.method} facts={len(fr.doc['facts'])} verified={len(vf)}  (${ledger.total():.4f})")

    # step 4 — writer sees brief + angle + verified facts only
    target_words = round(ai.writer.wpm * a.seconds / 60)
    req = ScriptRequest(language=a.language, brief=brief_doc["brief"], angle=angle, facts=writer_facts(fr.doc),
                        target_words=target_words)
    script = ai.writer.write(req, CallContext(None, "script"))
    draft_words = script["word_count"]
    print(f"[script] draft words={draft_words}/{target_words} model={script['writer']}  (${ledger.total():.4f})")

    reference = reference_from_transcript(transcript, a.title)
    script, report = ai.originality(script, reference, CallContext(None, "script"))
    report["policy"] = ai.writer.last_policy.model_dump() if ai.writer.last_policy else None
    (out / "originality.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "script.md").write_text(script_md(dict(script), report), encoding="utf-8")
    print(f"[originality] verdict={report['verdict']} max_sim={report['max_similarity']} "
          f"flagged={len(report['flagged_sentences'])} rounds={report['rewrite_rounds']}  (${ledger.total():.4f})")

    tts = ai.tts(script)
    (out / "tts.txt").write_text(tts.text, encoding="utf-8")
    print(f"[tts] chars={tts.chars} parts={len(tts.parts)} issues={tts.issues} note={tts.note!r}")

    cost = {"total_usd": float(ledger.total()), "seconds": round(time.time() - t0), "entries": ledger.entries}
    (out / "cost.json").write_text(json.dumps(cost, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] total ${ledger.total():.4f} in {cost['seconds']} s -> {out}")


if __name__ == "__main__":
    main()
