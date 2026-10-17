"""«Конкуренты»: fetching competitor data (yt-dlp), running the growth agent in the worker and
applying its doc changes (old versions are kept in data/growth/history/)."""
from __future__ import annotations

import json
import logging
import re
import shutil
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select

from app.config import REPO_ROOT, get_settings
from app.db import session_scope
from app.models import CompetitorItem, GrowthReport, Project
from app.providers.interfaces import CallContext
from app.sources import youtube
from app.storage import rel

log = logging.getLogger("app.growth")
CHANNEL_RE = re.compile(r"youtube\.com/(@|channel/|c/|user/)", re.I)
TRANSCRIPT_WORDS = 900          # beginning of the video: hook + structure


def growth_dir(*parts: str) -> Path:
    p = get_settings().data_path / "growth"
    for x in parts:
        p = p / x
    p.mkdir(parents=True, exist_ok=True)
    return p


def kind_of(url: str | None) -> str:
    if not url:
        return "image"
    return "channel" if CHANNEL_RE.search(url) and "watch?v=" not in url else "video"


def _date(s: str | None) -> date | None:
    try:
        return datetime.strptime(s or "", "%Y%m%d").date()
    except ValueError:
        return None


def fetch_video(item_id: uuid.UUID, url: str) -> dict[str, Any]:
    """Title, views, duration, tags, chapters, thumbnail, and the first ~900 words of the transcript."""
    out_dir = growth_dir(str(item_id), "ytdlp")
    try:
        got = youtube.fetch_subs(url, out_dir, youtube.ATTEMPTS[:2])
        info, transcript = got["info"], youtube.clean_vtt(got["vtt"])
    except RuntimeError:  # no subtitles: the info.json alone is still useful
        ip = out_dir / "yt.info.json"
        info = json.loads(ip.read_text(encoding="utf-8")) if ip.exists() else {}
        transcript = ""
    if not info:
        raise RuntimeError("yt-dlp could not read the video (check the link)")
    words = transcript.split()
    thumbs = []
    if info.get("id"):
        t = youtube.thumbnail(info["id"], growth_dir(str(item_id)) / "thumb.jpg")
        if t:
            thumbs.append(rel(t))
    return {
        "title": info.get("title") or "", "channel": info.get("channel") or info.get("uploader"),
        "views": info.get("view_count"), "duration_s": int(info.get("duration") or 0) or None,
        "published": _date(info.get("upload_date")), "thumbs": thumbs,
        "info": {"likes": info.get("like_count"), "comments": info.get("comment_count"),
                 "channel_subscribers": info.get("channel_follower_count"),
                 "tags": (info.get("tags") or [])[:20],
                 "chapters": [c.get("title") for c in (info.get("chapters") or [])][:20],
                 "description_start": (info.get("description") or "")[:600],
                 "transcript_start": " ".join(words[:TRANSCRIPT_WORDS]),
                 "transcript_words_total": len(words)},
    }


def fetch_channel(item_id: uuid.UUID, url: str) -> dict[str, Any]:
    """Channel name, subscribers and its most viewed recent videos (+ thumbnails of the top 4)."""
    base = re.sub(r"/(videos|shorts|streams|featured)/?$", "", url.rstrip("/"))
    r = youtube.run(["--flat-playlist", "--dump-single-json", "--playlist-end", "40", base + "/videos"])
    try:
        data = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"yt-dlp could not read the channel: {(r.stderr or '')[-300:]}") from e
    entries = [e for e in data.get("entries") or [] if e and e.get("id")]
    top = sorted(entries, key=lambda e: e.get("view_count") or 0, reverse=True)[:10]
    thumbs = []
    for e in top[:4]:
        t = youtube.thumbnail(e["id"], growth_dir(str(item_id)) / f"top_{e['id']}.jpg")
        if t:
            thumbs.append(rel(t))
    views = [e.get("view_count") or 0 for e in entries]
    return {
        "title": data.get("channel") or data.get("title") or base, "channel": data.get("channel"),
        "views": None, "duration_s": None, "published": None, "thumbs": thumbs,
        "info": {"channel_subscribers": data.get("channel_follower_count"),
                 "recent_videos_checked": len(entries),
                 "median_views": sorted(views)[len(views) // 2] if views else None,
                 "top_videos": [{"title": e.get("title"), "views": e.get("view_count"),
                                 "duration_s": e.get("duration"),
                                 "url": f"https://www.youtube.com/watch?v={e['id']}"} for e in top],
                 "description_start": (data.get("description") or "")[:600]},
    }


def _ai():
    from app.pipeline import ai_bridge
    return ai_bridge.build(None)


def _item_doc(it: CompetitorItem) -> dict[str, Any]:
    return {"kind": it.kind, "url": it.url, "title": it.title, "channel": it.channel, "views": it.views,
            "duration_s": it.duration_s, "published": it.published.isoformat() if it.published else None,
            "notes": it.notes, **(it.info or {})}


def analyze(item_id: uuid.UUID) -> None:
    """Worker task: fetch data (once), then the AI breakdown."""
    from ai.growth import analyze_item

    with session_scope() as db:
        it = db.get(CompetitorItem, item_id)
        if it is None:
            return
        it.status, it.error = "running", None
        url, kind, have_info = it.url, it.kind, bool(it.info)
    try:
        if url and not have_info:
            got = fetch_channel(item_id, url) if kind == "channel" else fetch_video(item_id, url)
            with session_scope() as db:
                it = db.get(CompetitorItem, item_id)
                it.title = it.title or got["title"]
                it.channel, it.views, it.duration_s, it.published = (got["channel"], got["views"],
                                                                     got["duration_s"], got["published"])
                it.info = got["info"]
                it.images = list(dict.fromkeys([*got["thumbs"], *(it.images or [])]))
        with session_scope() as db:
            it = db.get(CompetitorItem, item_id)
            doc, images = _item_doc(it), [get_settings().data_path / p for p in (it.images or [])]
        ai = _ai()
        images = [p for p in images if p.is_file()][:6]
        res = analyze_item(ai.llm, ai.settings.model_text, doc, images, CallContext(None, None))
        with session_scope() as db:
            it = db.get(CompetitorItem, item_id)
            it.analysis, it.status, it.updated_at = res, "done", datetime.now(timezone.utc)
    except Exception as e:  # noqa: BLE001 - shown on the card
        log.exception("competitor analysis failed")
        with session_scope() as db:
            it = db.get(CompetitorItem, item_id)
            if it is not None:
                it.status, it.error = "failed", str(e)[:1000]


def _context(db) -> tuple[list[dict], list[dict]]:
    items = db.scalars(select(CompetitorItem).where(CompetitorItem.status == "done")
                       .order_by(CompetitorItem.created_at.desc()).limit(40)).all()
    docs = [{**{k: v for k, v in _item_doc(i).items() if k not in ("transcript_start", "description_start")},
             "analysis": i.analysis} for i in items]
    projects = [{"title": p.title, "status": p.status, "source_url": p.source_url, "published_url": p.published_url}
                for p in db.scalars(select(Project).order_by(Project.created_at.desc()).limit(50))]
    return docs, projects


def run_report(report_id: uuid.UUID) -> None:
    """Worker task: playbook synthesis or a question."""
    from ai.growth import ask, synthesize

    with session_scope() as db:
        r = db.get(GrowthReport, report_id)
        if r is None:
            return
        r.status, r.error = "running", None
        kind, question = r.kind, r.question
        items, projects = _context(db)
    try:
        ai = _ai()
        ctx = CallContext(None, None)
        if kind == "synthesis":
            data = synthesize(ai.llm, ai.settings.model_script, items, projects, ctx)
        else:
            data = ask(ai.llm, ai.settings.model_text, question or "", items, projects, ctx)
        with session_scope() as db:
            r = db.get(GrowthReport, report_id)
            r.data, r.status = data, "done"
    except Exception as e:  # noqa: BLE001
        log.exception("growth report failed")
        with session_scope() as db:
            r = db.get(GrowthReport, report_id)
            if r is not None:
                r.status, r.error = "failed", str(e)[:1000]


def apply_changes(report_id: uuid.UUID, paths: list[str] | None = None) -> list[str]:
    """Write the proposed doc changes (all, or only ``paths``); old files go to data/growth/history/."""
    from ai.growth import allowed_change

    with session_scope() as db:
        r = db.get(GrowthReport, report_id)
        if r is None or r.kind != "synthesis" or not r.data:
            raise ValueError("No synthesis with doc changes")
        changes = r.data.get("doc_changes", [])
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    done = []
    for c in changes:
        path, action = c["path"], c["action"]
        if (paths and path not in paths) or not allowed_change(path, action):
            continue
        f = REPO_ROOT / path
        if f.exists():
            backup = growth_dir("history", stamp) / path.replace("/", "__")
            shutil.copyfile(f, backup)
        if action == "delete":
            f.unlink(missing_ok=True)
        else:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(c["content"].rstrip() + "\n", encoding="utf-8")
        done.append(path)
    with session_scope() as db:
        r = db.get(GrowthReport, report_id)
        applied = set((r.data or {}).get("applied", [])) | set(done)
        r.data = {**r.data, "applied": sorted(applied)}
        r.applied_at = datetime.now(timezone.utc)
    return done
