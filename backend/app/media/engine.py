"""Remotion engine scripts (engine/scripts/*.mjs) via subprocess: list args, no shell.
stdout carries JSON lines ({"progress":…}, {"still":…}, {"done":…}); stderr is the log."""
from __future__ import annotations

import json
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable

from app.config import get_settings
from app.media.props import asset_root

TIMEOUT_S = 60 * 60


class EngineError(RuntimeError):
    pass


def _node() -> str:
    b = get_settings().node_bin
    found = shutil.which(b) or (b if Path(b).is_file() else None)
    if not found:
        raise EngineError(f"node not found (NODE_BIN={b})")
    return found


def _run(script: str, args: list[str], on_line: Callable[[dict[str, Any]], None]) -> list[dict[str, Any]]:
    eng = get_settings().engine_path
    if not (eng / "node_modules").is_dir():
        raise EngineError("engine/node_modules missing: run `npm install` in engine/")
    cmd = [_node(), str(eng / "scripts" / script), *args, "--root", str(asset_root())]
    p = subprocess.Popen(cmd, cwd=eng, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                         encoding="utf-8", errors="replace")
    err: list[str] = []
    t = threading.Thread(target=lambda: err.extend(p.stderr), daemon=True)
    t.start()
    timer = threading.Timer(TIMEOUT_S, p.kill)
    timer.start()
    lines: list[dict[str, Any]] = []
    try:
        for raw in p.stdout:
            raw = raw.strip()
            if not raw.startswith("{"):
                continue
            try:
                obj = json.loads(raw)
            except ValueError:
                continue
            lines.append(obj)
            on_line(obj)
        p.wait()
    finally:
        timer.cancel()
        t.join(timeout=5)
    if p.returncode != 0:
        raise EngineError(f"{script} exited {p.returncode}: {''.join(err)[-3000:]}")
    return lines


def render(props_path: Path, out: Path, on_progress: Callable[[float], None]) -> None:
    _run("render.mjs", ["--props", str(props_path), "--out", str(out)],
         lambda o: on_progress(float(o["progress"])) if "progress" in o else None)


def stills(props_path: Path, out_dir: Path, on_still: Callable[[int], None] | None = None,
           scale: float = 0.5) -> list[tuple[int, Path]]:
    """Middle frame of every scene -> [(frame, png)] in scene order."""
    got: list[tuple[int, Path]] = []

    def line(o: dict[str, Any]) -> None:
        if "still" in o:
            got.append((int(o["frame"]), Path(o["still"])))
            if on_still:
                on_still(len(got))

    _run("stills.mjs", ["--props", str(props_path), "--frames", "mid", "--out", str(out_dir),
                        "--scale", str(scale)], line)
    return got
