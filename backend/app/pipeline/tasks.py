"""Huey queue (SQLite file under data/queue). One worker thread => one step at a time."""
from __future__ import annotations

import uuid

from huey import SqliteHuey, crontab

from app.config import get_settings

_queue_dir = get_settings().data_path / "queue"
_queue_dir.mkdir(parents=True, exist_ok=True)
huey = SqliteHuey("basqasha", filename=str(_queue_dir / "huey.sqlite3"))


@huey.task()
def run_step_task(project_id: str, step: str) -> None:
    from app.pipeline import orchestrator, steps  # noqa: F401 - registers handlers
    orchestrator.execute(uuid.UUID(project_id), step, orchestrator.HANDLERS[step])


@huey.task()
def operator_task(project_id: str, step: str, task: str) -> None:
    """Long operator actions (e.g. script approve re-checks originality). ``task`` may carry one
    argument after a colon, e.g. "regenerate_image:bg03"."""
    from app.pipeline import operator_actions, orchestrator
    name, _, arg = task.partition(":")
    fn = operator_actions.ACTIONS[name]
    orchestrator.execute(uuid.UUID(project_id), step, (lambda pid: fn(pid, arg)) if arg else fn)


@huey.periodic_task(crontab(hour="*/12", minute="7"))
def keep_alive() -> None:
    """Supabase free projects pause after ~1 week idle; a SELECT 1 twice a day keeps it awake."""
    from sqlalchemy import text

    from app.db import engine
    with engine.connect() as c:
        c.execute(text("select 1"))
