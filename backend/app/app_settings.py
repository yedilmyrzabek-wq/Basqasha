"""Operator-editable settings (table settings.data, singleton). Seeded from .env on first start;
after that the DB wins. Secrets never go here."""
from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AppSettings

STYLE_SUFFIX = (
    "Hand-drawn flat cartoon illustration in the style of popular stickman explainer videos: clean thick dark ink "
    "outlines, flat soft colors with light simple shading, warm light cream paper background (#F6EFE0). "
    "Palette: navy blue #34466B, teal #3FA59A, beige #CDB38E, white, small accents of mustard #E9B949 and coral #E06B4F. "
    "Simple readable shapes, uncluttered. No people, no characters, no text, no letters, no numbers, no logos. "
    "Compose the main subject in the right two-thirds of the frame; the left third continues the same scene "
    "(floor, ground, wall or sky) with no important objects, so a character can stand there; keep the top band calm "
    "(sky or wall). Fill the frame — no "
    "big blank areas. 16:9."
)


def defaults() -> dict[str, Any]:
    s = get_settings()
    return {
        "models": {"text": s.model_text, "script": s.model_script, "cheap": s.model_cheap,
                   "image": s.model_image, "embed": s.model_embed},
        # Claude CLI mode (script_writer = claude_code): every text step on the Claude subscription
        "claude": {"script": s.claude_model_script, "text": s.claude_model, "cheap": s.claude_model_cheap,
                   "effort": s.claude_effort_script},
        "script_writer": s.script_writer,   # claude_code = all text via Claude CLI | gemini = all via Gemini API
        "image_source": "gemini",   # gemini | manual (operator makes them in Google Flow) | samples (placeholders)
        "style_suffix": STYLE_SUFFIX,
        "backgrounds_count": 30,    # unique backgrounds per video (each ≈ $0.05)
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
    merged["claude"] = {**d["claude"], **(stored.get("claude") or {})}
    _cache = (time.monotonic(), merged)
    return dict(merged)


def save(db: Session, patch: dict[str, Any]) -> dict[str, Any]:
    global _cache
    row = _row(db)
    data = load(db, fresh=True)
    patch = {k: v for k, v in patch.items() if k != "keys"}
    for k in ("models", "claude"):
        if k in patch:
            data[k] = {**data[k], **(patch.pop(k) or {})}
    data.update(patch)
    row.data = data
    db.flush()
    _cache = (time.monotonic(), data)
    return data


def with_keys(data: dict[str, Any]) -> dict[str, Any]:
    s = get_settings()
    return {**data, "keys": {"gemini": bool(s.gemini_api_key), "database": bool(s.database_url)}}
