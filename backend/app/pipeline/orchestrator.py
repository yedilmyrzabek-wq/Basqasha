"""Step state machine (ARCHITECTURE §2).

pending -> running -> done | waiting_operator | failed;  waiting_operator -> running/done after an
operator action; failed -> running (retry); done -> stale when upstream output changes.
A step runs only when every earlier step is done; on done the next step is queued automatically.
"""
from __future__ import annotations

import logging
import traceback
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import cancel
from app.db import session_scope
from app.models import STEP_KEYS, JobLog, Project, ProjectStep
from app.providers.interfaces import BudgetExceeded, OperatorActionRequired

log = logging.getLogger(__name__)

INVALIDATABLE = ("done", "waiting_operator", "failed")
# storyboard / image changes (and the preview / render re-runs they cause) do not touch metadata
KEEP_METADATA_FROM = ("storyboard", "images", "preview", "render")


class StepConflict(Exception):
    """Not allowed in the current state (HTTP 409)."""


@dataclass(frozen=True)
class StepResult:
    status: str = "done"                 # done | waiting_operator
    wait_reason: str | None = None

    @staticmethod
    def wait(reason: str) -> "StepResult":
        return StepResult("waiting_operator", reason)


DONE = StepResult()
Handler = Callable[[uuid.UUID], StepResult]


def now() -> datetime:
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ rows
def ensure_steps(db: Session, project_id: uuid.UUID) -> None:
    have = set(db.scalars(select(ProjectStep.step).where(ProjectStep.project_id == project_id)))
    for k in STEP_KEYS:
        if k not in have:
            db.add(ProjectStep(project_id=project_id, step=k, status="pending", attempts=0))
    db.flush()


def get_step(db: Session, project_id: uuid.UUID, step: str) -> ProjectStep:
    ps = db.get(ProjectStep, (project_id, step))
    if ps is None:
        ensure_steps(db, project_id)
        ps = db.get(ProjectStep, (project_id, step))
    return ps


def steps_of(db: Session, project_id: uuid.UUID) -> list[ProjectStep]:
    rows = {r.step: r for r in db.scalars(select(ProjectStep).where(ProjectStep.project_id == project_id))}
    return [rows[k] for k in STEP_KEYS if k in rows]


def job_log(db: Session, project_id: uuid.UUID | None, step: str | None, message: str,
            level: str = "info", data: dict[str, Any] | None = None) -> None:
    db.add(JobLog(project_id=project_id, step=step, level=level, message=message[:4000], data=data))
    getattr(log, level if level != "warning" else "warning")("[%s/%s] %s", project_id, step, message[:300])


def refresh_project_status(db: Session, project_id: uuid.UUID) -> None:
    p = db.get(Project, project_id)
    if p is None or p.status in ("archived", "published"):
        return
    st = {s.step: s.status for s in steps_of(db, project_id)}
    if "failed" in st.values():
        p.status = "failed"
    elif "waiting_operator" in st.values():
        p.status = "waiting_operator"
    elif st.get("render") == "done":
        p.status = "ready"
    else:
        p.status = "active"


def current_step(steps: list[ProjectStep]) -> str:
    for s in steps:
        if s.status != "done":
            return s.step
    return STEP_KEYS[-1]


def set_state(db: Session, project_id: uuid.UUID, step: str, status: str, *,
              wait_reason: str | None = None, error: str | None = None) -> ProjectStep:
    ps = get_step(db, project_id, step)
    ps.status, ps.wait_reason, ps.error = status, wait_reason, error
    if status in ("done", "failed", "waiting_operator"):
        ps.finished_at = now()
    if status in ("done", "waiting_operator"):
        ps.progress = None
    db.flush()
    refresh_project_status(db, project_id)
    return ps


def set_progress(project_id: uuid.UUID, step: str, progress: float) -> None:
    """Worker-side progress (0..1) for long steps (images, stills, render)."""
    with session_scope() as db:
        get_step(db, project_id, step).progress = round(min(max(progress, 0.0), 1.0), 3)


def invalidate_after(db: Session, project_id: uuid.UUID, step: str) -> list[str]:
    """Mark later done/waiting/failed steps stale. Returns the keys changed."""
    i = STEP_KEYS.index(step)
    changed = []
    for ps in steps_of(db, project_id):
        j = STEP_KEYS.index(ps.step)
        if j <= i or ps.status not in INVALIDATABLE:
            continue
        if step in KEEP_METADATA_FROM and ps.step == "metadata":
            continue
        ps.status, ps.wait_reason = "stale", None
        changed.append(ps.step)
    if changed:
        job_log(db, project_id, step, f"Downstream steps marked stale: {', '.join(changed)}")
    db.flush()
    refresh_project_status(db, project_id)
    return changed


def check_can_run(db: Session, project_id: uuid.UUID, step: str) -> None:
    for ps in steps_of(db, project_id):
        if ps.step == step:
            break
        if ps.status != "done":
            raise StepConflict(f"Step '{ps.step}' must be done before '{step}' (it is {ps.status})")


# ------------------------------------------------------------------ queueing
def request_run(db: Session, project_id: uuid.UUID, step: str, *, task: str = "run",
                check: bool = True) -> ProjectStep:
    """Validate, mark running, invalidate downstream, COMMIT, then enqueue the Huey task."""
    from app.pipeline import tasks  # local import: tasks imports this module

    if step not in HANDLERS and task == "run":
        raise StepConflict(f"Step '{step}' is not implemented yet")
    if check:
        check_can_run(db, project_id, step)
    ps = get_step(db, project_id, step)
    if ps.status == "running":
        raise StepConflict(f"Step '{step}' is already running")
    ps.status, ps.wait_reason, ps.error, ps.progress = "running", None, None, None
    cancel.clear(project_id)  # a new run starts fresh even if an old «Остановить» flag is left
    invalidate_after(db, project_id, step)
    job_log(db, project_id, step, "Queued" if task == "run" else f"Queued: {task}")
    refresh_project_status(db, project_id)
    db.commit()  # the worker must see this state before it starts
    if task == "run":
        tasks.run_step_task(str(project_id), step)
    else:
        tasks.operator_task(str(project_id), step, task)
    return ps


def queue_next(project_id: uuid.UUID, step: str) -> None:
    i = STEP_KEYS.index(step)
    if i + 1 >= len(STEP_KEYS):
        return
    nxt = STEP_KEYS[i + 1]
    if nxt not in HANDLERS:
        return
    with session_scope() as db:
        ps = get_step(db, project_id, nxt)
        if ps.status in ("pending", "stale", "failed"):
            request_run(db, project_id, nxt)


# ------------------------------------------------------------------ execution (worker side)
def execute(project_id: uuid.UUID, step: str, fn: Handler) -> None:
    with cancel.bound(project_id):
        _execute(project_id, step, fn)


def _stopped(project_id: uuid.UUID, step: str) -> None:
    cancel.clear(project_id)
    with session_scope() as db:
        set_state(db, project_id, step, "failed", error=cancel.STOPPED)
        job_log(db, project_id, step, "Stopped by the operator", "warning")


def _execute(project_id: uuid.UUID, step: str, fn: Handler) -> None:
    with session_scope() as db:
        if db.get(Project, project_id) is None:
            log.info("Project %s was deleted; skipping queued step %s", project_id, step)
            return
    if cancel.requested(project_id):  # stopped while it was still waiting in the queue
        _stopped(project_id, step)
        return
    with session_scope() as db:
        ps = get_step(db, project_id, step)
        ps.status, ps.started_at, ps.attempts = "running", now(), (ps.attempts or 0) + 1
        ps.error = ps.wait_reason = None
        refresh_project_status(db, project_id)
        job_log(db, project_id, step, f"Started (attempt {ps.attempts})")
    try:
        result = fn(project_id)
    except cancel.Cancelled:
        _stopped(project_id, step)
        return
    except BudgetExceeded as e:
        with session_scope() as db:
            set_state(db, project_id, step, "waiting_operator", wait_reason="budget_exceeded", error=str(e))
            job_log(db, project_id, step, f"Budget exceeded: {e}", "warning")
        return
    except OperatorActionRequired as e:
        with session_scope() as db:
            set_state(db, project_id, step, "waiting_operator", error=str(e))
            job_log(db, project_id, step, f"Operator action required: {e}", "warning")
        return
    except Exception as e:  # noqa: BLE001 - every failure becomes a failed step with a log
        with session_scope() as db:
            set_state(db, project_id, step, "failed", error=f"{type(e).__name__}: {e}"[:2000])
            job_log(db, project_id, step, f"Failed: {type(e).__name__}: {e}", "error",
                    {"traceback": traceback.format_exc()[-6000:]})
        return
    # finished just as «Остановить» was pressed: keep the result, but do not start the next step
    stop = cancel.requested(project_id)
    cancel.clear(project_id)
    finish(project_id, step, result, queue=not stop)


def finish(project_id: uuid.UUID, step: str, result: StepResult, queue: bool = True) -> None:
    with session_scope() as db:
        set_state(db, project_id, step, result.status, wait_reason=result.wait_reason)
        msg = "Done" if result.status == "done" else f"Waiting for operator: {result.wait_reason}"
        job_log(db, project_id, step, msg)
    if result.status == "done" and queue:
        queue_next(project_id, step)


def complete_by_operator(db: Session, project_id: uuid.UUID, step: str, message: str) -> None:
    """Operator action finished a waiting step (choose angle, manual transcript ...)."""
    set_state(db, project_id, step, "done")
    invalidate_after(db, project_id, step)
    job_log(db, project_id, step, message)
    db.commit()
    queue_next(project_id, step)


HANDLERS: dict[str, Handler] = {}


def register(step: str):
    def deco(fn: Handler) -> Handler:
        HANDLERS[step] = fn
        return fn
    return deco
