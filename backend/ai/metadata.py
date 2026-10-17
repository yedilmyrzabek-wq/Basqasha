"""Step 10: YouTube metadata (schemas/metadata.schema.json). One LLM call writes titles, the
description intro, chapter titles, hashtags, tags and thumbnail texts; code computes chapter times
from the storyboard (+ words.json when given), sources from verified facts and the checklist.
A second call happens only if the titles/thumbnail texts break the rules (video_craft R15-R17,
kazakh_market R14)."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from app.providers.interfaces import CallContext, ILLM, OriginalityReference
from ai.prompts import LANGUAGE_NAMES, load_prompt
from ai.schemas import MetadataOut, validate_doc
from ai.storyboard import beat_of_words

log = logging.getLogger("ai.metadata")
MAX_DESC = 2400
MIN_CHAPTER_S = 10
_TOK = re.compile(r"\w+")


def _mmss(t: float) -> str:
    t = int(round(t))
    return f"{t // 60:02d}:{t % 60:02d}"


def beat_starts(script_doc: Mapping[str, Any], storyboard_doc: Mapping[str, Any],
                words_doc: Mapping[str, Any] | None) -> tuple[list[tuple[str, float]], float]:
    """[(beat, start_seconds)] in order + total seconds."""
    scenes = storyboard_doc["scenes"]
    n_words = scenes[-1]["end_word"] + 1
    if words_doc:
        times = [float(w["start"]) for w in words_doc["words"]]
        total = float(words_doc["duration"])
    else:  # estimate from the voice rate
        sec = 60 / float(script_doc.get("wpm_voice") or 110)
        times = [i * sec for i in range(n_words)]
        total = n_words * sec
    if all(s.get("beat") for s in scenes):
        starts = {}
        for s in scenes:
            starts.setdefault(s["beat"], s["start_word"])
    else:
        starts = {}
        for i, b in enumerate(beat_of_words(script_doc, n_words)):
            starts.setdefault(b, i)
    return [(b, 0.0 if i == 0 else times[min(i, len(times) - 1)]) for b, i in starts.items()], total


def chapter_times(beats: list[tuple[str, float]], total: float) -> list[tuple[str, float]]:
    """First at 00:00, ascending, each >= 10 s long (the last one too)."""
    out: list[tuple[str, float]] = []
    for b, t in beats:
        if not out:
            out.append((b, 0.0))
        elif t - out[-1][1] >= MIN_CHAPTER_S and total - t >= MIN_CHAPTER_S:
            out.append((b, t))
    return out


def _sources(facts_doc: Mapping[str, Any]) -> list[dict[str, str]]:
    facts = [f for f in facts_doc["facts"] if f["status"] == "verified"] or list(facts_doc["facts"])
    seen: dict[str, dict[str, str]] = {}
    for f in facts:
        for s in f.get("sources", []):
            url = s["url"].strip()
            if url.startswith("http") and url not in seen:
                seen[url] = {"title": (s.get("title") or urlparse(url).netloc).strip(), "url": url}
    return list(seen.values())


def _problems(out: MetadataOut, reference: OriginalityReference | None) -> list[str]:
    errs: list[str] = []
    titles = [t.strip() for t in out.titles]
    if len(titles) != 5:
        errs.append(f"need exactly 5 titles, got {len(titles)}")
    for t in titles:
        if not 10 <= len(t) <= 60:
            errs.append(f"title has {len(t)} characters (max 60): {t!r}")
        if "<" in t or ">" in t:
            errs.append(f"title contains < or >: {t!r}")
        if sum(1 for w in _TOK.findall(t) if len(w) >= 3 and w.isupper() and not w.isdigit()) > 1:
            errs.append(f"title has ALL-CAPS words: {t!r}")
    if sum(1 for t in titles if re.search(r"\d", t)) > 2:
        errs.append("at most 2 titles may contain a number")
    if not any(t.endswith("?") for t in titles):
        errs.append("at least 1 title must be a question ending with '?'")
    if len(out.thumbnail_texts) != 3:
        errs.append(f"need exactly 3 thumbnail_texts, got {len(out.thumbnail_texts)}")
    for th in out.thumbnail_texts:
        if len(th.strip()) > 18 or len(th.split()) > 3:
            errs.append(f"thumbnail text too long (<= 3 words, <= 18 chars): {th!r}")
        if th.strip().lower() in {t.lower() for t in titles}:
            errs.append(f"thumbnail text repeats a title: {th!r}")
    if len(out.thumbnail_prompts) != 3:
        errs.append(f"need exactly 3 thumbnail_prompts, got {len(out.thumbnail_prompts)}")
    return errs


def _description(out: MetadataOut, chapters: list[dict[str, str]], sources: list[dict[str, str]],
                 hashtags: list[str]) -> str:
    tail_tags = " ".join(hashtags)
    ch = f"{out.chapters_heading.strip()}:\n" + "\n".join(f"{c['at']} {c['title']}" for c in chapters)
    src_lines = [f"- {s['title']}: {s['url']}" for s in sources]
    intro = out.description_intro.strip()
    desc = ""
    for _ in range(50):
        src = f"{out.sources_heading.strip()}:\n" + "\n".join(src_lines)
        desc = "\n\n".join(x for x in (intro, ch, src, tail_tags) if x)
        if len(desc) <= MAX_DESC:
            return desc
        if len(src_lines) > 3:
            src_lines.pop()
        elif len(intro) > 150:
            intro = intro[: max(150, len(intro) - (len(desc) - MAX_DESC) - 1)].rsplit(" ", 1)[0]
        else:
            break
    return desc[:MAX_DESC]


def build_metadata(llm: ILLM, model: str, script_doc: Mapping[str, Any], facts_doc: Mapping[str, Any],
                   storyboard_doc: Mapping[str, Any], *, language: str, ctx: CallContext,
                   words_doc: Mapping[str, Any] | None = None, ai_disclosure: bool = False,
                   paid_promotion: bool = False, voice_plan_paid: bool | None = None,
                   reference: OriginalityReference | None = None, source_title: str = "",
                   source_views: int | None = None, source_thumb: Path | None = None,
                   character_block: str = "") -> dict[str, Any]:
    """source_* = the competitor video (title, views, downloaded thumbnail): its packaging is analysed
    and title 1 / the thumbnail concept follow it (owner decision 2026-10-18)."""
    beats, total = beat_starts(script_doc, storyboard_doc, words_doc)
    chap = chapter_times(beats, total)
    verified = [{"id": f["id"], "claim": f["claim"], "value": f.get("value")}
                for f in facts_doc["facts"] if f["status"] == "verified"]
    p = load_prompt("metadata")
    values = dict(language_name=LANGUAGE_NAMES.get(language, language), script_title=script_doc.get("title", ""),
                  script_text=script_doc["text"], facts_json=json.dumps(verified, ensure_ascii=False),
                  beats_json=json.dumps([{"beat": b, "at": _mmss(t)} for b, t in chap], ensure_ascii=False),
                  source_title=source_title or (reference.title if reference else "") or "-",
                  source_views=f"{source_views:,}".replace(",", " ") if source_views else "unknown",
                  thumb_note=("The source thumbnail is attached as an image: describe it exactly." if source_thumb
                              else "The source thumbnail is not available: infer a winning concept from the title."),
                  character_block=character_block or "a simple stickman mascot")
    images = [source_thumb] if source_thumb else []
    out = llm.generate_json(prompt=p.render(**values, repair_note=""), response_model=MetadataOut,
                            model=model, ctx=ctx, max_output_tokens=6000, images=images).value
    errs = _problems(out, reference)
    if errs:  # one repair call
        note = "\n## Fix these problems of your previous answer\n" + "\n".join(f"- {e}" for e in errs) + "\n"
        out = llm.generate_json(prompt=p.render(**values, repair_note=note), response_model=MetadataOut,
                                model=model, ctx=ctx, max_output_tokens=6000, images=images).value
        left = _problems(out, reference)
        if left:
            log.warning("metadata still breaks rules after repair: %s", left)

    titles_by_beat = {c.beat: c.title.strip() for c in out.chapter_titles}
    chapters = [{"at": _mmss(t), "title": (titles_by_beat.get(b) or b)[:60]} for b, t in chap]
    hashtags = []
    for h in out.hashtags:
        tag = "#" + re.sub(r"[\s#]+", "", h)
        if len(tag) > 1 and tag not in hashtags:
            hashtags.append(tag)
    hashtags = hashtags[:3]
    sources = _sources(facts_doc)
    doc: dict[str, Any] = {
        "language": language,
        "titles": [t.strip()[:60] for t in out.titles][:5],
        "description": _description(out, chapters, sources, hashtags),
        "chapters": chapters,
        "sources": sources,
        "hashtags": hashtags,
        "tags": [t.strip() for t in out.tags if t.strip()][:15],
        "thumbnail_texts": [t.strip() for t in out.thumbnail_texts][:3],
        "thumbnail_prompts": [t.strip() for t in out.thumbnail_prompts if t.strip()][:3],
        "packaging_notes": out.packaging_notes.strip(),
        "checklist": {"made_for_kids": False, "ai_disclosure": bool(ai_disclosure),
                      "paid_promotion": bool(paid_promotion)},
    }
    if voice_plan_paid is not None:
        doc["checklist"]["voice_plan_paid"] = bool(voice_plan_paid)
    validate_doc("metadata", doc)
    return doc
