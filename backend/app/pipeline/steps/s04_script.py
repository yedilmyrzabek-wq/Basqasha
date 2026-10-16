"""Step 4: script in the project language + originality check (auto-rewrite max 2 rounds);
waits for the operator's approval."""
from __future__ import annotations

import uuid
from typing import Any, Mapping

from sqlalchemy import func, select, update

from app.db import session_scope
from app.models import OriginalityReport, Project, Script
from app.pipeline import ai_bridge, originality_feed
from app.pipeline.context import load_context
from app.pipeline.orchestrator import StepResult, job_log, register
from app.providers.interfaces import CallContext, ScriptRequest
from app.schemas import errors as schema_errors
from app.storage import project_dir, write_json, write_text
from app.text import count_words


def _history(db, project_id: uuid.UUID) -> tuple[list[str], list[str]]:
    """Hook types of the last 3 other projects and the previous project's structure."""
    rows = db.execute(select(Project.hook_type, Project.structure_id)
                      .where(Project.id != project_id, Project.hook_type.is_not(None))
                      .order_by(Project.created_at.desc()).limit(3)).all()
    return [r[0] for r in rows], [r[1] for r in rows[:1] if r[1]]


def save_report(db, script_id: uuid.UUID, report: Mapping[str, Any], extra: dict | None = None) -> OriginalityReport:
    flagged = [{k: f.get(k) for k in ("index", "text", "similarity", "source_index")}
               for f in report.get("flagged_sentences", [])]
    data = {k: v for k, v in report.items() if k not in ("max_similarity", "verdict", "flagged_sentences")}
    row = OriginalityReport(script_id=script_id, max_similarity=float(report.get("max_similarity", 0)),
                            verdict=report.get("verdict", "fail"), flagged_sentences=flagged,
                            data={**data, **(extra or {})})
    db.add(row)
    db.flush()
    return row


@register("script")
def run(project_id: uuid.UUID) -> StepResult:
    ctx = load_context(project_id)
    if ctx.brief is None or ctx.angle is None:
        raise RuntimeError("Brief or chosen angle missing (step 2)")
    with session_scope() as db:
        hooks, structures = _history(db, project_id)
    verified = [f for f in ctx.facts if f["status"] == "verified"]
    req = ScriptRequest(language=ctx.language, brief=ctx.brief, angle=ctx.angle, facts=verified,
                        target_words=ctx.target_words, avoid_hook_types=hooks, avoid_structures=structures)
    cctx = CallContext(project_id, "script")
    ai = ai_bridge.build(project_id)

    draft = _unchecked_draft(project_id)
    if draft is not None:  # a previous attempt paid for the draft but failed in the originality phase
        script_id, doc = draft
        with session_scope() as db:
            job_log(db, project_id, "script", "Reusing the unchecked draft from the previous attempt")
    else:
        doc = dict(ai.writer.write(req, cctx))
        script_id = _save_version(project_id, doc)

    # check -> auto-rewrite flagged sentences (max 2 rounds) -> re-check; the reference is passed
    # explicitly and never reaches the writer
    script, report = ai.originality(doc, originality_feed.load_reference(project_id), cctx)
    doc, report = dict(script), dict(report)

    text = doc["text"]
    wc = count_words(text)
    with session_scope() as db:
        s = db.get(Script, script_id)
        s.llm_draft = s.text = text
        s.data, s.word_count = doc, wc
        save_report(db, s.id, report)
        folder = project_dir(project_id, "script")
        write_text(folder / f"script_v{s.version}.md", text)
        write_json(folder / f"originality_v{s.version}.json", report)
        for e in schema_errors("script", doc):
            job_log(db, project_id, "script", f"script.schema: {e}", "warning")
        job_log(db, project_id, "script",
                f"Script v{s.version}: {wc} words (target {ctx.target_words}), originality "
                f"{report.get('verdict')} max_sim={report.get('max_similarity')}, rewrites={report.get('rewrite_rounds', 0)}")
    return StepResult.wait("approve_script")


def _save_version(project_id: uuid.UUID, doc: dict) -> uuid.UUID:
    """Persist the LLM draft right away so a later failure does not throw away a paid call."""
    text = doc["text"]
    with session_scope() as db:
        version = (db.scalar(select(func.max(Script.version)).where(Script.project_id == project_id)) or 0) + 1
        db.execute(update(Script).where(Script.project_id == project_id, Script.approved).values(approved=False))
        s = Script(project_id=project_id, version=version, llm_draft=text, text=text, data=doc,
                   word_count=count_words(text), approved=False)
        db.add(s)
        db.flush()
        write_text(project_dir(project_id, "script") / f"script_v{version}_draft.md", text)
        return s.id


def _unchecked_draft(project_id: uuid.UUID) -> tuple[uuid.UUID, dict] | None:
    """Latest version if it is an unapproved, unedited LLM draft without an originality report."""
    with session_scope() as db:
        s = db.scalar(select(Script).where(Script.project_id == project_id)
                      .order_by(Script.version.desc()).limit(1))
        if s is None or s.approved or s.text != s.llm_draft:
            return None
        has_report = db.scalar(select(OriginalityReport.id).where(OriginalityReport.script_id == s.id).limit(1))
        return None if has_report else (s.id, dict(s.data))
