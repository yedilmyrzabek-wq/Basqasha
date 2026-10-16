"""Huey worker entry point: `uv run python -m app.worker` (portable; no huey_consumer script)."""
from __future__ import annotations

import logging

from huey.consumer import Consumer

from app.config import get_settings
from app.db import session_scope
from app.models import ProjectStep
from app.pipeline import orchestrator, steps  # noqa: F401 - registers handlers
from app.pipeline.tasks import huey


def _recover() -> None:
    """Steps left 'running' by a crashed worker with nothing queued -> failed (retry is one click)."""
    if len(huey) > 0:
        return
    with session_scope() as db:
        for ps in db.query(ProjectStep).filter(ProjectStep.status == "running"):
            orchestrator.set_state(db, ps.project_id, ps.step, "failed", error="Interrupted (worker restarted)")


def main() -> None:
    logging.basicConfig(level=get_settings().log_level,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    _recover()
    Consumer(huey, workers=1, worker_type="thread", periodic=True).run()


if __name__ == "__main__":
    main()
