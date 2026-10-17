"""Queued operator actions that need LLM calls (run by tasks.operator_task)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update

from app.db import session_scope
from app.models import Project, Script
from app.pipeline import ai_bridge, originality_feed
from app.pipeline.orchestrator import DONE, StepResult, job_log
from app.pipeline.steps.s04_script import save_report
from app.pipeline.steps.s06_storyboard import apply_comments
from app.pipeline.steps.s07_images import regenerate
from app.providers.interfaces import CallContext
from app.storage import project_dir, write_text
from app.text import count_words, edit_ratio, sync_beats


def current_script(db, project_id: uuid.UUID) -> Script | None:
    return db.scalar(select(Script).where(Script.project_id == project_id)
                     .order_by(Script.version.desc()).limit(1))


def approve_script(project_id: uuid.UUID) -> StepResult:
    """«Утвердить»: re-check originality of the edited text, then freeze the version."""
    with session_scope() as db:
        s = current_script(db, project_id)
        if s is None:
            raise RuntimeError("No script to approve")
        doc = sync_beats(s.data, s.text)
        script_id = s.id
    ai = ai_bridge.build(project_id)
    report = dict(ai.checker.check(doc, originality_feed.load_reference(project_id), CallContext(project_id, "script")))
    report.setdefault("verdict", "fail" if report.get("flagged_sentences") else "pass")
    tts = ai.tts(doc)
    with session_scope() as db:
        save_report(db, script_id, report, {"on_approve": True})
        if report.get("verdict") == "fail":
            job_log(db, project_id, "script", "Originality check failed on approve "
                    f"(max_sim={report.get('max_similarity')}); edit the flagged sentences and approve again",
                    "warning")
            return StepResult.wait("approve_script")
        db.execute(update(Script).where(Script.project_id == project_id, Script.approved).values(approved=False))
        s = db.get(Script, script_id)
        s.approved, s.approved_at = True, datetime.now(timezone.utc)
        s.edit_ratio = edit_ratio(s.llm_draft, s.text)
        s.word_count = count_words(s.text)
        s.data = doc
        s.tts_text = tts.text
        write_text(project_dir(project_id, "script") / f"tts_v{s.version}.txt", tts.text)
        for issue in tts.issues:
            job_log(db, project_id, "script", f"TTS text issue: {issue}", "warning")
        p = db.get(Project, project_id)
        p.hook_type = s.data.get("hook_type") or p.hook_type
        p.structure_id = s.data.get("structure_id") or p.structure_id
        job_log(db, project_id, "script", f"Script v{s.version} approved (edit_ratio={s.edit_ratio})")
    return DONE


ACTIONS = {"approve_script": approve_script, "apply_comments": apply_comments, "regenerate_image": regenerate}
