"""Step 11 «Рекомендации»: what was missing for this video (poses / costumes of the mascot, sounds,
music, backgrounds…) and how to add it. Output: data/projects/{id}/recommendations/recommendations.json
(items keep a «done» flag the operator ticks on the page)."""
from __future__ import annotations

import json
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.db import session_scope
from app.media import library
from app.models import JobLog, Project, Render
from app.pipeline import ai_bridge
from app.pipeline.context import load_context
from app.pipeline.media_state import aligned_track, current_storyboard, selected_images
from app.pipeline.orchestrator import DONE, StepResult, job_log, register
from app.providers.interfaces import CallContext
from app.storage import project_dir

SCENE_TEXT_CHARS = 220


def path(project_id: uuid.UUID) -> Path:
    return project_dir(project_id, "recommendations") / "recommendations.json"


def load(project_id: uuid.UUID) -> dict[str, Any] | None:
    f = path(project_id)
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None


def save(project_id: uuid.UUID, doc: dict[str, Any]) -> None:
    path(project_id).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")


def _context(project_id: uuid.UUID) -> dict[str, Any]:
    ctx = load_context(project_id)
    with session_scope() as db:
        p = db.get(Project, project_id)
        sb = current_storyboard(db, project_id)
        track = aligned_track(db, project_id)
        images = selected_images(db, project_id)
        warnings = [f"[{l.step}] {l.message[:300]}" for l in db.scalars(
            select(JobLog).where(JobLog.project_id == project_id, JobLog.level.in_(("warning", "error")))
            .order_by(JobLog.id.desc()).limit(30))]
        render = db.scalar(select(Render).where(Render.project_id == project_id, Render.kind == "full")
                           .order_by(Render.created_at.desc()).limit(1))
        words = track.words_json["words"] if track else []
        sb_doc = sb.data if sb else {"scenes": [], "backgrounds": []}
        img_rows = {slot: {"qa": a.qa_status, "source": a.source, "notes": ((a.qa_report or {}).get("notes") or "")[:200]}
                    for slot, a in images.items()}
        title, target, duration = p.title, p.target_seconds, float(track.duration) if track and track.duration else None
        render_checks = render.checks if render else None

    bg_prompt = {b["id"]: b["prompt"] for b in sb_doc.get("backgrounds", [])}
    scenes, usage = [], Counter()
    for s in sb_doc.get("scenes", []):
        ch = s.get("character") or {}
        poses = [ch.get("pose")] + [pc["pose"] for pc in ch.get("pose_changes", []) or []]
        usage.update(x for x in poses if x)
        text = " ".join(w["w"] for w in words[s["start_word"]:s["end_word"] + 1])
        scenes.append({"id": s["id"], "text": text[:SCENE_TEXT_CHARS], "poses": [x for x in poses if x],
                       "background": bg_prompt.get(s["background"], "")[:160],
                       "sfx": [x["file"] for x in s.get("sfx", []) or []]})
    script = ctx.approved_script or {}
    return {
        "video": {"title": title, "target_seconds": target, "voice_seconds": duration,
                  "script_words": script.get("word_count"), "target_words": script.get("target_words")},
        "scenes": scenes,
        "pose_usage": usage.most_common(),
        "images": {"problems": {k: v for k, v in img_rows.items() if v["qa"] not in ("passed",)},
                   "total": len(img_rows)},
        "library": {
            "poses": [{"name": x["name"], "tags": x.get("tags", [])} for x in library.poses()],
            "expressions": [x["name"] for x in library.expressions()],
            "sounds": sorted(library.sfx()), "music": [m.get("name") for m in library.music()],
            "sounds_are_placeholders": library.placeholder_sounds(),
            "notes": "Mascot = stickman in a white kalpak, turquoise scarf, navy hoodie, beige pants. "
                     "Animated video clips of the mascot are not used yet (only still poses).",
            "where_to_add": {"pose sheets (new poses / outfits)": "incoming/character/ (Claude cuts them into library/poses/)",
                             "sound effects": "library/sfx/ + an entry in library/sfx/sfx.json (or drop into incoming/sfx/)",
                             "music": "library/sfx/music/ + library/sfx/sfx.json «music» (or incoming/music/)",
                             "style samples": "library/style/samples/",
                             "competitor examples": "page «Анализ конкурентов»"},
        },
        "warnings_in_logs": warnings,
        "render_checks": render_checks,
        "character_block": library.character_block(),
    }


@register("recommendations")
def run(project_id: uuid.UUID) -> StepResult:
    context = _context(project_id)
    ai = ai_bridge.build(project_id)
    doc = ai.recommendations(context, ctx=CallContext(project_id, "recommendations"))
    save(project_id, doc)
    with session_scope() as db:
        job_log(db, project_id, "recommendations", f"{len(doc['items'])} recommendations")
    return DONE
