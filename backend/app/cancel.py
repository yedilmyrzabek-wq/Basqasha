"""«Остановить»: stop the running step of a project.

The API drops a flag file (data/projects/{id}/.stop). The worker sees it at the next checkpoint:
after every AI call (cost ledger) and every 0.5 s while a child process runs (Claude CLI, Remotion,
ffmpeg, yt-dlp) — the process tree is killed and the step ends as failed "Остановлено".
The project of the current worker thread is bound by the orchestrator, so deep code needs no ids.
"""
from __future__ import annotations

import os
import subprocess
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import get_settings

STOPPED = "Остановлено вами — нажмите «Повторить», чтобы запустить шаг заново"
_local = threading.local()


class Cancelled(BaseException):
    """BaseException (like KeyboardInterrupt) so retry loops with `except Exception` do not swallow it."""


def _flag(project_id: uuid.UUID) -> Path:
    return get_settings().data_path / "projects" / str(project_id) / ".stop"


def request(project_id: uuid.UUID) -> None:
    f = _flag(project_id)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.touch()


def clear(project_id: uuid.UUID) -> None:
    _flag(project_id).unlink(missing_ok=True)


def current() -> uuid.UUID | None:
    return getattr(_local, "project_id", None)


def requested(project_id: uuid.UUID | None = None) -> bool:
    pid = project_id or current()
    return pid is not None and _flag(pid).exists()


@contextmanager
def bound(project_id: uuid.UUID) -> Iterator[None]:
    """Worker thread works on this project until the block ends."""
    prev = current()
    _local.project_id = project_id
    try:
        yield
    finally:
        _local.project_id = prev


def check() -> None:
    if requested():
        raise Cancelled(STOPPED)


def kill_tree(p: subprocess.Popen) -> None:
    """Kill a child and its children (node -> Chrome, yt-dlp -> node)."""
    if p.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(p.pid)], capture_output=True)
    else:
        p.kill()
    try:
        p.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def run(cmd: list[str], *, input: str | None = None, timeout: float | None = None,
        **kw) -> subprocess.CompletedProcess:
    """subprocess.run(capture_output=True, text=True) that stops on «Остановить»."""
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         encoding=kw.pop("encoding", "utf-8"), errors=kw.pop("errors", "replace"), **kw)
    pid = current()
    deadline = time.monotonic() + timeout if timeout else None
    data = input
    while True:
        try:
            out, err = p.communicate(data, timeout=0.5)
            break
        except subprocess.TimeoutExpired:
            data = None  # stdin is sent once; a retry keeps the output already read
            if requested(pid):
                kill_tree(p)
                raise Cancelled(STOPPED) from None
            if deadline and time.monotonic() > deadline:
                kill_tree(p)
                raise subprocess.TimeoutExpired(cmd, timeout) from None
    return subprocess.CompletedProcess(cmd, p.returncode, out, err)


def watch(p: subprocess.Popen) -> threading.Event:
    """For a Popen read line by line elsewhere: kill it when a stop is requested. Set the returned
    event when the process is done."""
    pid, done = current(), threading.Event()

    def loop() -> None:
        while not done.wait(0.5):
            if requested(pid):
                kill_tree(p)
                return
    threading.Thread(target=loop, daemon=True).start()
    return done
