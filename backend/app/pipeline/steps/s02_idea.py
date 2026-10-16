"""Step 2: brief + 3 localization angles from the transcript; waits for the operator's choice."""
from __future__ import annotations

import uuid

from sqlalchemy import delete

from app.db import session_scope
from app.models import Angle, Brief, Project
from app.pipeline import ai_bridge
from app.pipeline.orchestrator import StepResult, job_log, register
from app.schemas import validate
from app.sources import SourceRepository
from app.storage import next_version, project_dir, write_json


@register("idea")
def run(project_id: uuid.UUID) -> StepResult:
    with session_scope() as db:
        src = SourceRepository(db).get(project_id)
        if src is None:
            raise RuntimeError("No transcript (step 1)")
        transcript, yt_title, secs, views = src.transcript, src.yt_title, src.yt_duration, src.yt_views
        language = db.get(Project, project_id).language

    doc = ai_bridge.generate_idea(project_id, transcript, language=language, source_title=yt_title,
                                  source_seconds=secs, source_views=views)
    validate("brief", doc)

    with session_scope() as db:
        folder = project_dir(project_id, "brief")
        rel = write_json(folder / f"brief_v{next_version(folder, 'brief_v', '.json')}.json", doc)
        row = db.get(Brief, project_id)
        if row is None:
            db.add(Brief(project_id=project_id, data=doc))
        else:
            row.data = doc
        db.execute(delete(Angle).where(Angle.project_id == project_id))
        for i, a in enumerate(doc["angles"], start=1):
            db.add(Angle(project_id=project_id, idx=i, data=a, is_custom=False, chosen=False))
        job_log(db, project_id, "idea", f"Brief + {len(doc['angles'])} angles -> {rel}")
    return StepResult.wait("choose_angle")
