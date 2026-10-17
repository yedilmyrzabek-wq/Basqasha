"""library/ manifests: poses.json (character poses) and sfx.json (sound effects + music)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import get_settings


def _read(rel: str) -> dict[str, Any]:
    f = get_settings().library_path / rel
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def poses() -> list[dict[str, Any]]:
    """[{name, file, tags, width, height}] — file relative to library/poses/."""
    return [p for p in _read("poses/poses.json").get("poses", []) if p.get("active", True)]


def sfx() -> dict[str, str]:
    """name -> file relative to library/sfx/."""
    return {s["name"]: s["file"] for s in _read("sfx/sfx.json").get("sfx", [])}


def music() -> list[dict[str, Any]]:
    return _read("sfx/sfx.json").get("music", [])


def samples() -> list[Path]:
    """Placeholder backgrounds (library/style/samples) for running without image generation."""
    d = get_settings().library_path / "style" / "samples"
    return sorted(p for p in d.glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
