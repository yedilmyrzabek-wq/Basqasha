"""Settings, costs, health."""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import app_settings
from app.api.common import get_project
from app.config import get_settings
from app.db import engine, get_db, get_read_db
from app.models import CostEntry

router = APIRouter(prefix="/api", tags=["settings"])

DB_HINT = "Supabase project may be paused — open dashboard → Resume project"


@router.get("/health")
def health():
    s = get_settings()
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
        db, hint = "ok", None
    except Exception:  # noqa: BLE001
        db, hint = "unreachable", DB_HINT
    tools = {name: bool(shutil.which(b) or Path(b).is_file())
             for name, b in (("ffmpeg", s.ffmpeg_bin), ("ffprobe", s.ffprobe_bin), ("node", s.node_bin))}
    try:
        import yt_dlp  # noqa: F401
        tools["yt_dlp"] = True
    except ImportError:
        tools["yt_dlp"] = False
    return {"db": db, "db_hint": hint, "last_backup_at": None, "tools": tools}


@router.get("/settings")
def get_app_settings(db: Session = Depends(get_read_db)):
    return app_settings.with_keys(app_settings.load(db))


@router.put("/settings")
@router.patch("/settings")
def save_app_settings(body: dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    if body.get("script_writer") not in (None, "gemini", "claude_code"):
        raise HTTPException(422, "script_writer must be gemini or claude_code")
    ts = body.get("target_seconds")
    if ts is not None and not 180 <= int(ts) <= 300:
        raise HTTPException(422, "target_seconds must be 180..300")
    return app_settings.with_keys(app_settings.save(db, body))


def _costs(rows: list[CostEntry], limit: float, warn: float | None) -> dict:
    by_model: dict[str, float] = {}
    for r in rows:
        by_model[r.model] = round(by_model.get(r.model, 0) + float(r.usd), 6)
    return {"total_usd": round(sum(float(r.usd) for r in rows), 6), "limit_usd": limit, "warn_usd": warn,
            "by_model": by_model,
            "entries": [{"project_id": r.project_id, "step": r.step, "provider": r.provider, "model": r.model,
                         "units": r.units, "usd": float(r.usd), "created_at": r.created_at} for r in rows]}


@router.get("/projects/{project_id}/costs")
def project_costs(project_id: uuid.UUID, db: Session = Depends(get_read_db)):
    p = get_project(db, project_id)
    rows = list(db.scalars(select(CostEntry).where(CostEntry.project_id == project_id).order_by(CostEntry.id)))
    warn = float(app_settings.load(db)["budget_project_warn_usd"])
    return _costs(rows, float(p.budget_usd), warn)


@router.get("/costs")
def month_costs(month: str | None = Query(None, pattern=r"^[0-9]{4}-[0-9]{2}$"), db: Session = Depends(get_read_db)):
    now = datetime.now(timezone.utc)
    y, m = (int(x) for x in month.split("-")) if month else (now.year, now.month)
    start = datetime(y, m, 1, tzinfo=timezone.utc)
    end = datetime(y + (m == 12), m % 12 + 1, 1, tzinfo=timezone.utc)
    rows = list(db.scalars(select(CostEntry).where(CostEntry.created_at >= start, CostEntry.created_at < end)
                           .order_by(CostEntry.id)))
    return _costs(rows, float(app_settings.load(db)["budget_month_stop_usd"]), None)
