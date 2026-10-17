"""Step 1: source transcript via yt-dlp subtitles (manual paste is the fallback).

Output: data/projects/{id}/source/transcript.txt + source_material row (no timestamps, no
rolling duplicates from auto-subs)."""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone

from app.db import session_scope
from app.models import Project
from app.pipeline.orchestrator import DONE, StepResult, job_log, register
from app.sources import SourceRepository
from app.sources.youtube import clean_pasted, clean_vtt, fetch_subs
from app.storage import project_dir, write_text


@register("source")
def run(project_id: uuid.UUID) -> StepResult:
    with session_scope() as db:
        p = db.get(Project, project_id)
        url = p.source_url
        existing = SourceRepository(db).get(project_id)
        if not url:
            if existing is not None:
                return DONE  # manual transcript already present
            raise RuntimeError("No source URL; paste the transcript manually")

    got = fetch_subs(url, project_dir(project_id, "source/ytdlp"))
    transcript = clean_vtt(got["vtt"])
    if len(transcript) < 200:
        raise RuntimeError(f"Subtitles too short after cleaning ({len(transcript)} chars); paste manually")
    info = got["info"]
    with session_scope() as db:
        rel = write_text(project_dir(project_id, "source") / "transcript.txt", transcript)
        SourceRepository(db).upsert(
            project_id, source_url=url, yt_video_id=info.get("id"), yt_title=info.get("title"),
            yt_channel=info.get("channel") or info.get("uploader"), yt_duration=info.get("duration"),
            yt_views=info.get("view_count"), views_checked_at=datetime.now(timezone.utc) if info.get("view_count") else None,
            origin="yt_dlp", transcript=transcript)
        job_log(db, project_id, "source",
                f"Transcript: {len(transcript.split())} words from '{got['lang']}' subs "
                f"(client {got['client']}) -> {rel}")
    shutil.rmtree(project_dir(project_id, "source/ytdlp"), ignore_errors=True)
    return DONE


def save_manual(db, project_id: uuid.UUID, text: str, source_url: str | None) -> str:
    """PUT /source and create-with-transcript: store the pasted text (caller completes the step)."""
    transcript = clean_pasted(text)
    write_text(project_dir(project_id, "source") / "transcript.txt", transcript)
    repo = SourceRepository(db)
    prev = repo.get(project_id)
    fields = {"origin": "manual", "transcript": transcript, "source_url": source_url}
    if prev is not None and not source_url:
        fields["source_url"] = prev.source_url
    repo.upsert(project_id, **fields)
    return transcript
