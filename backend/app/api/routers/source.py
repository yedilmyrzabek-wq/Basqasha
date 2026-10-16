"""Step 1 UI (allowed to use app.sources — originality guard)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.common import get_project
from app.db import get_db, get_read_db
from app.pipeline import orchestrator
from app.pipeline.steps.s01_source import save_manual
from app.sources import SourceRepository

router = APIRouter(prefix="/api/projects/{project_id}/source", tags=["content"])


class TranscriptIn(BaseModel):
    transcript: str = Field(min_length=200)


def source_out(db: Session, project_id: uuid.UUID) -> dict:
    s = SourceRepository(db).get(project_id)
    if s is None:
        raise HTTPException(404, "No transcript yet")
    return {"source_url": s.source_url, "yt_title": s.yt_title, "yt_duration": s.yt_duration,
            "yt_views": s.yt_views, "origin": s.origin, "transcript": s.transcript}


def complete_manual(db: Session, project_id: uuid.UUID, text: str) -> None:
    p = get_project(db, project_id)
    ps = orchestrator.get_step(db, project_id, "source")
    if ps.status == "running":
        raise orchestrator.StepConflict("Step 'source' is running; wait for it to finish or fail")
    save_manual(db, project_id, text, p.source_url)
    orchestrator.complete_by_operator(db, project_id, "source", "Transcript pasted manually")


@router.get("")
def get_source(project_id: uuid.UUID, db: Session = Depends(get_read_db)):
    return source_out(db, project_id)


@router.put("")
def put_transcript(project_id: uuid.UUID, body: TranscriptIn, db: Session = Depends(get_db)):
    complete_manual(db, project_id, body.transcript)
    return source_out(db, project_id)
