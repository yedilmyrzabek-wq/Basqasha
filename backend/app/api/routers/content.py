"""Steps 2-4 content: idea/angles, facts, script."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.api.common import get_project, step_state
from app.db import get_db, get_read_db
from app.models import Angle, Brief, Fact, OriginalityReport, Script
from app.pipeline import orchestrator, originality_feed
from app.pipeline.context import fact_doc
from app.pipeline.operator_actions import current_script
from app.pipeline.steps.s03_facts import fact_idx, fact_row
from app.schemas import errors as schema_errors
from app.text import count_words, sync_beats, within_budget

router = APIRouter(prefix="/api/projects/{project_id}", tags=["content"])


# ------------------------------------------------------------------ idea
@router.get("/idea")
def get_idea(project_id: uuid.UUID, db: Session = Depends(get_read_db)):
    get_project(db, project_id)
    brief = db.get(Brief, project_id)
    angles = db.scalars(select(Angle).where(Angle.project_id == project_id).order_by(Angle.idx, Angle.created_at))
    return {"brief": brief.data.get("brief") if brief else None,
            "angles": [{"id": a.id, "chosen": a.chosen, "is_custom": a.is_custom, "data": a.data} for a in angles]}


def _choose(db: Session, project_id: uuid.UUID, angle: Angle) -> dict:
    ps = orchestrator.get_step(db, project_id, "idea")
    if ps.status not in ("waiting_operator", "done", "stale"):
        raise orchestrator.StepConflict(f"Step 'idea' is {ps.status}; angles can be chosen once it has produced them")
    db.execute(update(Angle).where(Angle.project_id == project_id, Angle.id != angle.id).values(chosen=False))
    db.flush()
    angle.chosen = True
    p = get_project(db, project_id)
    if not p.title:
        p.title = angle.data.get("title", "")
    db.flush()
    orchestrator.complete_by_operator(db, project_id, "idea", f"Angle chosen: {angle.data.get('title')}")
    return step_state(orchestrator.get_step(db, project_id, "facts"))


@router.post("/angles/{angle_id}/choose", status_code=202)
def choose_angle(project_id: uuid.UUID, angle_id: uuid.UUID, db: Session = Depends(get_db)):
    a = db.get(Angle, angle_id)
    if a is None or a.project_id != project_id:
        raise HTTPException(404, "Angle not found")
    return _choose(db, project_id, a)


@router.post("/angles/custom", status_code=202)
def custom_angle(project_id: uuid.UUID, body: dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    get_project(db, project_id)
    errs = schema_errors("brief", body, "angle")
    if errs:
        raise HTTPException(422, {"detail": "Invalid angle", "errors": errs})
    a = Angle(project_id=project_id, idx=0, data=body, is_custom=True, chosen=False)
    db.add(a)
    db.flush()
    return _choose(db, project_id, a)


# ------------------------------------------------------------------ facts
def fact_out(f: Fact) -> dict:
    return {"id": f.id, "fact": fact_doc(f), "edited_by_operator": f.edited_by_operator}


def _check_fact(body: dict) -> None:
    errs = schema_errors("facts", body, "fact")
    if errs:
        raise HTTPException(422, {"detail": "Invalid fact", "errors": errs})


def _facts_changed(db: Session, project_id: uuid.UUID, msg: str) -> None:
    orchestrator.job_log(db, project_id, "facts", msg)
    orchestrator.invalidate_after(db, project_id, "facts")


@router.get("/facts")
def list_facts(project_id: uuid.UUID, db: Session = Depends(get_read_db)):
    rows = db.scalars(select(Fact).where(Fact.project_id == project_id).order_by(Fact.idx))
    return [fact_out(f) for f in rows]


@router.post("/facts", status_code=201)
def create_fact(project_id: uuid.UUID, body: dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    get_project(db, project_id)
    _check_fact(body)
    max_idx = db.scalar(select(func.max(Fact.idx)).where(Fact.project_id == project_id)) or 0
    idx = fact_idx(body.get("id"), max_idx + 1)
    if db.scalar(select(Fact.id).where(Fact.project_id == project_id, Fact.idx == idx)):
        idx = max_idx + 1
    f = fact_row(project_id, body, idx, edited=True)
    db.add(f)
    db.flush()
    _facts_changed(db, project_id, f"Fact f{idx:02d} added by operator")
    return fact_out(f)


@router.put("/facts/{fact_id}")
def update_fact(project_id: uuid.UUID, fact_id: uuid.UUID, body: dict[str, Any] = Body(...),
                db: Session = Depends(get_db)):
    f = db.get(Fact, fact_id)
    if f is None or f.project_id != project_id:
        raise HTTPException(404, "Fact not found")
    _check_fact(body)
    new = fact_row(project_id, body, f.idx, edited=True)
    for k in ("claim", "value", "source_url", "sources", "status", "on_screen", "edited_by_operator"):
        setattr(f, k, getattr(new, k))
    db.flush()
    _facts_changed(db, project_id, f"Fact f{f.idx:02d} edited by operator")
    return fact_out(f)


@router.delete("/facts/{fact_id}", status_code=204)
def delete_fact(project_id: uuid.UUID, fact_id: uuid.UUID, db: Session = Depends(get_db)):
    f = db.get(Fact, fact_id)
    if f is None or f.project_id != project_id:
        raise HTTPException(404, "Fact not found")
    db.delete(f)
    db.flush()
    _facts_changed(db, project_id, f"Fact f{f.idx:02d} deleted by operator")
    return Response(status_code=204)


# ------------------------------------------------------------------ script
class ScriptSave(BaseModel):
    text: str
    version: int


def script_out(db: Session, project_id: uuid.UUID) -> dict:
    p = get_project(db, project_id)
    s = current_script(db, project_id)
    if s is None:
        raise HTTPException(404, "No script yet")
    wpm = float(p.wpm_voice)
    rep = db.scalar(select(OriginalityReport).where(OriginalityReport.script_id == s.id)
                    .order_by(OriginalityReport.created_at.desc()).limit(1))
    originality = None
    if rep is not None:
        ex = originality_feed.excerpts(project_id, [f.get("source_index") for f in rep.flagged_sentences])
        flagged = [{**f, "source_excerpt": ex.get(f.get("source_index"))} for f in rep.flagged_sentences]
        originality = {"max_similarity": rep.max_similarity, "verdict": rep.verdict, "flagged_sentences": flagged,
                       "created_at": rep.created_at}
    return {"version": s.version, "llm_draft": s.llm_draft, "text": s.text, "approved": s.approved,
            "word_count": s.word_count, "target_words": p.target_words,
            "est_seconds": round(s.word_count / wpm * 60, 1), "within_budget": within_budget(s.word_count, p.target_words),
            "data": s.data, "originality": originality}


@router.get("/script")
def get_script(project_id: uuid.UUID, db: Session = Depends(get_read_db)):
    return script_out(db, project_id)


@router.put("/script")
def save_script(project_id: uuid.UUID, body: ScriptSave, db: Session = Depends(get_db)):
    s = current_script(db, project_id)
    if s is None:
        raise HTTPException(404, "No script yet")
    if body.version != s.version:
        raise orchestrator.StepConflict(f"Version changed: current is v{s.version}")
    ps = orchestrator.get_step(db, project_id, "script")
    if ps.status == "running":
        raise orchestrator.StepConflict("Script step is running")
    wc = count_words(body.text)
    if s.approved:  # approved text is frozen: edits create a new version that needs approval again
        n = Script(project_id=project_id, version=s.version + 1, llm_draft=s.llm_draft, text=body.text,
                   data=sync_beats(s.data, body.text), word_count=wc, approved=False)
        db.add(n)
        db.flush()
        orchestrator.set_state(db, project_id, "script", "waiting_operator", wait_reason="approve_script")
        orchestrator.invalidate_after(db, project_id, "script")
        orchestrator.job_log(db, project_id, "script", f"Approved script edited -> new version v{n.version}")
    else:
        s.text, s.word_count, s.data = body.text, wc, sync_beats(s.data, body.text)
        db.flush()
    return script_out(db, project_id)


@router.post("/script/approve", status_code=202)
def approve_script(project_id: uuid.UUID, db: Session = Depends(get_db)):
    ps = orchestrator.get_step(db, project_id, "script")
    if not (ps.status == "waiting_operator" and ps.wait_reason == "approve_script"):
        raise orchestrator.StepConflict(f"Script is not waiting for approval (status {ps.status})")
    return step_state(orchestrator.request_run(db, project_id, "script", task="approve_script"))
