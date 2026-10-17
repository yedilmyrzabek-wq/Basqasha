"""Step 6: storyboard (AI) -> repair + schema/rule check -> storyboard_v{n}.json + DB row.
Rule violations are kept in storyboard.errors; only an unusable document fails the step."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select

from app import app_settings
from app.db import session_scope
from app.media import library, storyboard_rules
from app.models import SceneComment, Storyboard
from app.pipeline import ai_bridge
from app.pipeline.context import load_context
from app.pipeline.media_state import aligned_track, current_storyboard
from app.pipeline.orchestrator import DONE, StepResult, job_log, register
from app.providers.interfaces import CallContext
from app.schemas import errors as schema_errors
from app.storage import project_dir, write_json


def save_version(project_id: uuid.UUID, doc: dict[str, Any], words_doc: dict[str, Any],
                 voice_track_id: uuid.UUID | None, origin: str) -> Storyboard:
    """Repair, validate and persist a new storyboard version (used by the step and by PUT)."""
    poses = {p["name"] for p in library.poses()}
    fixed, fixes = storyboard_rules.repair(doc, words_doc["words"], poses, set(library.sfx()))
    errs = schema_errors("storyboard", fixed) + storyboard_rules.check(fixed, words_doc["words"], poses)
    with session_scope() as db:
        n = (db.scalar(select(func.max(Storyboard.version)).where(Storyboard.project_id == project_id)) or 0) + 1
        rel = write_json(project_dir(project_id, "storyboard") / f"storyboard_v{n}.json", fixed)
        row = Storyboard(project_id=project_id, version=n, voice_track_id=voice_track_id, data=fixed, errors=errs)
        db.add(row)
        db.flush()
        if fixes:
            job_log(db, project_id, "storyboard", f"Auto-fixed {len(fixes)} issue(s): " + "; ".join(fixes[:15]),
                    "warning", {"fixes": fixes})
        job_log(db, project_id, "storyboard",
                f"Storyboard v{n} ({origin}): {len(fixed['scenes'])} scenes, {len(fixed['backgrounds'])} backgrounds, "
                f"{len(errs)} rule/schema issue(s) -> {rel}", "warning" if errs else "info",
                {"errors": errs} if errs else None)
        db.expunge(row)
        return row


def generate(project_id: uuid.UUID, operator_comments: str | None = None) -> Storyboard:
    ctx = load_context(project_id)
    if ctx.approved_script is None:
        raise RuntimeError("No approved script (step 4)")
    with session_scope() as db:
        track = aligned_track(db, project_id)
        words_doc, track_id = track.words_json, track.id
        n_backgrounds = int(app_settings.load(db).get("backgrounds_count", 30))
    poses = library.poses()
    if not poses:
        raise RuntimeError("library/poses/poses.json has no poses")
    ai = ai_bridge.build(project_id)
    doc = ai.storyboard(ctx.approved_script, words_doc, poses, sorted(library.sfx()), language=ctx.language,
                        ctx=CallContext(project_id, "storyboard"), operator_comments=operator_comments,
                        n_backgrounds=n_backgrounds)
    return save_version(project_id, dict(doc), words_doc, track_id,
                        "revised by operator comments" if operator_comments else "AI")


@register("storyboard")
def run(project_id: uuid.UUID) -> StepResult:
    generate(project_id)
    return DONE


def apply_comments(project_id: uuid.UUID) -> StepResult:
    """Operator action (preview step): unresolved scene comments -> new storyboard version.
    Returns DONE for the storyboard step, so images (unchanged slots are reused) and the preview re-run."""
    with session_scope() as db:
        sb = current_storyboard(db, project_id)
        if sb is None:
            raise RuntimeError("No storyboard")
        rows = list(db.scalars(select(SceneComment).where(SceneComment.project_id == project_id,
                                                          SceneComment.storyboard_id == sb.id,
                                                          SceneComment.resolved.is_(False))
                               .order_by(SceneComment.scene_id, SceneComment.created_at)))
        if not rows:
            raise RuntimeError("No unresolved scene comments to apply")
        scenes = {s["id"]: s for s in sb.data["scenes"]}
        lines = [f"Scene {c.scene_id} (\"{scenes.get(c.scene_id, {}).get('text', '')[:120]}\", "
                 f"background {scenes.get(c.scene_id, {}).get('background')}): {c.text}" for c in rows]
        ids = [c.id for c in rows]
    new = generate(project_id, "\n".join(lines))
    with session_scope() as db:
        for c in db.scalars(select(SceneComment).where(SceneComment.id.in_(ids))):
            c.resolved = True
        job_log(db, project_id, "storyboard", f"Applied {len(ids)} scene comment(s) -> storyboard v{new.version}")
    return DONE
