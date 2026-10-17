"""DB lookups shared by steps 5-10 and their routers (current script / voice / storyboard / images)."""
from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ImageAsset, Script, Storyboard, VoiceTrack
from app.storage import abs_data

OK_QA = ("passed", "manual_approved")


def approved_script(db: Session, project_id: uuid.UUID) -> Script | None:
    return db.scalar(select(Script).where(Script.project_id == project_id, Script.approved)
                     .order_by(Script.version.desc()).limit(1))


def current_track(db: Session, project_id: uuid.UUID) -> VoiceTrack | None:
    return db.scalar(select(VoiceTrack).where(VoiceTrack.project_id == project_id, VoiceTrack.is_current)
                     .order_by(VoiceTrack.created_at.desc()).limit(1))


def aligned_track(db: Session, project_id: uuid.UUID) -> VoiceTrack:
    t = current_track(db, project_id)
    if t is None or not t.words_json or not t.path:
        raise RuntimeError("No aligned voice track (step 5)")
    return t


def current_storyboard(db: Session, project_id: uuid.UUID) -> Storyboard | None:
    return db.scalar(select(Storyboard).where(Storyboard.project_id == project_id)
                     .order_by(Storyboard.version.desc()).limit(1))


def selected_images(db: Session, project_id: uuid.UUID) -> dict[str, ImageAsset]:
    rows = db.scalars(select(ImageAsset).where(ImageAsset.project_id == project_id, ImageAsset.selected)
                      .order_by(ImageAsset.created_at))
    return {r.slot: r for r in rows}  # latest selected wins


def image_ok(a: ImageAsset | None) -> bool:
    return a is not None and a.qa_status in OK_QA and bool(a.path) and abs_data(a.path).is_file()


def image_paths(db: Session, project_id: uuid.UUID, sb: dict) -> dict[str, Path]:
    """slot -> absolute image path for every background; raises if one is missing."""
    sel = selected_images(db, project_id)
    out, missing = {}, []
    for bg in sb["backgrounds"]:
        a = sel.get(bg["id"])
        if a is None or not a.path or not abs_data(a.path).is_file():
            missing.append(bg["id"])
        else:
            out[bg["id"]] = abs_data(a.path)
    if missing:
        raise RuntimeError(f"No image for {', '.join(missing)} (step 7)")
    return out
