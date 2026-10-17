"""«Конкуренты» — the growth manager (owner idea 2026-10-18).

1. analyze_item: one competitor video / channel / screenshot (+ the owner's comment) -> why it works,
   what the audience likes, how we apply it, rule candidates, video ideas. Thumbnails are images
   the model looks at (Claude CLI: Read tool; Gemini: native vision).
2. synthesize: all breakdowns + the current living docs -> a new playbook (docs/growth/playbook.md),
   proposed changes to the other living docs, and "what to film next". The owner applies the changes.
3. ask: a free question to the agent with the same context.

The playbook is injected into the idea / script / storyboard / metadata prompts ({{playbook}}, see
ai.prompts), so what we learn from competitors changes the next video.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal, Sequence

from pydantic import BaseModel, Field

from app.providers.interfaces import CallContext, ILLM
from ai.prompts import load_prompt

log = logging.getLogger("ai.growth")
REPO = Path(__file__).resolve().parents[2]
PLAYBOOK = REPO / "docs" / "growth" / "playbook.md"
# docs the agent may change: everything in docs/growth (create / update / delete) + two research docs
EDITABLE_FIXED = ("docs/research/reference_channels.md", "docs/research/topics_backlog.md")
PLAYBOOK_PROMPT_CHARS = 6000

CHANNEL = (
    "Basqasha: a Kazakh-language YouTube channel of animated stickman explainers (2D hand-drawn, our mascot is a "
    "white round-headed stickman in a white Kazakh kalpak, turquoise scarf, navy hoodie). Business model: the owner "
    "picks a viral English animated explainer (psychology, discipline, brain, science, money, facts, history) and we "
    "make our own Kazakh video on the same idea — our own text, pictures and voice (ElevenLabs). Audience: Kazakh "
    "speakers 13+, mostly on phones. Production: 3-10 min videos, ~30 illustrated backgrounds, poses of the mascot, "
    "captions, sound effects; thumbnails are made in Google Flow. Owner rules: topics are UNIVERSAL — never Kazakh / "
    "nomad / ethnographic topics and no forced Kazakhstan angle (yurts, auls, nomads only if the source itself is "
    "about them); a local everyday example inside a universal topic is fine."
)


# ------------------------------------------------------------------ output models
class Insight(BaseModel):
    aspect: Literal["topic", "title", "thumbnail", "hook", "structure", "pacing", "visuals", "audio",
                    "character", "emotion", "community", "other"]
    insight: str = Field(description="RUSSIAN, 1-2 sentences, concrete")


class Rule(BaseModel):
    area: Literal["ideas", "titles", "thumbnails", "script", "storyboard", "visuals", "audio", "publishing"]
    rule: str = Field(description="RUSSIAN, one actionable rule we can follow, with a number when possible")


class Idea(BaseModel):
    title_kk: str = Field(description="working title in Kazakh, simple spoken, <= 60 chars")
    why_ru: str = Field(description="RUSSIAN: why it will work for our audience")
    source_url: str | None = Field(None, description="the English video to base it on, if known")


class ItemAnalysisOut(BaseModel):
    summary: str = Field(description="RUSSIAN, 2-4 sentences: what this is and the main lesson")
    why_it_works: list[Insight]
    audience: str = Field(description="RUSSIAN: what viewers like here (and what they would dislike)")
    title_pattern: str = Field(description="RUSSIAN: the title formula, e.g. 'простой вопрос «Что X делали весь день?»'")
    thumbnail_concept: str = Field(description="RUSSIAN: what the thumbnail shows and why it is clicked")
    hook: str = Field(description="RUSSIAN: how the first 10-30 s hold the viewer (or 'нет данных')")
    apply_for_us: list[str] = Field(description="RUSSIAN, 3-7 concrete things we do in our next videos")
    rules: list[Rule]
    video_ideas: list[Idea] = Field(description="0-5 ideas for us inspired by this")
    learn_score: int = Field(description="0-10: how much we can learn from it")


class DocChange(BaseModel):
    path: str = Field(description="repo-relative path, e.g. docs/growth/playbook.md")
    action: Literal["update", "create", "delete"]
    reason: str = Field(description="RUSSIAN: what changes and why")
    content: str = Field("", description="full new Markdown content (empty for delete)")


class FilmIdea(BaseModel):
    title_kk: str
    why_ru: str
    source_url: str | None = None
    priority: int = Field(description="1 = film first")


class SynthesisOut(BaseModel):
    summary: str = Field(description="RUSSIAN: what we learned overall, 3-6 sentences")
    playbook_md: str = Field(description="full new content of docs/growth/playbook.md (RUSSIAN)")
    doc_changes: list[DocChange] = Field(description="changes to OTHER living docs (not the playbook)")
    film_next: list[FilmIdea] = Field(description="3-10 videos to make next, best first")


class AnswerOut(BaseModel):
    answer_md: str = Field(description="RUSSIAN Markdown answer")
    film_next: list[FilmIdea] = Field(default_factory=list)


# ------------------------------------------------------------------ helpers
def playbook_text() -> str:
    try:
        return PLAYBOOK.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def playbook_for_prompts() -> str:
    """Section added to generation prompts; empty when there is no playbook yet."""
    text = playbook_text()
    if not text:
        return ""
    if len(text) > PLAYBOOK_PROMPT_CHARS:
        text = text[:PLAYBOOK_PROMPT_CHARS].rsplit("\n", 1)[0] + "\n…"
    return ("\n## Lessons from competitors (the owner's growth playbook — follow the rules that apply to this task)\n"
            + text + "\n")


def editable_docs() -> dict[str, str]:
    """Living docs the synthesis may change: path -> current content."""
    out: dict[str, str] = {}
    for p in sorted((REPO / "docs" / "growth").glob("*.md")):
        out[p.relative_to(REPO).as_posix()] = p.read_text(encoding="utf-8")
    for rel in EDITABLE_FIXED:
        p = REPO / rel
        if p.is_file():
            out[rel] = p.read_text(encoding="utf-8")
    return out


def allowed_change(path: str, action: str) -> bool:
    path = path.replace("\\", "/").lstrip("/")
    if ".." in path or not path.endswith(".md"):
        return False
    if path.startswith("docs/growth/") and path.count("/") == 2:
        return path != "docs/growth/playbook.md" or action != "delete"
    return path in EDITABLE_FIXED and action == "update"


def _compact(analyses: Sequence[dict[str, Any]]) -> str:
    return json.dumps(list(analyses), ensure_ascii=False, indent=0)[:60_000]


# ------------------------------------------------------------------ calls
def analyze_item(llm: ILLM, model: str, item: dict[str, Any], images: Sequence[Path], ctx: CallContext) -> dict:
    p = load_prompt("growth_item")
    text = p.render(channel=CHANNEL, item_json=json.dumps(item, ensure_ascii=False, indent=1),
                    images_note=(f"{len(images)} image(s) attached: thumbnails / screenshots — look at each one."
                                 if images else "No images attached."),
                    playbook_now=playbook_text()[:4000] or "(empty — this is one of the first breakdowns)")
    out = llm.generate_json(prompt=text, response_model=ItemAnalysisOut, model=model, ctx=ctx,
                            images=list(images), max_output_tokens=6000).value
    return out.model_dump()


def synthesize(llm: ILLM, model: str, items: Sequence[dict[str, Any]], our_projects: Sequence[dict[str, Any]],
               ctx: CallContext) -> dict:
    docs = editable_docs()
    p = load_prompt("growth_synthesis")
    text = p.render(channel=CHANNEL, items_json=_compact(items),
                    projects_json=json.dumps(list(our_projects), ensure_ascii=False),
                    playbook_now=docs.get("docs/growth/playbook.md", "(no playbook yet)"),
                    docs_json=json.dumps({k: v for k, v in docs.items() if k != "docs/growth/playbook.md"},
                                         ensure_ascii=False, indent=1))
    out = llm.generate_json(prompt=text, response_model=SynthesisOut, model=model, ctx=ctx,
                            max_output_tokens=32000).value
    changes = [{**c.model_dump(), "path": c.path.replace("\\", "/").lstrip("/"),
                "old": docs.get(c.path.replace("\\", "/").lstrip("/"))}
               for c in out.doc_changes if allowed_change(c.path, c.action)]
    dropped = [c.path for c in out.doc_changes if not allowed_change(c.path, c.action)]
    if dropped:
        log.warning("synthesis proposed changes outside the living docs (ignored): %s", dropped)
    changes.insert(0, {"path": "docs/growth/playbook.md",
                       "action": "update" if "docs/growth/playbook.md" in docs else "create",
                       "reason": "Плейбук: правила из всех разборов", "content": out.playbook_md,
                       "old": docs.get("docs/growth/playbook.md")})
    return {"summary": out.summary, "doc_changes": changes,
            "film_next": [f.model_dump() for f in sorted(out.film_next, key=lambda f: f.priority)],
            "ignored": dropped}


def ask(llm: ILLM, model: str, question: str, items: Sequence[dict[str, Any]],
        our_projects: Sequence[dict[str, Any]], ctx: CallContext) -> dict:
    p = load_prompt("growth_question")
    text = p.render(channel=CHANNEL, question=question, items_json=_compact(items),
                    projects_json=json.dumps(list(our_projects), ensure_ascii=False),
                    playbook_now=playbook_text() or "(no playbook yet)")
    return llm.generate_json(prompt=text, response_model=AnswerOut, model=model, ctx=ctx,
                             max_output_tokens=8000).value.model_dump()
