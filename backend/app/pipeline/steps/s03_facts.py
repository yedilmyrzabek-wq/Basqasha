"""Step 3: facts with sources (Google Search grounding) for the brief + chosen angle."""
from __future__ import annotations

import uuid

from sqlalchemy import delete

from app.db import session_scope
from app.models import Fact
from app.pipeline import ai_bridge
from app.pipeline.context import load_context
from app.pipeline.orchestrator import DONE, StepResult, job_log, register
from app.schemas import validate
from app.storage import next_version, project_dir, write_json


def fact_row(project_id: uuid.UUID, f: dict, idx: int, edited: bool = False) -> Fact:
    sources = f.get("sources") or []
    return Fact(project_id=project_id, idx=idx, claim=f["claim"], value=f.get("value"),
                source_url=(sources[0]["url"] if sources else None), sources=sources,
                status=f.get("status", "unverified"), on_screen=bool(f.get("on_screen", False)),
                edited_by_operator=edited)


def fact_idx(fact_id: str | None, fallback: int) -> int:
    try:
        return int(str(fact_id)[1:])
    except (TypeError, ValueError):
        return fallback


@register("facts")
def run(project_id: uuid.UUID) -> StepResult:
    ctx = load_context(project_id)
    if ctx.brief is None or ctx.angle is None:
        raise RuntimeError("Brief or chosen angle missing (step 2)")
    doc, method = ai_bridge.research_facts(project_id, ctx.brief, ctx.angle, ctx.language)
    validate("facts", doc)

    with session_scope() as db:
        folder = project_dir(project_id, "facts")
        rel = write_json(folder / f"facts_v{next_version(folder, 'facts_v', '.json')}.json", doc)
        db.execute(delete(Fact).where(Fact.project_id == project_id))
        for i, f in enumerate(doc["facts"], start=1):
            db.add(fact_row(project_id, f, fact_idx(f.get("id"), i)))
        verified = sum(1 for f in doc["facts"] if f["status"] == "verified")
        job_log(db, project_id, "facts", f"{len(doc['facts'])} facts ({verified} verified, {method}) -> {rel}")
    return DONE
