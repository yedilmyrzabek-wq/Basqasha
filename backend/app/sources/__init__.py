"""ORIGINALITY GUARD: the source transcript lives only here.

Allowed importers (code-review rule, ARCHITECTURE §4): app/pipeline/steps/s01_source.py,
app/pipeline/steps/s02_idea.py, app/pipeline/originality_feed.py, app/api/routers/source.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, FetchedValue, ForeignKey, Integer, Text, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db import Base


class SourceMaterial(Base):
    __tablename__ = "source_material"
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project.id", ondelete="CASCADE"), primary_key=True)
    source_url: Mapped[str | None] = mapped_column(Text)
    yt_video_id: Mapped[str | None] = mapped_column(Text)
    yt_title: Mapped[str | None] = mapped_column(Text)
    yt_channel: Mapped[str | None] = mapped_column(Text)
    yt_duration: Mapped[int | None] = mapped_column(Integer)
    yt_views: Mapped[int | None] = mapped_column(BigInteger)
    views_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    origin: Mapped[str] = mapped_column(Text, default="yt_dlp")
    transcript: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=FetchedValue())


class SourceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, project_id: uuid.UUID) -> SourceMaterial | None:
        return self.db.scalar(select(SourceMaterial).where(SourceMaterial.project_id == project_id))

    def upsert(self, project_id: uuid.UUID, **fields) -> SourceMaterial:
        row = self.get(project_id)
        if row is None:
            row = SourceMaterial(project_id=project_id, **fields)
            self.db.add(row)
        else:
            for k, v in fields.items():
                setattr(row, k, v)
        self.db.flush()
        return row
