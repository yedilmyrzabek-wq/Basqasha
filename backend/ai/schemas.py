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


# ---------------------------------------------------------------- step 6 (storyboard)
class PlanBackground(BaseModel):
    id: str
    prompt: str


class PlanScene(BaseModel):
    id: int
    background: str
    pose: str


class StoryboardPlanOut(BaseModel):
    backgrounds: list[PlanBackground]
    scenes: list[PlanScene]


class PoseChangeOut(BaseModel):
    at_word: int
    pose: str


class OverlayOut(BaseModel):
    type: Literal["label", "counter", "arrow", "coins", "stamp", "note"]
    at_word: int
    text: str | None = None
    value: float | None = None
    suffix: str | None = None
    color: Literal["ink", "red", "blue", "green", "yellow"] | None = None


class SfxOut(BaseModel):
    file: str
    at_word: int


class SceneDetailOut(BaseModel):
    id: int
    pose_changes: list[PoseChangeOut]
    overlays: list[OverlayOut]
    punch_at_word: int | None = None
    keywords: list[int]
    sfx: list[SfxOut]


class StoryboardDetailsOut(BaseModel):
    scenes: list[SceneDetailOut]


# ---------------------------------------------------------------- step 7 (image QA)
class ImageQAOut(BaseModel):
    has_text: bool
    has_people: bool
    style_match: bool
    is_photoreal: bool
    notes: str


# ---------------------------------------------------------------- step 10 (metadata)
class ChapterTitleOut(BaseModel):
    beat: str
    title: str


class MetadataOut(BaseModel):
    packaging_notes: str = ""          # RUSSIAN: how the source video is packaged and what we reuse
    titles: list[str]
    description_intro: str
    chapters_heading: str
    sources_heading: str
    chapter_titles: list[ChapterTitleOut]
    hashtags: list[str]
    tags: list[str]
    thumbnail_texts: list[str]
    thumbnail_prompts: list[str] = []  # English prompts for Google Flow (16:9 YouTube thumbnail)
