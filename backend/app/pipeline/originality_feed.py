"""Builds the OriginalityReference — the only way source text reaches step 4 (checker) and
step 10 (title overlap). Passed explicitly; never put into a generator prompt."""
from __future__ import annotations

import re
import uuid

from app.db import session_scope
from app.providers.interfaces import OriginalityReference
from app.sources import SourceRepository


def load_reference(project_id: uuid.UUID) -> OriginalityReference:
    with session_scope() as db:
        src = SourceRepository(db).get(project_id)
        if src is None:
            raise RuntimeError("No source transcript for the originality check (step 1 output missing)")
        text, title = src.transcript, src.yt_title
    sentences = tuple(s.strip() for s in re.split(r"(?<=[.!?…])\s+|\n{2,}", text) if len(s.strip()) > 3)
    return OriginalityReference(sentences=sentences, title=title)


def excerpts(project_id: uuid.UUID, source_indexes: list[int | None], width: int = 220) -> dict[int, str]:
    """For API display only (flagged sentence -> source excerpt). Indexes follow the list the
    checker compares against (ai/originality.py): sentences with >= 3 words, then the title."""
    wanted = {i for i in source_indexes if i is not None}
    if not wanted:
        return {}
    ref = load_reference(project_id)
    src = [s for s in ref.sentences if len(s.split()) >= 3] + ([ref.title] if ref.title else [])
    return {i: src[i][:width] for i in wanted if 0 <= i < len(src)}
