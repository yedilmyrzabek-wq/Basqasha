"""Step 10: YouTube metadata (titles, description with sources + chapters, tags, thumbnail texts,
publish checklist) -> meta/meta.md + metadata row."""
from __future__ import annotations

import uuid
from typing import Any

from app.db import session_scope
from app.models import Metadata, Project
from app.pipeline import ai_bridge, originality_feed
from app.pipeline.context import load_context
from app.pipeline.media_state import aligned_track, current_storyboard, selected_images
from app.pipeline.orchestrator import DONE, StepResult, job_log, register
from app.providers.interfaces import CallContext
from app.schemas import errors as schema_errors
from app.media import library
from app.sources import SourceRepository, youtube
from app.storage import project_dir, rel, write_text

PAID_PLANS = ("starter", "creator", "pro")


def source_thumbnail(project_id: uuid.UUID, video_id: str | None):
    """The competitor's thumbnail, downloaded once to data/projects/{id}/source/thumb.jpg."""
    return youtube.thumbnail(video_id, project_dir(project_id, "source") / "thumb.jpg")


def checklist(db, project_id: uuid.UUID) -> dict[str, Any]:
    p = db.get(Project, project_id)
    sb = current_storyboard(db, project_id)
    used = {bg["id"] for bg in sb.data["backgrounds"]} if sb else set()
    imgs = [a for slot, a in selected_images(db, project_id).items() if slot in used]
    plan = aligned_track(db, project_id).provider_plan
    out: dict[str, Any] = {"made_for_kids": False,
                           "ai_disclosure": any(a.is_photoreal or a.depicts_real_person for a in imgs),
                           "paid_promotion": bool(p.sponsored)}
    if plan in PAID_PLANS or plan == "free":
        out["voice_plan_paid"] = plan in PAID_PLANS
    return out


def to_markdown(m: dict[str, Any]) -> str:
    lines = ["# Titles", *[f"{i}. {t}" for i, t in enumerate(m["titles"], 1)], "", "# Description", m["description"], "",
             "# Chapters", *[f"{c['at']} {c['title']}" for c in m["chapters"]], "", "# Sources",
             *[f"- {s.get('title') or s['url']}: {s['url']}" for s in m["sources"]], ""]
    if m.get("hashtags"):
        lines += ["# Hashtags", " ".join(m["hashtags"]), ""]
    if m.get("tags"):
        lines += ["# Tags", ", ".join(m["tags"]), ""]
    lines += ["# Thumbnail texts", *[f"- {t}" for t in m["thumbnail_texts"]], ""]
    if m.get("thumbnail_prompts"):
        lines += ["# Thumbnail prompts (Google Flow)", *[f"{i}. {t}" for i, t in enumerate(m["thumbnail_prompts"], 1)], ""]
    if m.get("packaging_notes"):
        lines += ["# Packaging analysis (source video)", m["packaging_notes"], ""]
    lines += ["# Checklist",
              *[f"- {k}: {v}" for k, v in m["checklist"].items()], ""]
    return "\n".join(lines)


def save(db, project_id: uuid.UUID, m: dict[str, Any]) -> None:
    row = db.get(Metadata, project_id) or Metadata(project_id=project_id, data={})
    row.data = m
    c = m.get("checklist", {})
    row.made_for_kids, row.ai_disclosure, row.paid_promotion = (bool(c.get("made_for_kids")),
                                                               bool(c.get("ai_disclosure")), bool(c.get("paid_promotion")))
    db.merge(row)
    write_text(project_dir(project_id, "meta") / "meta.md", to_markdown(m))


@register("metadata")
def run(project_id: uuid.UUID) -> StepResult:
    ctx = load_context(project_id)
    if ctx.approved_script is None:
        raise RuntimeError("No approved script (step 4)")
    with session_scope() as db:
        sb = current_storyboard(db, project_id)
        if sb is None:
            raise RuntimeError("No storyboard (step 6)")
        sb_doc, words_doc = sb.data, aligned_track(db, project_id).words_json
        chk = checklist(db, project_id)
        src = SourceRepository(db).get(project_id)
        src_title, src_views, src_vid = ((src.yt_title, src.yt_views, src.yt_video_id) if src else (None, None, None))
    thumb = source_thumbnail(project_id, src_vid)
    facts_doc = {"language": ctx.language, "facts": ctx.facts}
    try:
        reference = originality_feed.load_reference(project_id)
    except RuntimeError as e:  # e.g. a project without a step-1 transcript
        reference = None
        with session_scope() as db:
            job_log(db, project_id, "metadata", f"Title-overlap check skipped: {e}", "warning")
    ai = ai_bridge.build(project_id)
    m = dict(ai.metadata(ctx.approved_script, facts_doc, sb_doc, language=ctx.language,
                         ctx=CallContext(project_id, "metadata"), words_doc=words_doc,
                         ai_disclosure=chk["ai_disclosure"], paid_promotion=chk["paid_promotion"],
                         voice_plan_paid=chk.get("voice_plan_paid"),
                         reference=reference, source_title=src_title or "", source_views=src_views,
                         source_thumb=thumb, character_block=library.character_block()))
    if thumb:
        m["source_thumbnail"] = rel(thumb)
    m["checklist"] = {**m.get("checklist", {}), **chk}
    with session_scope() as db:
        for e in schema_errors("metadata", m):
            job_log(db, project_id, "metadata", f"metadata.schema: {e}", "warning")
        save(db, project_id, m)
        job_log(db, project_id, "metadata", f"{len(m.get('titles', []))} titles, {len(m.get('chapters', []))} chapters "
                f"-> meta/meta.md")
    return DONE
