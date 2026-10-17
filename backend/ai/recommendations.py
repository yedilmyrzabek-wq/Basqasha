"""Step 11 «Рекомендации»: after the video is made, the AI looks at what this video needed and what our
library has, and tells the owner what to add or change (poses / costumes of the mascot, sounds, music,
backgrounds, script, packaging), where to put it and — for images — a ready Google Flow prompt."""
from __future__ import annotations

import json
from typing import Any, Literal, Mapping

from pydantic import BaseModel, Field

from app.providers.interfaces import CallContext, ILLM
from ai.prompts import load_prompt


class Recommendation(BaseModel):
    category: Literal["character", "poses", "sounds", "music", "backgrounds", "script", "packaging", "pipeline"]
    priority: int = Field(description="1 = do before the next video, 2 = soon, 3 = nice to have")
    title: str = Field(description="RUSSIAN, short")
    details: str = Field(description="RUSSIAN: what was missing in THIS video (scene / moment) and why it matters")
    where: str = Field(description="RUSSIAN: exactly where / how to add it (folder, page, file name)")
    flow_prompt: str = Field("", description="ENGLISH prompt for Google Flow when an image / pose sheet is needed, else empty")


class RecommendationsOut(BaseModel):
    summary: str = Field(description="RUSSIAN, 2-4 sentences")
    items: list[Recommendation]


def build_recommendations(llm: ILLM, model: str, context: Mapping[str, Any], *, ctx: CallContext) -> dict[str, Any]:
    p = load_prompt("recommendations")
    text = p.render(context_json=json.dumps(context, ensure_ascii=False, indent=1),
                    character_block=context.get("character_block") or "a simple stickman mascot")
    out = llm.generate_json(prompt=text, response_model=RecommendationsOut, model=model, ctx=ctx,
                            max_output_tokens=8000).value
    items = sorted((i.model_dump() for i in out.items), key=lambda i: i["priority"])
    return {"summary": out.summary, "items": [{**i, "done": False} for i in items]}
