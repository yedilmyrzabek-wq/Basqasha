"""Pydantic models for LLM structured output (google-genai response_schema).

They mirror /schemas/*.schema.json but stay loose (no regex/length constraints, which the
Gemini schema subset handles poorly). Final documents are assembled in code and validated
against the JSON Schemas with ``validate_doc``.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Mapping

import jsonschema
from pydantic import BaseModel

SCHEMAS_DIR = Path(__file__).resolve().parents[2] / "schemas"

HookType = Literal["question", "number", "paradox", "scene", "myth"]
Category = Literal["H", "W", "E", "G", "S", "F", "Sp", "P", "M"]


# ---------------------------------------------------------------- step 2
class KeyConcept(BaseModel):
    term: str
    gloss: str


class BriefOut(BaseModel):
    topic: str
    core_question: str
    structure_idea: list[str]
    key_concepts: list[KeyConcept]
    category: Category
    risk: int
    sensitive_topics: list[str]
    operator_summary: str


class AngleOut(BaseModel):
    title: str
    pitch: str
    why_it_works: str
    hook_words: list[str]
    suggested_hook_type: HookType
    k: int
    v: int
    f: int
    r: int


class IdeaOut(BaseModel):
    brief: BriefOut
    angles: list[AngleOut]


# ---------------------------------------------------------------- step 3
class SourceOut(BaseModel):
    url: str
    title: str
    is_primary: bool


class FactOut(BaseModel):
    claim: str
    value: str | None
    status: Literal["verified", "unverified", "conflicting"]
    sources: list[SourceOut]
    note: str | None


class FactsOut(BaseModel):
    facts: list[FactOut]


class Evidence(BaseModel):
    doc_id: str
    quote: str


class DocFactOut(BaseModel):
    claim: str
    value: str | None
    evidence: list[Evidence]
    disputed: bool
    note: str | None


class DocFactsOut(BaseModel):
    facts: list[DocFactOut]


# ---------------------------------------------------------------- step 4
class BeatOut(BaseModel):
    beat: str
    text: str
    fact_ids: list[str]


class ScriptOut(BaseModel):
    title: str
    hook_type: HookType
    beats: list[BeatOut]


class RewriteItem(BaseModel):
    index: int
    text: str


class RewriteOut(BaseModel):
    items: list[RewriteItem]


class JudgeItem(BaseModel):
    index: int
    copied: bool
    reason: str


class JudgeOut(BaseModel):
    items: list[JudgeItem]


class PolicyIssue(BaseModel):
    kind: Literal["advice", "manipulation", "tone", "kids"]
    sentence: str
    reason: str


class PolicyOut(BaseModel):
    no_advice: bool
    issues: list[PolicyIssue]


# ---------------------------------------------------------------- validation
@lru_cache
def _schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMAS_DIR / f"{name}.schema.json").read_text(encoding="utf-8"))


def validate_doc(name: str, doc: Mapping[str, Any]) -> None:
    """Raise jsonschema.ValidationError if ``doc`` violates /schemas/{name}.schema.json."""
    jsonschema.validate(doc, _schema(name), format_checker=jsonschema.FormatChecker())


class QueriesOut(BaseModel):
    queries: list[str]
