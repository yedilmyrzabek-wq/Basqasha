"""ORM mapping of supabase/migrations/0001_init.sql (the DB is the source of truth; no DDL here).

source_material is deliberately NOT here: it lives in app.sources (originality guard).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (BigInteger, Boolean, Computed, Date, DateTime, FetchedValue, ForeignKey,
                        Integer, Numeric, REAL, SmallInteger, Text)
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

STEP_KEYS = ("source", "idea", "facts", "script", "voice",
             "storyboard", "images", "preview", "render", "metadata")

LanguageE = ENUM("kk", "ru", "en", name="language_code", create_type=False)
StepKeyE = ENUM(*STEP_KEYS, name="step_key", create_type=False)
StepStatusE = ENUM("pending", "running", "waiting_operator", "done", "failed", "stale",
                   name="step_status", create_type=False)
ProjectStatusE = ENUM("active", "waiting_operator", "failed", "ready", "published", "archived",
                      name="project_status", create_type=False)
HookTypeE = ENUM("question", "number", "paradox", "scene", "myth", name="hook_type", create_type=False)
FactStatusE = ENUM("verified", "unverified", "conflicting", "rejected", name="fact_status", create_type=False)
ImageQaE = ENUM("pending", "passed", "failed", "needs_manual", "manual_approved",
                name="image_qa_status", create_type=False)
RenderKindE = ENUM("preview", "full", "short", name="render_kind", create_type=False)

DB = FetchedValue()  # column default/trigger lives in the database


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=DB)


def created() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=DB)


def updated() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=DB, server_onupdate=DB)


def project_fk(**kw: Any) -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), ForeignKey("project.id", ondelete="CASCADE"), **kw)


class Project(Base):
    __tablename__ = "project"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(Text, server_default=DB)
    status: Mapped[str] = mapped_column(ProjectStatusE, server_default=DB)
    language: Mapped[str] = mapped_column(LanguageE, server_default=DB)
    script: Mapped[str] = mapped_column(Text, server_default=DB)
    target_seconds: Mapped[int] = mapped_column(Integer, server_default=DB)
    wpm_voice: Mapped[Decimal] = mapped_column(Numeric(5, 1), server_default=DB)
    target_words: Mapped[int] = mapped_column(Integer, Computed("round(wpm_voice * target_seconds / 60)::int"))
    source_url: Mapped[str | None] = mapped_column(Text)
    hook_type: Mapped[str | None] = mapped_column(HookTypeE)
    structure_id: Mapped[str | None] = mapped_column(Text)
    sponsored: Mapped[bool] = mapped_column(Boolean, server_default=DB)
    sponsor_name: Mapped[str | None] = mapped_column(Text)
    budget_usd: Mapped[Decimal] = mapped_column(Numeric(8, 2), server_default=DB)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), server_default=DB)
    published_url: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


class ProjectStep(Base):
    __tablename__ = "project_step"
    __mapper_args__ = {"eager_defaults": True}
    project_id: Mapped[uuid.UUID] = project_fk(primary_key=True)
    step: Mapped[str] = mapped_column(StepKeyE, primary_key=True)
    status: Mapped[str] = mapped_column(StepStatusE, server_default=DB)
    wait_reason: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, server_default=DB)
    progress: Mapped[float | None] = mapped_column(REAL)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = updated()


class Brief(Base):
    __tablename__ = "brief"
    project_id: Mapped[uuid.UUID] = project_fk(primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created()


class Angle(Base):
    __tablename__ = "angle"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = project_fk()
    idx: Mapped[int] = mapped_column(Integer)
    data: Mapped[dict] = mapped_column(JSONB)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    chosen: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created()


class Fact(Base):
    __tablename__ = "fact"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = project_fk()
    idx: Mapped[int] = mapped_column(Integer, default=0)
    claim: Mapped[str] = mapped_column(Text)
    value: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)
    sources: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(FactStatusE, default="unverified")
    on_screen: Mapped[bool] = mapped_column(Boolean, default=False)
    edited_by_operator: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = updated()


class Script(Base):
    __tablename__ = "script"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = project_fk()
    version: Mapped[int] = mapped_column(Integer)
    llm_draft: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    edit_ratio: Mapped[float | None] = mapped_column(REAL)
    tts_text: Mapped[str | None] = mapped_column(Text)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


class OriginalityReport(Base):
    __tablename__ = "originality_report"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = uuid_pk()
    script_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("script.id", ondelete="CASCADE"))
    max_similarity: Mapped[float] = mapped_column(REAL)
    verdict: Mapped[str] = mapped_column(Text)
    flagged_sentences: Mapped[list] = mapped_column(JSONB, default=list)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = created()


class VoiceTrack(Base):
    __tablename__ = "voice_track"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = project_fk()
    script_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("script.id", ondelete="CASCADE"))
    upload_path: Mapped[str] = mapped_column(Text)
    path: Mapped[str | None] = mapped_column(Text)
    duration: Mapped[float | None] = mapped_column(REAL)
    words_json: Mapped[dict | None] = mapped_column(JSONB)
    provider: Mapped[str] = mapped_column(Text, default="manual_upload")
    provider_plan: Mapped[str] = mapped_column(Text, default="unknown")
    model_id: Mapped[str] = mapped_column(Text, default="eleven_v4")
    wpm_measured: Mapped[float | None] = mapped_column(REAL)
    alignment_ok: Mapped[bool | None] = mapped_column(Boolean)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = created()


class Storyboard(Base):
    __tablename__ = "storyboard"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = project_fk()
    version: Mapped[int] = mapped_column(Integer)
    voice_track_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("voice_track.id", ondelete="SET NULL"))
    data: Mapped[dict] = mapped_column(JSONB)
    errors: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = created()


class ImageAsset(Base):
    __tablename__ = "image_asset"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = project_fk()
    slot: Mapped[str] = mapped_column(Text)
    prompt: Mapped[str] = mapped_column(Text)
    path: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, default="generated")
    license: Mapped[str] = mapped_column(Text, default="own:gemini-api-output")
    is_photoreal: Mapped[bool] = mapped_column(Boolean, default=False)
    depicts_real_person: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    qa_status: Mapped[str] = mapped_column(ImageQaE, default="pending")
    qa_report: Mapped[dict | None] = mapped_column(JSONB)
    selected: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = created()


class Pose(Base):
    __tablename__ = "pose"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(Text, unique=True)
    path: Mapped[str] = mapped_column(Text)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = created()


class SceneComment(Base):
    __tablename__ = "scene_comment"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = project_fk()
    storyboard_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("storyboard.id", ondelete="CASCADE"))
    scene_id: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created()


class Render(Base):
    __tablename__ = "render"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[uuid.UUID] = uuid_pk()
    project_id: Mapped[uuid.UUID] = project_fk()
    kind: Mapped[str] = mapped_column(RenderKindE)
    storyboard_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("storyboard.id", ondelete="SET NULL"))
    path: Mapped[str | None] = mapped_column(Text)
    props_path: Mapped[str | None] = mapped_column(Text)
    duration: Mapped[float | None] = mapped_column(REAL)
    checks: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = created()


class Metadata(Base):
    __tablename__ = "metadata"
    project_id: Mapped[uuid.UUID] = project_fk(primary_key=True)
    data: Mapped[dict] = mapped_column(JSONB)
    made_for_kids: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_disclosure: Mapped[bool] = mapped_column(Boolean, default=False)
    paid_promotion: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = updated()


class AppSettings(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, default=1)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = updated()


class JobLog(Base):
    __tablename__ = "job_log"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, server_default=DB)
    project_id: Mapped[uuid.UUID | None] = project_fk(nullable=True)
    step: Mapped[str | None] = mapped_column(StepKeyE)
    level: Mapped[str] = mapped_column(Text, default="info")
    message: Mapped[str] = mapped_column(Text)
    data: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = created()


class Pricing(Base):
    __tablename__ = "pricing"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, server_default=DB)
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    unit: Mapped[str] = mapped_column(Text)
    usd_per_unit: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    effective_from: Mapped[date] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(Text)


class CostEntry(Base):
    __tablename__ = "cost_entry"
    __mapper_args__ = {"eager_defaults": True}
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, server_default=DB)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("project.id", ondelete="SET NULL"))
    step: Mapped[str | None] = mapped_column(StepKeyE)
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    tier: Mapped[str] = mapped_column(Text, default="standard")
    units: Mapped[dict] = mapped_column(JSONB, default=dict)
    usd: Mapped[Decimal] = mapped_column(Numeric(10, 6))
    created_at: Mapped[datetime] = created()
