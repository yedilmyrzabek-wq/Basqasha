"""Huey worker entry point: `uv run python -m app.worker` (portable; no huey_consumer script)."""
from __future__ import annotations

import logging

from huey.consumer import Consumer

from app.config import get_settings
from app.db import session_scope
from app.models import CompetitorItem, GrowthReport, ProjectStep
from app.pipeline import orchestrator, steps  # noqa: F401 - registers handlers
from app.pipeline.tasks import huey


def _recover() -> None:
    """Steps left 'running' by a crashed worker with nothing queued -> failed (retry is one click)."""
    if len(huey) > 0:
        return
    with session_scope() as db:
        for ps in db.query(ProjectStep).filter(ProjectStep.status == "running"):
            orchestrator.set_state(db, ps.project_id, ps.step, "failed", error="Interrupted (worker restarted)")
        for model in (CompetitorItem, GrowthReport):  # «Конкуренты»: same, retry is one click
            for row in db.query(model).filter(model.status.in_(("pending", "running"))):
                row.status, row.error = "failed", "Interrupted (worker restarted)"


def main() -> None:
    logging.basicConfig(level=get_settings().log_level,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    _recover()
    # 2 threads: a long render or Opus call does not block the other queue item. Steps of one project
    # still run one after another (the next step is queued only when the previous one finishes).
    Consumer(huey, workers=2, worker_type="thread", periodic=True).run()


if __name__ == "__main__":
    main()
