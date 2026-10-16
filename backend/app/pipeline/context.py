"""StepContext for steps 3+: brief, chosen angle, facts, approved script. NO transcript field
(originality guard, ARCHITECTURE §4)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from app.db import session_scope
from app.models import Angle, Brief, Fact, Project, Script


@dataclass(frozen=True)
class StepContext:
    project_id: uuid.UUID
    language: str
    target_words: int
    target_seconds: int
    wpm_voice: float
    brief: dict[str, Any] | None
    angle: dict[str, Any] | None
    facts: list[dict[str, Any]] = field(default_factory=list)
    approved_script: dict[str, Any] | None = None


def fact_doc(f: Fact) -> dict[str, Any]:
    doc: dict[str, Any] = {"id": f"f{f.idx:02d}", "claim": f.claim, "value": f.value, "status": f.status,
                           "sources": f.sources or [], "on_screen": f.on_screen}
    return doc


def load_context(project_id: uuid.UUID) -> StepContext:
    with session_scope() as db:
        p = db.get(Project, project_id)
        brief = db.get(Brief, project_id)
        angle = db.scalar(select(Angle).where(Angle.project_id == project_id, Angle.chosen))
        facts = db.scalars(select(Fact).where(Fact.project_id == project_id).order_by(Fact.idx)).all()
        approved = db.scalar(select(Script).where(Script.project_id == project_id, Script.approved))
        return StepContext(
            project_id=project_id, language=p.language, target_words=p.target_words,
            target_seconds=p.target_seconds, wpm_voice=float(p.wpm_voice),
            brief=(brief.data.get("brief") if brief else None), angle=(angle.data if angle else None),
            facts=[fact_doc(f) for f in facts],
            approved_script=({**approved.data, "text": approved.text} if approved else None))
