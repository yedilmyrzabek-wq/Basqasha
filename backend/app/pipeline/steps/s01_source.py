"""Step 1: source transcript via yt-dlp subtitles (manual paste is the fallback).

Output: data/projects/{id}/source/transcript.txt + source_material row (no timestamps, no
rolling duplicates from auto-subs)."""
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.db import session_scope
from app.models import Project
from app.pipeline.orchestrator import DONE, StepResult, job_log, register
from app.sources import SourceRepository
from app.storage import project_dir, write_text

TIMEOUT_S = 60
_INLINE_TS = re.compile(r"<\d{1,2}:\d{2}(?::\d{2})?[.,]\d{3}>")
_TAG = re.compile(r"</?[^>]+>")
_NOISE = re.compile(r"\[(?:music|applause|laughter|laughs|cheering|inaudible|silence|__)[^\]]*\]|♪+|NaN:NaN",
                    re.IGNORECASE)
_LEFTOVER_TS = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d{1,3})?\b")


def clean_vtt(raw: str) -> str:
    """WebVTT -> plain text. Auto-subs repeat the previous line in each cue (rolling captions);
    lines equal to one of the last emitted lines are dropped."""
    out: list[str] = []
    started = False
    for line in raw.splitlines():
        s = line.strip()
        if "-->" in s:  # cue timing line; everything before the first one is the header
            started = True
            continue
        if not started or not s or s.isdigit():
            continue
        if s.startswith(("NOTE", "STYLE", "REGION")):
            continue
        s = _INLINE_TS.sub("", s)
        s = html.unescape(_TAG.sub("", s)).replace(" ", " ")
        s = _NOISE.sub(" ", s)
        s = re.sub(r"\s+", " ", s).strip(" -")
        if not s or s in out[-3:]:
            continue
        # rolling auto-subs sometimes re-emit a line as a prefix of the next one
        if out and s.startswith(out[-1]) and len(s) > len(out[-1]):
            out[-1] = s
            continue
        out.append(s)
    return to_paragraphs(" ".join(out))


def clean_pasted(text: str) -> str:
    """Manual paste: also strip timestamps that copy-paste from YouTube's transcript panel brings."""
    lines = []
    for line in text.splitlines():
        s = _LEFTOVER_TS.sub(" ", _NOISE.sub(" ", line))
        s = re.sub(r"\s+", " ", s).strip()
        if s and s not in lines[-2:]:
            lines.append(s)
    return to_paragraphs(" ".join(lines))


def to_paragraphs(text: str, per_par: int = 5) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?…])\s+", text)
    if len(sentences) < 3:  # auto-subs without punctuation: wrap by words
        words = text.split()
        return "\n\n".join(" ".join(words[i:i + 120]) for i in range(0, len(words), 120))
    return "\n\n".join(" ".join(sentences[i:i + per_par]) for i in range(0, len(sentences), per_par))


def _js_runtime_arg() -> str:
    node = get_settings().node_bin
    return "node" if node == "node" else f"node:{node}"


# (player client, sub langs). Asking for one language at a time avoids the timedtext 429 that
# aborts the whole run when yt-dlp fetches several tracks in a row.
ATTEMPTS = ((None, "en-orig"), (None, "en.*"), ("android_vr", "en-orig,en"), ("mweb", "en.*"))


def _run_ytdlp(url: str, out_dir: Path, client: str | None, langs: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "yt_dlp", "--js-runtimes", _js_runtime_arg(),
           "--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", langs,
           "--sub-format", "vtt", "--write-info-json", "--ignore-no-formats-error",
           "--no-playlist", "--no-progress",
           "-o", str(out_dir / "yt.%(ext)s"), url]
    if client:
        cmd[3:3] = ["--extractor-args", f"youtube:player_client={client}"]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=TIMEOUT_S)


def _last_error(stderr: str | None) -> str:
    errs = [ln for ln in (stderr or "").splitlines() if ln.startswith("ERROR")]
    return (errs[-1] if errs else (stderr or "")[-300:])[:400]


def _pick_sub(out_dir: Path) -> Path | None:
    subs = sorted(out_dir.glob("yt.*.vtt"))
    if not subs:
        return None
    by_lang = {p.name[3:-4]: p for p in subs}
    for pref in ("en-orig", "en", "en-US", "en-GB"):
        if pref in by_lang:
            return by_lang[pref]
    return subs[0]


def fetch(project_id: uuid.UUID, url: str) -> dict:
    out_dir = project_dir(project_id, "source/ytdlp")
    for f in out_dir.glob("yt.*"):
        f.unlink()
    errors = []
    for client, langs in ATTEMPTS:
        try:
            r = _run_ytdlp(url, out_dir, client, langs)
        except subprocess.TimeoutExpired:
            errors.append(f"client={client or 'default'}/{langs}: timeout {TIMEOUT_S}s")
            continue
        sub = _pick_sub(out_dir)
        if sub is not None:
            info_p = out_dir / "yt.info.json"
            info = json.loads(info_p.read_text(encoding="utf-8")) if info_p.exists() else {}
            return {"vtt": sub.read_text(encoding="utf-8", errors="replace"), "lang": sub.name[3:-4],
                    "info": info, "client": client or "default"}
        errors.append(f"client={client or 'default'}/{langs} exit={r.returncode}: {_last_error(r.stderr)}")
    raise RuntimeError("yt-dlp could not get English subtitles; paste the transcript manually. "
                       + " | ".join(errors))


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

    got = fetch(project_id, url)
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
