"""Step 7: one background image per storyboard slot (Gemini + vision QA in backend/ai), or the
placeholder samples from library/style/samples (setting image_source = "samples" or the
use-samples endpoint) so the pipeline runs without image billing. A slot without a usable image
-> waiting_operator / manual_images (regenerate, edit prompt, upload own, or use samples)."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import update

from app import app_settings
from app.db import session_scope
from app.media import library
from app.models import ImageAsset, Storyboard
from app.pipeline import ai_bridge
from app.pipeline.media_state import current_storyboard, image_ok, selected_images
from app.pipeline.orchestrator import DONE, StepResult, job_log, register, set_progress
from app.providers.interfaces import CallContext
from app.storage import project_dir, rel

QUOTA_MARKERS = ("image model unavailable", "429", "RESOURCE_EXHAUSTED", "quota")


def _new_asset(db, project_id: uuid.UUID, slot: str, prompt: str, **kw: Any) -> ImageAsset:
    db.execute(update(ImageAsset).where(ImageAsset.project_id == project_id, ImageAsset.slot == slot)
               .values(selected=False))
    a = ImageAsset(project_id=project_id, slot=slot, prompt=prompt, selected=True, **kw)
    db.add(a)
    db.flush()
    return a


def _out_path(project_id: uuid.UUID, slot: str, ext: str = ".png") -> Path:
    folder = project_dir(project_id, "images")
    k = 1
    while any((folder / f"{slot}_a{k}{e}").exists() for e in (".png", ".jpg", ".jpeg", ".webp")):
        k += 1
    return folder / f"{slot}_a{k}{ext}"


def use_sample(db, project_id: uuid.UUID, slot: str, prompt: str, index: int) -> ImageAsset:
    samples = library.samples()
    if not samples:
        raise RuntimeError("library/style/samples is empty")
    src = samples[index % len(samples)]
    dst = _out_path(project_id, slot, src.suffix.lower())
    shutil.copyfile(src, dst)
    return _new_asset(db, project_id, slot, prompt, path=rel(dst), source="library",
                      license=f"placeholder:library/style/samples/{src.name}", attempts=0,
                      qa_status="manual_approved", qa_report={"notes": "placeholder sample (not for publishing)"})


def fill_samples(project_id: uuid.UUID, only_missing: bool = True) -> int:
    """Fill slots with library samples round-robin. Returns the number of slots filled."""
    with session_scope() as db:
        sb = current_storyboard(db, project_id)
        if sb is None:
            raise RuntimeError("No storyboard (step 6)")
        sel = selected_images(db, project_id)
        n = 0
        for i, bg in enumerate(sb.data["backgrounds"]):
            if only_missing and image_ok(sel.get(bg["id"])):
                continue
            use_sample(db, project_id, bg["id"], bg["prompt"], i)
            n += 1
        _write_files(db, sb.id, project_id)
        return n


def _write_files(db, storyboard_id: uuid.UUID, project_id: uuid.UUID) -> None:
    """storyboard.backgrounds[].file = selected image (in place; not a new version)."""
    sb = db.get(Storyboard, storyboard_id)
    sel = selected_images(db, project_id)
    data = dict(sb.data)
    data["backgrounds"] = [{**bg, **({"file": sel[bg["id"]].path.split("/", 2)[-1]} if image_ok(sel.get(bg["id"])) else {})}
                           for bg in data["backgrounds"]]
    sb.data = data


def _generate(project_id: uuid.UUID, ai, slot: str, prompt: str) -> tuple[str, str]:
    """One slot via the AI facade. Returns (qa_status, notes)."""
    out = _out_path(project_id, slot)
    r = ai.background_image(prompt, out, ctx=CallContext(project_id, "images"))
    status = {"ok": "passed"}.get(r.get("qa_status"), r.get("qa_status") or "needs_manual")
    path = r.get("path")
    with session_scope() as db:
        _new_asset(db, project_id, slot, prompt, path=rel(Path(path)) if path else None, source="generated",
                   attempts=int(r.get("attempts") or 0), qa_status=status if path else "needs_manual",
                   is_photoreal=bool(r.get("is_photoreal")), depicts_real_person=bool(r.get("depicts_real_person")),
                   qa_report={"notes": r.get("qa_notes"), "model": r.get("model")})
        job_log(db, project_id, "images", f"{slot}: {status} after {r.get('attempts')} attempt(s). {r.get('qa_notes') or ''}"[:1000],
                "info" if status == "passed" else "warning")
    return status, str(r.get("qa_notes") or "")


def set_prompt(db, project_id: uuid.UUID, slot: str, prompt: str) -> None:
    """«Изменить промпт»: the slot prompt lives in the current storyboard row (edited in place)."""
    sb = current_storyboard(db, project_id)
    data = dict(sb.data)
    data["backgrounds"] = [{**bg, "prompt": prompt} if bg["id"] == slot else bg for bg in data["backgrounds"]]
    sb.data = data


def process(project_id: uuid.UUID, only: str | None = None) -> StepResult:
    """Make every slot without a usable image for its current prompt (or just ``only``)."""
    with session_scope() as db:
        sb = current_storyboard(db, project_id)
        if sb is None:
            raise RuntimeError("No storyboard (step 6)")
        sb_id, backgrounds = sb.id, sb.data["backgrounds"]
        sel = selected_images(db, project_id)
        source = app_settings.load(db).get("image_source", "gemini")

    if only:
        todo = [bg for bg in backgrounds if bg["id"] == only]
        if not todo:
            raise RuntimeError(f"Slot {only} is not in the current storyboard")
    else:
        todo = [bg for bg in backgrounds
                if not (image_ok(sel.get(bg["id"])) and sel[bg["id"]].prompt == bg["prompt"])]
    with session_scope() as db:
        job_log(db, project_id, "images", f"{len(todo)} of {len(backgrounds)} slot(s) to make "
                f"({'library samples' if source == 'samples' and not only else 'Gemini'})")

    ai = None
    blocked: str | None = None
    for k, bg in enumerate(todo):
        slot = bg["id"]
        if source == "samples" and not only:
            with session_scope() as db:
                use_sample(db, project_id, slot, bg["prompt"], backgrounds.index(bg))
        elif blocked:
            with session_scope() as db:
                _new_asset(db, project_id, slot, bg["prompt"], path=None, attempts=0, qa_status="needs_manual",
                           qa_report={"notes": f"skipped: {blocked}"})
        else:
            ai = ai or ai_bridge.build(project_id)
            status, notes = _generate(project_id, ai, slot, bg["prompt"])
            if status == "needs_manual" and any(m.lower() in notes.lower() for m in QUOTA_MARKERS):
                blocked = "image generation unavailable (quota / billing) — upload images or use samples"
        set_progress(project_id, "images", (k + 1) / max(1, len(todo)))

    with session_scope() as db:
        _write_files(db, sb_id, project_id)
        sel = selected_images(db, project_id)
        bad = [bg["id"] for bg in backgrounds if not image_ok(sel.get(bg["id"]))]
        if bad:
            job_log(db, project_id, "images", f"Need manual images: {', '.join(bad)}", "warning")
            return StepResult.wait("manual_images")
    return DONE


@register("images")
def run(project_id: uuid.UUID) -> StepResult:
    return process(project_id)


def regenerate(project_id: uuid.UUID, slot: str) -> StepResult:
    """Operator action «Перегенерировать» (always via Gemini, even when image_source = samples)."""
    return process(project_id, only=slot)


def save_upload(project_id: uuid.UUID, slot: str, data: bytes, filename: str, *, license: str,
                is_photoreal: bool, depicts_real_person: bool) -> ImageAsset:
    """«Загрузить свою»: becomes the selected asset with qa_status manual_approved."""
    from PIL import Image

    with session_scope() as db:
        sb = current_storyboard(db, project_id)
        bg = next((b for b in (sb.data["backgrounds"] if sb else []) if b["id"] == slot), None)
        if bg is None:
            raise ValueError(f"Slot {slot} is not in the current storyboard")
        out = _out_path(project_id, slot)
        tmp = out.with_suffix(".upload")
        tmp.write_bytes(data)
        try:
            with Image.open(tmp) as im:
                im.convert("RGB").save(out)
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"Not an image ({filename}): {e}") from e
        finally:
            tmp.unlink(missing_ok=True)
        a = _new_asset(db, project_id, slot, bg["prompt"], path=rel(out), source="manual_upload", license=license,
                       is_photoreal=is_photoreal, depicts_real_person=depicts_real_person, attempts=0,
                       qa_status="manual_approved", qa_report={"notes": f"uploaded {filename}"})
        _write_files(db, sb.id, project_id)
        job_log(db, project_id, "images", f"{slot}: own image uploaded ({filename})")
        return a


def all_ok(project_id: uuid.UUID) -> bool:
    with session_scope() as db:
        sb = current_storyboard(db, project_id)
        sel = selected_images(db, project_id)
        return sb is not None and all(image_ok(sel.get(bg["id"])) for bg in sb.data["backgrounds"])

