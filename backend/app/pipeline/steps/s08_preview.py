"""Step 8: props.json -> Remotion stills (middle frame of every scene) -> contact sheet (Pillow).
Waits for approve_preview; scene comments + apply-comments produce a new storyboard version."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from app.db import session_scope
from app.media import engine, props as props_mod, sheet
from app.models import Project, Render
from app.pipeline.media_state import aligned_track, current_storyboard, image_paths
from app.pipeline.orchestrator import StepResult, job_log, register, set_progress
from app.schemas import errors as schema_errors
from app.storage import abs_data, next_version, project_dir, rel, write_json


def build_props(project_id: uuid.UUID, step: str, composition: str = "Explainer") -> tuple[dict[str, Any], uuid.UUID]:
    """Current storyboard + images + aligned voice -> props (and the storyboard id)."""
    with session_scope() as db:
        sb = current_storyboard(db, project_id)
        if sb is None:
            raise RuntimeError("No storyboard (step 6)")
        track = aligned_track(db, project_id)
        images = image_paths(db, project_id, sb.data)
        p = db.get(Project, project_id)
        sponsor = (p.sponsor_name or "Sponsor") if p.sponsored else None
        doc = props_mod.build(sb.data, track.words_json, images, abs_data(track.path),
                              composition=composition, sponsor=sponsor)
        for e in schema_errors("props", doc):
            job_log(db, project_id, step, f"props.schema: {e}", "warning")
        return doc, sb.id


def scene_times(words_doc: dict, sb: dict) -> list[tuple[float, float]]:
    w = words_doc["words"]
    starts = [w[s["start_word"]]["start"] for s in sb["scenes"]]
    return list(zip(starts, starts[1:] + [words_doc["duration"]]))


@register("preview")
def run(project_id: uuid.UUID) -> StepResult:
    doc, sb_id = build_props(project_id, "preview")
    folder = project_dir(project_id, "render")
    n = next_version(folder, "contact_sheet_v", ".png")
    props_path = folder / f"props_preview_v{n}.json"
    write_json(props_path, doc)
    missing = sheet.missing_glyphs(doc)
    with session_scope() as db:
        if missing:
            job_log(db, project_id, "preview", f"Font has no glyph for: {' '.join(missing)} (render will fail)", "error")
        job_log(db, project_id, "preview", f"Rendering {len(doc['scenes'])} stills ({doc['duration_frames']} frames)")

    total = len(doc["scenes"])
    shots = engine.stills(props_path, folder / f"stills_v{n}",
                          on_still=lambda k: set_progress(project_id, "preview", k / total) if k % 4 == 0 else None)
    if len(shots) != total:
        raise RuntimeError(f"Expected {total} stills, got {len(shots)}")
    tiles = []
    stills: dict[str, str] = {}
    for scene, (_f, png) in zip(doc["scenes"], shots):
        t0 = scene["from"] / 30
        tiles.append((scene["id"], png, f"{int(t0 // 60)}:{t0 % 60:04.1f}  {len(scene.get('overlays', []))} overlays"))
        stills[str(scene["id"])] = rel(Path(png))
    out = sheet.contact_sheet(tiles, folder / f"contact_sheet_v{n}.png")
    with session_scope() as db:
        db.add(Render(project_id=project_id, kind="preview", storyboard_id=sb_id, path=rel(out),
                      props_path=rel(props_path), duration=round(doc["duration_frames"] / 30, 2),
                      checks={"stills": stills, "glyphs_missing": missing}))
        job_log(db, project_id, "preview", f"Contact sheet {out.name}: {total} scenes")
    return StepResult.wait("approve_preview")
