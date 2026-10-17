"""YouTube helpers shared by step 1 (source transcript), step 10 (source thumbnail) and «Конкуренты»:
yt-dlp calls, subtitle cleaning, thumbnail download. No database access here."""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

from app import cancel
from app.config import get_settings

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


def js_runtime_arg() -> str:
    node = get_settings().node_bin
    return "node" if node == "node" else f"node:{node}"


# (player client, sub langs). Asking for one language at a time avoids the timedtext 429 that
# aborts the whole run when yt-dlp fetches several tracks in a row.
ATTEMPTS = ((None, "en-orig"), (None, "en.*"), ("android_vr", "en-orig,en"), ("mweb", "en.*"))


def run_subs(url: str, out_dir: Path, client: str | None, langs: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, "-m", "yt_dlp", "--js-runtimes", js_runtime_arg(),
           "--skip-download", "--write-subs", "--write-auto-subs", "--sub-langs", langs,
           "--sub-format", "vtt", "--write-info-json", "--ignore-no-formats-error",
           "--no-playlist", "--no-progress",
           "-o", str(out_dir / "yt.%(ext)s"), url]
    if client:
        cmd[3:3] = ["--extractor-args", f"youtube:player_client={client}"]
    return cancel.run(cmd, timeout=TIMEOUT_S)


def last_error(stderr: str | None) -> str:
    errs = [ln for ln in (stderr or "").splitlines() if ln.startswith("ERROR")]
    return (errs[-1] if errs else (stderr or "")[-300:])[:400]


def pick_sub(out_dir: Path) -> Path | None:
    subs = sorted(out_dir.glob("yt.*.vtt"))
    if not subs:
        return None
    by_lang = {p.name[3:-4]: p for p in subs}
    for pref in ("en-orig", "en", "en-US", "en-GB"):
        if pref in by_lang:
            return by_lang[pref]
    return subs[0]


def fetch_subs(url: str, out_dir: Path, attempts: tuple = ATTEMPTS) -> dict:
    """English subtitles + info.json of one video into ``out_dir``: {vtt, lang, info, client}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob("yt.*"):
        f.unlink()
    errors = []
    for client, langs in attempts:
        try:
            r = run_subs(url, out_dir, client, langs)
        except subprocess.TimeoutExpired:
            errors.append(f"client={client or 'default'}/{langs}: timeout {TIMEOUT_S}s")
            continue
        sub = pick_sub(out_dir)
        if sub is not None:
            info_p = out_dir / "yt.info.json"
            info = json.loads(info_p.read_text(encoding="utf-8")) if info_p.exists() else {}
            return {"vtt": sub.read_text(encoding="utf-8", errors="replace"), "lang": sub.name[3:-4],
                    "info": info, "client": client or "default"}
        errors.append(f"client={client or 'default'}/{langs} exit={r.returncode}: {last_error(r.stderr)}")
    raise RuntimeError("yt-dlp could not get English subtitles; paste the transcript manually. "
                       + " | ".join(errors))


def run(args: list[str], timeout: int = 180) -> subprocess.CompletedProcess:
    """Any yt-dlp call (e.g. a channel's flat playlist)."""
    return cancel.run([sys.executable, "-m", "yt_dlp", "--js-runtimes", js_runtime_arg(), "--no-progress", *args],
                      timeout=timeout)


def download(url: str, out: Path) -> Path | None:
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = r.read()
    except Exception:  # noqa: BLE001 - optional asset
        return None
    if len(data) <= 1000:
        return None
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    return out


def thumbnail(video_id: str | None, out: Path) -> Path | None:
    """Best available thumbnail of a video (kept if already downloaded)."""
    if not video_id:
        return None
    if out.is_file() and out.stat().st_size > 1000:
        return out
    for name in ("maxresdefault.jpg", "hqdefault.jpg"):
        if download(f"https://i.ytimg.com/vi/{video_id}/{name}", out):
            return out
    return None
