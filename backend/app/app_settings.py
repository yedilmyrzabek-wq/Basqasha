"""Operator-editable settings (table settings.data, singleton). Seeded from .env on first start;
after that the DB wins. Secrets never go here."""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AppSettings

STYLE_SUFFIX = (
    "Flat vector illustration, minimal, warm cream paper background (#F6F1E7), thick dark ink outlines, "
    "limited palette: muted red #E4572E, teal blue #2E86AB, green #3BA55C, mustard #F2C14E. "
    "No people, no characters, no text, no letters, no logos. Large empty area in the lower-left third. "
    "Soft paper grain. 16:9."
)


def defaults() -> dict[str, Any]:
    s = get_settings()
    return {
        "models": {"text": s.model_text, "script": s.model_script, "cheap": s.model_cheap,
                   "image": s.model_image, "embed": s.model_embed},
        "script_writer": s.script_writer,
        "style_suffix": STYLE_SUFFIX,
        "target_seconds": s.default_target_seconds,
        "wpm_voice": s.default_wpm_voice,
        "similarity_threshold": 0.8,
        "budget_project_usd": s.budget_project_usd,
        "budget_project_warn_usd": s.budget_project_warn_usd,
        "budget_month_stop_usd": s.budget_month_stop_usd,
    }


def _row(db: Session) -> AppSettings:
    row = db.get(AppSettings, 1)
    if row is None:
        row = AppSettings(id=1, data={})
        db.add(row)
    if not row.data:
        row.data = defaults()
        db.flush()
    return row


_cache: tuple[float, dict[str, Any]] | None = None
CACHE_S = 15  # API and worker are separate processes; a PUT reaches the other one within 15 s


def load(db: Session, fresh: bool = False) -> dict[str, Any]:
    """DB values merged over defaults (so newly added keys get a value)."""
    global _cache
    if not fresh and _cache and time.monotonic() - _cache[0] < CACHE_S:
        return dict(_cache[1])
    d = defaults()
    stored = _row(db).data
    merged = {**d, **stored}
    merged["models"] = {**d["models"], **(stored.get("models") or {})}
    _cache = (time.monotonic(), merged)
    return dict(merged)


def save(db: Session, patch: dict[str, Any]) -> dict[str, Any]:
    global _cache
    row = _row(db)
    data = load(db, fresh=True)
    patch = {k: v for k, v in patch.items() if k != "keys"}
    if "models" in patch:
        data["models"] = {**data["models"], **(patch.pop("models") or {})}
    data.update(patch)
    row.data = data
    db.flush()
    _cache = (time.monotonic(), data)
    return data


def with_keys(data: dict[str, Any]) -> dict[str, Any]:
    s = get_settings()
    return {**data, "keys": {"gemini": bool(s.gemini_api_key), "database": bool(s.database_url)}}
