"""JSON Schema validation against /schemas/*.schema.json."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator

from app.config import REPO_ROOT


@lru_cache
def _schema(name: str) -> dict[str, Any]:
    return json.loads((REPO_ROOT / "schemas" / f"{name}.schema.json").read_text(encoding="utf-8"))


def errors(name: str, doc: Any, defn: str | None = None) -> list[str]:
    """Error strings for ``doc`` against schema ``name`` (or its ``$defs/defn``)."""
    schema = _schema(name)
    if defn:
        schema = {**schema["$defs"][defn], "$defs": schema["$defs"]}
    v = Draft202012Validator(schema)
    return [f"{'/'.join(map(str, e.absolute_path)) or '$'}: {e.message}" for e in v.iter_errors(doc)][:20]


def validate(name: str, doc: Any, defn: str | None = None) -> None:
    errs = errors(name, doc, defn)
    if errs:
        raise ValueError(f"{name} schema validation failed: " + "; ".join(errs))
