"""Shared helpers for routers: lookups and OpenAPI-shaped serializers.
The DB is ~235 ms away, so project reads are one query each (project + steps + voice duration)."""
from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import app_settings
from app.models import STEP_KEYS, Project, ProjectStep, VoiceTrack
from app.pipeline import orchestrator

_voice_duration = (select(VoiceTrack.duration)
                   .where(VoiceTrack.project_id == Project.id, VoiceTrack.is_current)
                   .limit(1).correlate(Project).scalar_subquery())


def get_project(db: Session, project_id: uuid.UUID) -> Project:
    p = db.get(Project, project_id)
    if p is None:
        raise HTTPException(404, "Project not found")
    return p


def step_state(ps: ProjectStep) -> dict[str, Any]:
    return {"step": ps.step, "status": ps.status, "wait_reason": ps.wait_reason, "progress": ps.progress,
            "error": ps.error, "attempts": ps.attempts, "updated_at": ps.updated_at}


def _ordered(steps: list[ProjectStep]) -> list[ProjectStep]:
    return sorted(steps, key=lambda s: STEP_KEYS.index(s.step))


def project_out(p: Project, steps: list[ProjectStep], duration: float | None) -> dict[str, Any]:
    return {
        "id": p.id, "title": p.title, "status": p.status, "language": p.language,
        "target_seconds": p.target_seconds, "target_words": p.target_words, "wpm_voice": float(p.wpm_voice),
        "duration": duration, "cost_usd": float(p.cost_usd), "budget_usd": float(p.budget_usd),
        "sponsored": p.sponsored, "sponsor_name": p.sponsor_name, "source_url": p.source_url,
        "current_step": orchestrator.current_step(steps) if steps else "source",
        "created_at": p.created_at,
    }


def list_projects(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(select(Project, ProjectStep, _voice_duration)
                      .outerjoin(ProjectStep, ProjectStep.project_id == Project.id)
                      .order_by(Project.created_at.desc())).all()
    order, projects, steps, durs = [], {}, defaultdict(list), {}
    for p, ps, dur in rows:
        if p.id not in projects:
            order.append(p.id)
            projects[p.id], durs[p.id] = p, dur
        if ps is not None:
            steps[p.id].append(ps)
    return [project_out(projects[i], _ordered(steps[i]), durs[i]) for i in order]


def project_detail(db: Session, project_id: uuid.UUID) -> dict[str, Any]:
    db.expire_all()  # after writes in this session: re-read trigger-maintained columns (cost_usd)
    rows = db.execute(select(Project, ProjectStep, _voice_duration)
                      .outerjoin(ProjectStep, ProjectStep.project_id == Project.id)
                      .where(Project.id == project_id)).all()
    if not rows:
        raise HTTPException(404, "Project not found")
    p, dur = rows[0][0], rows[0][2]
    steps = _ordered([r[1] for r in rows if r[1] is not None])
    return {**project_out(p, steps, dur), "steps": [step_state(s) for s in steps],
            "budget_warn_usd": float(app_settings.load(db)["budget_project_warn_usd"])}
