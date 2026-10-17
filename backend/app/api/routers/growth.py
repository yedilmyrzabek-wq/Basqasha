"""«Конкуренты» — growth manager: competitor items, playbook synthesis, questions, doc changes."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import growth
from app.db import get_db, get_read_db
from app.models import CompetitorItem, GrowthReport
from app.storage import file_url, rel

router = APIRouter(prefix="/api/growth", tags=["growth"])
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def item_out(it: CompetitorItem) -> dict[str, Any]:
    return {"id": it.id, "kind": it.kind, "url": it.url, "title": it.title, "channel": it.channel,
            "views": it.views, "duration_s": it.duration_s,
            "published": it.published.isoformat() if it.published else None, "notes": it.notes,
            "images": [file_url(p) for p in (it.images or [])], "info": it.info or {}, "status": it.status,
            "error": it.error, "analysis": it.analysis, "created_at": it.created_at}


def report_out(r: GrowthReport) -> dict[str, Any]:
    return {"id": r.id, "kind": r.kind, "question": r.question, "status": r.status, "error": r.error,
            "data": r.data, "applied_at": r.applied_at, "created_at": r.created_at}


def _save_images(item_id: uuid.UUID, files: list[UploadFile]) -> list[str]:
    from PIL import Image

    out = []
    folder = growth.growth_dir(str(item_id))
    for k, f in enumerate(files or []):
        if not f.filename:
            continue
        dst = folder / f"own_{datetime.now().strftime('%H%M%S')}_{k}.png"
        try:
            with Image.open(f.file) as im:
                im.convert("RGB").save(dst)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(422, f"Not an image: {f.filename} ({e})") from e
        out.append(rel(dst))
    return out


def _queue_item(db: Session, it: CompetitorItem) -> None:
    from app.pipeline import tasks

    it.status, it.error = "pending", None
    db.commit()
    tasks.growth_item_task(str(it.id))


@router.get("/items")
def list_items(db: Session = Depends(get_read_db)):
    return [item_out(i) for i in db.scalars(select(CompetitorItem).order_by(CompetitorItem.created_at.desc()))]


@router.post("/items", status_code=201)
def create_item(url: str = Form(""), notes: str = Form(""), title: str = Form(""),
                files: list[UploadFile] = File(default=[]), db: Session = Depends(get_db)):
    url = url.strip() or None
    if not url and not any(f.filename for f in files or []):
        raise HTTPException(422, "Нужна ссылка (видео или канал) или хотя бы одна картинка")
    it = CompetitorItem(kind=growth.kind_of(url), url=url, title=title.strip(), notes=notes.strip(), images=[],
                        info={})
    db.add(it)
    db.flush()
    it.images = _save_images(it.id, files)
    _queue_item(db, it)
    return item_out(it)


@router.patch("/items/{item_id}")
def update_item(item_id: uuid.UUID, notes: str | None = Form(None), files: list[UploadFile] = File(default=[]),
                reanalyze: bool = Form(True), db: Session = Depends(get_db)):
    it = db.get(CompetitorItem, item_id)
    if it is None:
        raise HTTPException(404, "Not found")
    if notes is not None:
        it.notes = notes.strip()
    new = _save_images(it.id, files)
    if new:
        it.images = [*(it.images or []), *new]
    if reanalyze and it.status != "running":
        _queue_item(db, it)
    return item_out(it)


@router.post("/items/{item_id}/analyze", status_code=202)
def reanalyze(item_id: uuid.UUID, refetch: bool = False, db: Session = Depends(get_db)):
    it = db.get(CompetitorItem, item_id)
    if it is None:
        raise HTTPException(404, "Not found")
    if it.status == "running":
        raise HTTPException(409, "Уже разбирается")
    if refetch:
        it.info = {}
    _queue_item(db, it)
    return item_out(it)


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: uuid.UUID, db: Session = Depends(get_db)):
    it = db.get(CompetitorItem, item_id)
    if it is not None:
        db.delete(it)


@router.get("/reports")
def list_reports(db: Session = Depends(get_read_db)):
    return [report_out(r) for r in db.scalars(select(GrowthReport).order_by(GrowthReport.created_at.desc()).limit(30))]


@router.post("/reports", status_code=201)
def create_report(body: dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    """{"kind": "synthesis"} = update the playbook + docs; {"kind": "question", "question": "..."}"""
    from app.pipeline import tasks

    kind = body.get("kind")
    q = (body.get("question") or "").strip()
    if kind not in ("synthesis", "question") or (kind == "question" and not q):
        raise HTTPException(422, "kind = synthesis | question (+ question text)")
    if kind == "synthesis" and not db.scalar(select(CompetitorItem.id).where(CompetitorItem.status == "done").limit(1)):
        raise HTTPException(422, "Сначала добавь и дождись разбора хотя бы одного примера")
    r = GrowthReport(kind=kind, question=q or None, status="pending")
    db.add(r)
    db.commit()
    tasks.growth_report_task(str(r.id))
    return report_out(r)


@router.post("/reports/{report_id}/apply")
def apply_report(report_id: uuid.UUID, body: dict[str, Any] = Body(default={})):
    """Write the proposed doc changes to disk (all, or body.paths). Old versions -> data/growth/history/."""
    try:
        done = growth.apply_changes(report_id, body.get("paths"))
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return {"applied": done, "at": datetime.now(timezone.utc)}


@router.get("/playbook")
def get_playbook():
    from ai.growth import PLAYBOOK, playbook_text
    return {"path": PLAYBOOK.relative_to(PLAYBOOK.parents[2]).as_posix(), "text": playbook_text()}
