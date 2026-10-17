"""Steps 6-10: storyboard, images, preview (contact sheet + comments), renders, metadata."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import app_settings
from app.api.common import get_project, step_state
from app.db import get_db, get_read_db
from app.media import library, storyboard_rules
from app.models import Metadata, Render, SceneComment, Storyboard, VoiceTrack
from app.pipeline import orchestrator
from app.pipeline.media_state import aligned_track, current_storyboard, selected_images
from app.pipeline.steps import s06_storyboard, s07_images, s10_metadata, s11_recommendations
from app.pipeline.steps.s08_preview import scene_times
from app.schemas import errors as schema_errors
from app.storage import file_url

router = APIRouter(prefix="/api/projects/{project_id}", tags=["media"])


def invalid(detail: str, errors: list[str] | None = None) -> JSONResponse:
    """422 in the OpenAPI Error shape {detail, errors}."""
    return JSONResponse({"detail": detail, "errors": errors or []}, status_code=422)


def _not_running(db: Session, project_id: uuid.UUID, step: str) -> None:
    if orchestrator.get_step(db, project_id, step).status == "running":
        raise orchestrator.StepConflict(f"Step '{step}' is running; wait for it to finish")


# ------------------------------------------------------------------ storyboard
def storyboard_out(sb: Storyboard) -> dict[str, Any]:
    return {"version": sb.version, "data": sb.data, "errors": sb.errors or []}


@router.get("/storyboard", tags=["content"])
def get_storyboard(project_id: uuid.UUID, db: Session = Depends(get_read_db)):
    sb = current_storyboard(db, project_id)
    if sb is None:
        raise HTTPException(404, "No storyboard yet")
    return storyboard_out(sb)


@router.put("/storyboard", tags=["content"])
def save_storyboard(project_id: uuid.UUID, body: dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    get_project(db, project_id)
    orchestrator.check_can_run(db, project_id, "storyboard")
    _not_running(db, project_id, "storyboard")
    track = aligned_track(db, project_id)
    try:
        fixed, _ = storyboard_rules.repair(body, track.words_json["words"], {p["name"] for p in library.poses()},
                                           set(library.sfx()))
    except (ValueError, KeyError, TypeError) as e:
        return invalid(f"Invalid storyboard: {e}")
    errs = schema_errors("storyboard", fixed)
    if errs:
        return invalid("Storyboard schema validation failed", errs)
    sb = s06_storyboard.save_version(project_id, body, track.words_json, track.id, "edited by operator")
    orchestrator.complete_by_operator(db, project_id, "storyboard", f"Storyboard v{sb.version} saved by the operator")
    return storyboard_out(sb)


# ------------------------------------------------------------------ images
def _slots(db: Session, project_id: uuid.UUID) -> list[dict[str, Any]]:
    sb = current_storyboard(db, project_id)
    if sb is None:
        raise HTTPException(404, "No storyboard yet")
    sel = selected_images(db, project_id)
    style = (app_settings.load(db).get("style_suffix") or "").strip()
    used: dict[str, list[int]] = {}
    for s in sb.data["scenes"]:
        used.setdefault(s["background"], []).append(s["id"])
    out = []
    for bg in sb.data["backgrounds"]:
        a = sel.get(bg["id"])
        out.append({"slot": bg["id"], "prompt": bg["prompt"],
                    "flow_prompt": f"{bg['prompt'].strip()} {style}".strip(),
                    "url": file_url(a.path) if a is not None and a.path else None,
                    "qa_status": a.qa_status if a is not None else "pending",
                    "qa_notes": ((a.qa_report or {}).get("notes") if a is not None else None),
                    "attempts": a.attempts if a is not None else 0,
                    "source": a.source if a is not None else "generated",
                    "used_in_scenes": used.get(bg["id"], [])})
    return out


def _slot(db: Session, project_id: uuid.UUID, slot: str) -> dict[str, Any]:
    for s in _slots(db, project_id):
        if s["slot"] == slot:
            return s
    raise HTTPException(404, f"Slot {slot} is not in the current storyboard")


def _images_changed(db: Session, project_id: uuid.UUID, message: str) -> None:
    """After an upload / samples: finish a waiting images step, or re-run the preview if it was done."""
    ps = orchestrator.get_step(db, project_id, "images")
    try:
        orchestrator.check_can_run(db, project_id, "images")
    except orchestrator.StepConflict:
        return
    if ps.status == "done":
        orchestrator.invalidate_after(db, project_id, "images")
        orchestrator.job_log(db, project_id, "images", message)
        db.commit()
        orchestrator.queue_next(project_id, "images")
    elif s07_images.all_ok(project_id):
        orchestrator.complete_by_operator(db, project_id, "images", message)


@router.get("/images")
def list_images(project_id: uuid.UUID, db: Session = Depends(get_read_db)):
    return _slots(db, project_id)


class RegenerateIn(BaseModel):
    prompt: str | None = None


@router.post("/images/{slot}/regenerate", status_code=202)
def regenerate_image(project_id: uuid.UUID, slot: str, body: RegenerateIn | None = None,
                     db: Session = Depends(get_db)):
    _slot(db, project_id, slot)
    _not_running(db, project_id, "images")
    orchestrator.check_can_run(db, project_id, "images")
    if body and body.prompt and body.prompt.strip():
        s07_images.set_prompt(db, project_id, slot, body.prompt.strip())
    orchestrator.request_run(db, project_id, "images", task=f"regenerate_image:{slot}")
    return _slot(db, project_id, slot)


@router.post("/images/{slot}/upload")
def upload_image(project_id: uuid.UUID, slot: str, file: UploadFile = File(...),
                 license: str = Form("own:google-flow-output"), is_photoreal: bool = Form(False),
                 depicts_real_person: bool = Form(False), db: Session = Depends(get_db)):
    _slot(db, project_id, slot)
    _not_running(db, project_id, "images")
    try:
        s07_images.save_upload(project_id, slot, file.file.read(), file.filename or "upload", license=license,
                               is_photoreal=is_photoreal, depicts_real_person=depicts_real_person)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    _images_changed(db, project_id, f"{slot}: replaced by an uploaded image")
    return _slot(db, project_id, slot)


@router.post("/images/use-samples")
def use_samples(project_id: uuid.UUID, all_slots: bool = False, db: Session = Depends(get_db)):
    """Placeholder backgrounds from library/style/samples (test runs without image billing).
    Default: only slots without a usable image; ?all_slots=true replaces every slot."""
    get_project(db, project_id)
    _not_running(db, project_id, "images")
    n = s07_images.fill_samples(project_id, only_missing=not all_slots)
    _images_changed(db, project_id, f"Placeholder samples used for {n} slot(s)")
    return _slots(db, project_id)


# ------------------------------------------------------------------ preview
def _comment_out(c: SceneComment) -> dict[str, Any]:
    return {"id": c.id, "scene_id": c.scene_id, "text": c.text, "resolved": c.resolved}


def _latest_preview(db: Session, project_id: uuid.UUID) -> Render | None:
    return db.scalar(select(Render).where(Render.project_id == project_id, Render.kind == "preview")
                     .order_by(Render.created_at.desc()).limit(1))


@router.get("/preview")
def get_preview(project_id: uuid.UUID, db: Session = Depends(get_read_db)):
    r = _latest_preview(db, project_id)
    if r is None:
        raise HTTPException(404, "No preview yet")
    sb = db.get(Storyboard, r.storyboard_id) if r.storyboard_id else current_storyboard(db, project_id)
    track = db.get(VoiceTrack, sb.voice_track_id) if sb.voice_track_id else aligned_track(db, project_id)
    comments: dict[int, list] = {}
    for c in db.scalars(select(SceneComment).where(SceneComment.storyboard_id == sb.id)
                        .order_by(SceneComment.created_at)):
        comments.setdefault(c.scene_id, []).append(_comment_out(c))
    stills = (r.checks or {}).get("stills", {})
    scenes = [{"scene_id": s["id"], "still_url": file_url(stills.get(str(s["id"]))), "start": round(a, 2),
               "end": round(b, 2), "text": s["text"], "comments": comments.get(s["id"], [])}
              for s, (a, b) in zip(sb.data["scenes"], scene_times(track.words_json, sb.data))]
    return {"contact_sheet_url": file_url(r.path), "storyboard_version": sb.version, "scenes": scenes,
            "glyphs_missing": (r.checks or {}).get("glyphs_missing", [])}


class CommentIn(BaseModel):
    scene_id: int
    text: str


@router.post("/preview/comments", status_code=201)
def add_comment(project_id: uuid.UUID, body: CommentIn, db: Session = Depends(get_db)):
    r = _latest_preview(db, project_id)
    sb = db.get(Storyboard, r.storyboard_id) if r is not None and r.storyboard_id else current_storyboard(db, project_id)
    if sb is None:
        raise HTTPException(404, "No storyboard yet")
    if body.scene_id not in {s["id"] for s in sb.data["scenes"]}:
        raise HTTPException(422, f"Scene {body.scene_id} is not in storyboard v{sb.version}")
    if not body.text.strip():
        raise HTTPException(422, "Empty comment")
    c = SceneComment(project_id=project_id, storyboard_id=sb.id, scene_id=body.scene_id, text=body.text.strip())
    db.add(c)
    db.flush()
    return _comment_out(c)


@router.post("/preview/apply-comments", status_code=202)
def apply_comments(project_id: uuid.UUID, db: Session = Depends(get_db)):
    sb = current_storyboard(db, project_id)
    open_n = len(list(db.scalars(select(SceneComment.id).where(
        SceneComment.storyboard_id == sb.id, SceneComment.resolved.is_(False))))) if sb else 0
    if not open_n:
        raise orchestrator.StepConflict("No unresolved scene comments")
    return step_state(orchestrator.request_run(db, project_id, "storyboard", task="apply_comments"))


@router.post("/preview/approve", status_code=202)
def approve_preview(project_id: uuid.UUID, db: Session = Depends(get_db)):
    ps = orchestrator.get_step(db, project_id, "preview")
    if not (ps.status == "waiting_operator" and ps.wait_reason == "approve_preview"):
        raise orchestrator.StepConflict(f"Preview is not waiting for approval (status {ps.status})")
    orchestrator.complete_by_operator(db, project_id, "preview", "Preview approved")
    return step_state(orchestrator.get_step(db, project_id, "render"))


# ------------------------------------------------------------------ renders + metadata
@router.get("/renders")
def list_renders(project_id: uuid.UUID, db: Session = Depends(get_read_db)):
    rows = db.scalars(select(Render).where(Render.project_id == project_id).order_by(Render.created_at.desc()))
    return [{"id": r.id, "kind": r.kind, "url": file_url(r.path), "duration": r.duration, "checks": r.checks,
             "created_at": r.created_at} for r in rows]


@router.get("/metadata", tags=["content"])
def get_metadata(project_id: uuid.UUID, db: Session = Depends(get_read_db)):
    m = db.get(Metadata, project_id)
    if m is None:
        raise HTTPException(404, "No metadata yet")
    return {**m.data, "source_thumbnail_url": file_url(m.data.get("source_thumbnail"))}


@router.put("/metadata", tags=["content"])
def save_metadata(project_id: uuid.UUID, body: dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    get_project(db, project_id)
    body.pop("source_thumbnail_url", None)
    errs = schema_errors("metadata", body)
    if errs:
        return invalid("Metadata schema validation failed", errs)
    s10_metadata.save(db, project_id, body)
    orchestrator.job_log(db, project_id, "metadata", "Metadata edited by the operator")
    return body



# ------------------------------------------------------------------ recommendations (step 11)
@router.get("/recommendations", tags=["content"])
def get_recommendations(project_id: uuid.UUID, db: Session = Depends(get_read_db)):
    get_project(db, project_id)
    doc = s11_recommendations.load(project_id)
    if doc is None:
        raise HTTPException(404, "No recommendations yet")
    return doc


@router.patch("/recommendations/{index}", tags=["content"])
def mark_recommendation(project_id: uuid.UUID, index: int, body: dict[str, Any] = Body(...),
                        db: Session = Depends(get_db)):
    """{"done": true|false} — the operator ticks off what they added."""
    get_project(db, project_id)
    doc = s11_recommendations.load(project_id)
    if doc is None or not 0 <= index < len(doc["items"]):
        raise HTTPException(404, "No such recommendation")
    doc["items"][index]["done"] = bool(body.get("done"))
    s11_recommendations.save(project_id, doc)
    return doc
