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


def placeholder_sounds() -> bool:
    """sfx.json still holds the placeholder sounds from the old example."""
    return bool(_read("sfx/sfx.json").get("placeholder"))


def expressions() -> list[dict[str, Any]]:
    return _read("character/expressions/expressions.json").get("expressions", [])


def character_block() -> str:
    """The shared character description from library/character/PROMPTS.md (first code block after
    «Общий блок»), so generated prompts keep our kalpak stickman."""
    f = get_settings().library_path / "character" / "PROMPTS.md"
    try:
        return f.read_text(encoding="utf-8").split("Общий блок", 1)[1].split("```", 2)[1].strip()
    except (OSError, IndexError):
        return ""
