"""Local file storage under DATA_DIR. The DB stores POSIX paths relative to DATA_DIR."""
from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from app.config import get_settings


def project_dir(project_id: uuid.UUID | str, sub: str = "") -> Path:
    p = get_settings().data_path / "projects" / str(project_id)
    if sub:
        p = p / sub
    p.mkdir(parents=True, exist_ok=True)
    return p


def rel(path: Path) -> str:
    """Absolute path under DATA_DIR -> POSIX relative path for the DB."""
    return path.resolve().relative_to(get_settings().data_path).as_posix()


def abs_data(relpath: str) -> Path:
    return get_settings().data_path / relpath


def file_url(relpath: str | None, root: str = "data") -> str | None:
    if not relpath:
        return None
    return f"{get_settings().asset_base_url.rstrip('/')}/files/{root}/{relpath}"


def write_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return rel(path)


def write_json(path: Path, data: Any) -> str:
    return write_text(path, json.dumps(data, ensure_ascii=False, indent=1, default=str))


def next_version(folder: Path, prefix: str, suffix: str) -> int:
    """Next free n for files named {prefix}{n}{suffix} (old versions are never deleted)."""
    n = 1
    while (folder / f"{prefix}{n}{suffix}").exists():
        n += 1
    return n
