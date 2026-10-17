"""Voice (step 5: text for ElevenLabs, mp3 upload, alignment review) and the pose library (read side)."""
from __future__ import annotations

import json
import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.common import get_project, step_state
from app.config import get_settings
from app.db import get_db, get_read_db
from app.models import Pose, Script, VoiceTrack
from app.pipeline import ai_bridge, orchestrator
from app.pipeline.steps.s05_voice import save_upload
from app.storage import file_url

router = APIRouter(prefix="/api", tags=["media"])

MODEL_HINT = {"kk": "Модель: Eleven v4 (или v3). Multilingual v2 / Flash / Turbo не поддерживают казахский."}


@router.get("/projects/{project_id}/voice")
def get_voice(project_id: uuid.UUID, db: Session = Depends(get_read_db)):
    s = db.scalar(select(Script).where(Script.project_id == project_id, Script.approved))
    track = db.scalar(select(VoiceTrack).where(VoiceTrack.project_id == project_id, VoiceTrack.is_current))
    out: dict[str, Any] = {"tts_text": None, "tts_chars": 0, "tts_parts": [], "track": None,
                           "model_hint": MODEL_HINT.get(s.data.get("language", "kk") if s else "kk",
                                                        "Модель: Eleven v4.")}
    if s is not None and s.tts_text:
        parts = [s.tts_text]
        if len(s.tts_text) > 5000:
            parts = ai_bridge.tts_export({**s.data, "text": s.text}).parts
        out.update(tts_text=s.tts_text, tts_chars=len(s.tts_text), tts_parts=parts)
    if track is not None:
        quality = (track.words_json or {}).get("quality") or {}
        out["track"] = {"url": file_url(track.path or track.upload_path), "duration": track.duration,
                        "wpm_measured": track.wpm_measured, "alignment_ok": track.alignment_ok,
                        "anchored_ratio": quality.get("anchored_ratio")}
    return out


@router.post("/projects/{project_id}/voice", status_code=202)
def upload_voice(project_id: uuid.UUID, file: UploadFile = File(...),
                 model_id: Literal["eleven_v4", "eleven_v3"] = Form("eleven_v4"),
                 provider_plan: Literal["free", "starter", "creator", "pro", "unknown"] = Form("unknown"),
                 db: Session = Depends(get_db)):
    get_project(db, project_id)
    orchestrator.check_can_run(db, project_id, "voice")
    if orchestrator.get_step(db, project_id, "voice").status == "running":
        raise orchestrator.StepConflict("Voice step is running; wait for it to finish")
    try:
        save_upload(project_id, file.file.read(), model_id, provider_plan)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return step_state(orchestrator.request_run(db, project_id, "voice"))


@router.post("/projects/{project_id}/voice/accept-alignment", status_code=202)
def accept_alignment(project_id: uuid.UUID, db: Session = Depends(get_db)):
    ps = orchestrator.get_step(db, project_id, "voice")
    if not (ps.status == "waiting_operator" and ps.wait_reason == "review_alignment"):
        raise orchestrator.StepConflict(f"Voice is not waiting for an alignment review (status {ps.status})")
    orchestrator.complete_by_operator(db, project_id, "voice", "Alignment accepted by the operator")
    return step_state(orchestrator.get_step(db, project_id, "voice"))


def _library_poses() -> list[dict[str, Any]]:
    f = get_settings().library_path / "poses" / "poses.json"
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text(encoding="utf-8")).get("poses", [])
    except (ValueError, AttributeError):
        return []


@router.get("/poses", tags=["library"])
def list_poses(db: Session = Depends(get_read_db)):
    """DB pose rows (incl. inactive sheet candidates) + poses.json entries not yet in the DB."""
    out, seen = [], set()
    for p in db.scalars(select(Pose).order_by(Pose.name)):
        seen.add(p.name)
        out.append({"id": p.id, "name": p.name, "url": file_url(p.path, "library"), "width": p.width,
                    "height": p.height, "tags": p.tags, "active": p.active})
    for p in _library_poses():
        if p.get("name") in seen:
            continue
        out.append({"id": uuid.uuid5(uuid.NAMESPACE_URL, f"basqasha:pose:{p['name']}"), "name": p["name"],
                    "url": file_url(f"poses/{p.get('file', 'pose_' + p['name'] + '.png')}", "library"),
                    "width": p.get("width"), "height": p.get("height"), "tags": p.get("tags", []), "active": True})
    return out
