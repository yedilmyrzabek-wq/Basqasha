"""Load versioned prompts from /prompts/*.md and fill {{placeholders}}."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_FM = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)
_VAR = re.compile(r"\{\{(\w+)\}\}")

LANGUAGE_NAMES = {"kk": "Kazakh", "ru": "Russian", "en": "English"}


@dataclass(frozen=True)
class Prompt:
    id: str
    version: str
    meta: dict[str, str]
    body: str

    @property
    def tag(self) -> str:
        return f"{self.id}@v{self.version}"

    def render(self, **values: object) -> str:
        def sub(m: re.Match[str]) -> str:
            key = m.group(1)
            if key == "playbook" and key not in values:  # growth playbook, read fresh every time
                from ai.growth import playbook_for_prompts
                return playbook_for_prompts()
            if key not in values:
                raise KeyError(f"prompt {self.id}: missing value for {{{{{key}}}}}")
            v = values[key]
            return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, indent=1)
        return _VAR.sub(sub, self.body)


def load_prompt(name: str) -> Prompt:
    """Cached per file version: editing a prompt .md takes effect without restarting the worker."""
    f = PROMPTS_DIR / f"{name}.md"
    return _load(f, f.stat().st_mtime_ns)


@lru_cache(maxsize=128)
def _load(f: Path, _mtime: int) -> Prompt:
    name = f.stem
    raw = f.read_text(encoding="utf-8")
    m = _FM.match(raw)
    meta: dict[str, str] = {}
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        raw = raw[m.end():]
    return Prompt(id=meta.get("id", name), version=meta.get("version", "0"), meta=meta, body=raw)


def language_rules(language: str) -> str:
    path = PROMPTS_DIR / f"lang_{language}.md"
    return load_prompt(f"lang_{language}").body.strip() if path.exists() else ""


@lru_cache
def kk_abbrev() -> dict[str, str]:
    data = json.loads((PROMPTS_DIR / "kk_abbrev.json").read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}
