from __future__ import annotations

import shutil
import uuid
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import app_settings, cancel
from app.api.common import get_project, list_projects as list_all, project_detail, step_state
from app.api.routers import source as source_router
from app.db import get_db, get_read_db
from app.models import STEP_KEYS, JobLog, Project, ProjectStep
from app.pipeline import orchestrator
from app.storage import project_dir

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    source_url: str | None = None
    transcript: str | None = None
    title: str | None = None
    language: Literal["kk", "ru", "en"] = "kk"
    target_seconds: int | None = Field(None, ge=60, le=3600)
    sponsored: bool = False

    @model_validator(mode="after")
    def _one_source(self):
        if not self.source_url and not self.transcript:
            raise ValueError("source_url or transcript is required")
        return self


class ProjectUpdate(BaseModel):
    title: str | None = None
    target_seconds: int | None = Field(None, ge=60, le=3600)
    sponsored: bool | None = None
    sponsor_name: str | None = None
    budget_usd: float | None = Field(None, ge=0)
    status: Literal["archived", "active"] | None = None


@router.get("")
def list_projects(db: Session = Depends(get_read_db)):
    return list_all(db)


@router.post("", status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    cfg = app_settings.load(db)
    p = Project(title=body.title or "", language=body.language,
                target_seconds=body.target_seconds or int(cfg["target_seconds"]),
                wpm_voice=Decimal(str(cfg["wpm_voice"])), budget_usd=Decimal(str(cfg["budget_project_usd"])),
                sponsored=body.sponsored, source_url=body.source_url)
    db.add(p)
    db.flush()
    orchestrator.ensure_steps(db, p.id)
    project_dir(p.id)
    orchestrator.job_log(db, p.id, "source", "Project created")
    if body.transcript:
        source_router.complete_manual(db, p.id, body.transcript)
    else:
        orchestrator.request_run(db, p.id, "source")
    return project_detail(db, p.id)


@router.get("/{project_id}")
def get_one(project_id: uuid.UUID, db: Session = Depends(get_read_db)):
    return project_detail(db, project_id)


@router.patch("/{project_id}")
def update_project(project_id: uuid.UUID, body: ProjectUpdate, db: Session = Depends(get_db)):
    p = get_project(db, project_id)
    patch = body.model_dump(exclude_unset=True)
    budget_raised = "budget_usd" in patch and Decimal(str(patch["budget_usd"])) > p.budget_usd
    target_changed = "target_seconds" in patch and patch["target_seconds"] != p.target_seconds
    for k, v in patch.items():
        setattr(p, k, Decimal(str(v)) if k == "budget_usd" else v)
    db.flush()
    if target_changed:  # word budget changed -> the script (and everything after) is stale
        orchestrator.invalidate_after(db, p.id, "facts")
    if body.status == "active":
        orchestrator.refresh_project_status(db, p.id)
    if budget_raised:  # continue a step stopped by the budget guard
        for ps in orchestrator.steps_of(db, p.id):
            if ps.status == "waiting_operator" and ps.wait_reason == "budget_exceeded":
                orchestrator.request_run(db, p.id, ps.step)
                break
    return project_detail(db, p.id)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: uuid.UUID, delete_files: bool = False, db: Session = Depends(get_db)):
    p = get_project(db, project_id)
    if db.scalar(select(ProjectStep.step).where(ProjectStep.project_id == project_id,
                                                ProjectStep.status == "running").limit(1)):
        raise orchestrator.StepConflict("Проект сейчас работает — сначала нажмите «Остановить»")
    db.delete(p)
    db.flush()
    if delete_files:
        shutil.rmtree(project_dir(project_id), ignore_errors=True)
    return Response(status_code=204)


@router.post("/{project_id}/stop", status_code=202, tags=["steps"])
def stop_project(project_id: uuid.UUID, db: Session = Depends(get_db)):
    """«Остановить»: the running step ends within a second or two (see app/cancel.py)."""
    get_project(db, project_id)
    running = db.scalars(select(ProjectStep.step).where(ProjectStep.project_id == project_id,
                                                        ProjectStep.status == "running")).all()
    if not running:
        raise orchestrator.StepConflict("Nothing is running")
    cancel.request(project_id)
    for step in running:
        orchestrator.job_log(db, project_id, step, "Stop requested by the operator", "warning")
    return {"stopping": list(running)}


# ------------------------------------------------------------------ steps
@router.post("/{project_id}/steps/{step}/run", status_code=202, tags=["steps"])
def run_step(project_id: uuid.UUID, step: Literal[STEP_KEYS], db: Session = Depends(get_db)):  # type: ignore[valid-type]
    get_project(db, project_id)
    return step_state(orchestrator.request_run(db, project_id, step))


@router.get("/{project_id}/steps/{step}/logs", tags=["steps"])
def step_logs(project_id: uuid.UUID, step: Literal[STEP_KEYS], after_id: int | None = None,  # type: ignore[valid-type]
              db: Session = Depends(get_read_db)):
    q = select(JobLog).where(JobLog.project_id == project_id, JobLog.step == step)
    if after_id is not None:
        q = q.where(JobLog.id > after_id)
    rows = db.scalars(q.order_by(JobLog.id).limit(500))
    return [{"id": r.id, "level": r.level, "message": r.message, "created_at": r.created_at, "data": r.data}
            for r in rows]
