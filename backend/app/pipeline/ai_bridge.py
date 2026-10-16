"""The only place the pipeline touches backend/ai (ai-engineer): ai.factory.build_ai wired with
the DB cost ledger and the operator settings (models, writer, wpm, similarity threshold)."""
from __future__ import annotations

import uuid
from typing import Any, Mapping

from app import app_settings
from app.config import get_settings
from app.costs import ledger
from app.db import session_scope
from app.models import Project
from app.providers.interfaces import CallContext, OriginalityReference


def build(project_id: uuid.UUID | None = None):
    from ai.factory import build_ai  # imported lazily so the API starts even if ai/ is broken

    with session_scope() as db:
        cfg = app_settings.load(db)
        wpm = float(db.get(Project, project_id).wpm_voice) if project_id else float(cfg["wpm_voice"])
    m = cfg["models"]
    settings = get_settings().model_copy(update={
        "model_text": m["text"], "model_script": m["script"], "model_cheap": m["cheap"],
        "model_image": m["image"], "model_embed": m["embed"]})
    return build_ai(ledger, settings, wpm=wpm, script_writer=cfg["script_writer"],
                    similarity_threshold=float(cfg["similarity_threshold"]))


def generate_idea(project_id: uuid.UUID, transcript: str, *, language: str, source_title: str | None,
                  source_seconds: int | None, source_views: int | None) -> dict[str, Any]:
    """Step 2: brief.schema.json document (brief + exactly 3 angles)."""
    return build(project_id).idea(transcript, language=language, ctx=CallContext(project_id, "idea"),
                                  source_title=source_title or "", source_minutes=(source_seconds or 0) / 60,
                                  source_views=source_views)


def research_facts(project_id: uuid.UUID, brief: Mapping[str, Any], angle: Mapping[str, Any],
                   language: str) -> tuple[dict[str, Any], str]:
    """Step 3: (facts.schema.json document, method)."""
    r = build(project_id).facts(brief, angle, language=language, ctx=CallContext(project_id, "facts"))
    return r.doc, r.method


def tts_export(script: Mapping[str, Any]):
    from ai.factory import AI
    return AI.tts(script)
