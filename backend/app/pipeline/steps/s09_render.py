"""Step 9: full Remotion render -> ffmpeg master (-14 LUFS / -1 dBTP, video copied) -> checks:
duration = voice ± 0.5 s, glyph coverage."""
from __future__ import annotations

import time
import uuid

from app.db import session_scope
from app.media import engine, ffmpeg, sheet
from app.models import Render
from app.pipeline.media_state import aligned_track
from app.pipeline.orchestrator import DONE, StepResult, job_log, register, set_progress
from app.pipeline.steps.s08_preview import build_props
from app.storage import next_version, project_dir, rel, write_json

TOLERANCE_S = 0.5


@register("render")
def run(project_id: uuid.UUID) -> StepResult:
    doc, sb_id = build_props(project_id, "render")
    missing = sheet.missing_glyphs(doc)
    if missing:
        raise RuntimeError(f"Engine fonts have no glyph for: {' '.join(missing)}")
    with session_scope() as db:
        voice_s = float(aligned_track(db, project_id).duration)
    folder = project_dir(project_id, "render")
    n = next_version(folder, "final_v", ".mp4")
    props_path = folder / f"props_full_v{n}.json"
    write_json(props_path, doc)
    raw, final = folder / f"raw_v{n}.mp4", folder / f"final_v{n}.mp4"
    with session_scope() as db:
        job_log(db, project_id, "render", f"Rendering {doc['duration_frames']} frames -> {final.name}")

    last = {"t": 0.0}

    def progress(p: float) -> None:
        if time.monotonic() - last["t"] > 3 or p >= 1:   # ~1 DB write per 3 s
            last["t"] = time.monotonic()
            set_progress(project_id, "render", p * 0.95)

    t0 = time.monotonic()
    engine.render(props_path, raw, progress)
    render_s = time.monotonic() - t0
    loud = ffmpeg.master_video(raw, final)
    raw.unlink(missing_ok=True)
    dur = ffmpeg.duration(final)
    lufs = ffmpeg.loudness(final)
    ok = abs(dur - voice_s) <= TOLERANCE_S
    checks = {"duration_ok": ok, "duration": round(dur, 3), "voice_duration": round(voice_s, 3),
              "lufs": lufs, "lufs_before_master": float(loud["input_i"]), "render_seconds": round(render_s, 1),
              "glyphs_missing": missing}
    with session_scope() as db:
        db.add(Render(project_id=project_id, kind="full", storyboard_id=sb_id, path=rel(final),
                      props_path=rel(props_path), duration=round(dur, 3), checks=checks))
        job_log(db, project_id, "render", f"{final.name}: {dur:.2f} s (voice {voice_s:.2f} s), {lufs} LUFS, "
                f"rendered in {render_s:.0f} s", "info" if ok else "error", checks)
    if not ok:
        raise RuntimeError(f"Duration {dur:.2f} s differs from the voice {voice_s:.2f} s by more than {TOLERANCE_S} s")
    return DONE
