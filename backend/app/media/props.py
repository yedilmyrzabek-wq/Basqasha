"""storyboard + words.json + poses.json -> Remotion props (ARCHITECTURE §5, schemas/props.schema.json).

Assets are written as paths relative to ``asset_root()`` (the common parent of DATA_DIR and
LIBRARY_DIR); the engine scripts serve them from a temporary local HTTP server (`--root`), so a
render does not depend on the API process being up.
"""
from __future__ import annotations

import math
import os
import re
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.media import library

FPS = 30
SFX_MIN_GAP = 8               # frames (~0.25 s)
SFX_PER_MIN = 24
DEFAULT_VOLUME = {"whoosh": 0.5, "pop": 0.6}
MUSIC_VOLUME = 0.12
CAPTION_TAIL = 6


def asset_root() -> Path:
    s = get_settings()
    return Path(os.path.commonpath([s.data_path, s.library_path]))


def asset(path: Path) -> str:
    return path.resolve().relative_to(asset_root()).as_posix()


def frame(t: float) -> int:
    return int(round(t * FPS))


def _letters(w: str) -> str:
    return re.sub(r"[^\w-]", "", w)


def _stem(w: str) -> str:
    return _letters(w).lower()[:5]


def _phrase_split(words: list[dict], a: int, b: int) -> list[tuple[int, int]]:
    """Split a scene's words into caption phrases of <= 7 words / <= 42 chars, no 1-word tail."""
    out: list[list[int]] = [[]]
    for i in range(a, b + 1):
        cur = out[-1]
        text = " ".join(words[j]["w"] for j in cur + [i])
        if cur and (len(cur) >= 7 or len(text) > 42):
            out.append([i])
        else:
            cur.append(i)
    if len(out) > 1 and len(out[-1]) == 1:
        if len(out[-2]) < 7:
            out[-2] += out.pop()
        else:
            out[-1].insert(0, out[-2].pop())
    return [(p[0], p[-1]) for p in out if p]


def _keyword(words: list[dict], a: int, b: int, wanted: str | None) -> str:
    if wanted and any(_letters(words[i]["w"]).lower().startswith(wanted.lower()) for i in range(a, b + 1)):
        return wanted
    longest = max(range(a, b + 1), key=lambda i: len(_letters(words[i]["w"])))
    return _stem(words[longest]["w"]) or words[longest]["w"]


def build(sb: dict[str, Any], words_doc: dict[str, Any], images: dict[str, Path], voice: Path, *,
          composition: str = "Explainer", sponsor: str | None = None) -> dict[str, Any]:
    words = words_doc["words"]
    duration_frames = math.ceil(words_doc["duration"] * FPS)
    poses = {p["name"]: p for p in library.poses()}
    sfx_files = library.sfx()
    lib = get_settings().library_path
    scenes_sb = sb["scenes"]

    # scene boundaries (absolute frames)
    starts = [0]
    for s in scenes_sb[1:]:
        w = s["start_word"]
        f = max(frame(words[w - 1]["end"]), frame(words[w]["start"]) - 3)
        starts.append(max(f, starts[-1] + 1))
    ends = starts[1:] + [duration_frames]

    scenes, captions, sfx = [], [], []
    prev_bg = None
    for s, f0, f1 in zip(scenes_sb, starts, ends):
        rel = lambda w: max(0, frame(words[w]["start"]) - f0)  # noqa: E731 - scene-relative frame
        cam = s["camera"]
        bg = {"src": asset(images[s["background"]]), "zoom_from": cam["zoom_from"], "zoom_to": cam["zoom_to"],
              "focus": list(cam["focus"])}
        if cam.get("punch_at_word") is not None:
            bg["punch"] = [rel(cam["punch_at_word"])]
        scene: dict[str, Any] = {"id": s["id"], "from": f0, "duration": max(1, f1 - f0), "background": bg}

        ch = s.get("character")
        if ch and ch.get("pose") in poses:
            sched = [{"at": 0, "pose": ch["pose"]}] + [{"at": rel(pc["at_word"]), "pose": pc["pose"]}
                                                       for pc in ch.get("pose_changes", []) or []]
            scene["character"] = {
                "x": ch["x"], "y": ch["y"], "height": ch.get("height", 470), "flip": bool(ch.get("flip", False)),
                "schedule": [{**e, "src": asset(lib / "poses" / poses[e["pose"]]["file"]),
                              "width": int(poses[e["pose"]]["width"]), "height": int(poses[e["pose"]]["height"]),
                              "scale": float(poses[e["pose"]].get("scale", 1.0))}
                             for e in sched]}
        else:
            scene["character"] = None

        overlays = []
        for o in s.get("overlays", []) or []:
            item = {k: v for k, v in o.items() if k != "at_word"}
            item["at"] = rel(o["at_word"])
            overlays.append(item)
            if o["type"] in ("label", "stamp"):
                sfx.append(("pop", f0 + item["at"], None, 2))
        scene["overlays"] = overlays
        scenes.append(scene)

        if prev_bg is not None and s["background"] != prev_bg:
            sfx.append(("whoosh", f0, None, 1))
        prev_bg = s["background"]
        for x in s.get("sfx", []) or []:
            sfx.append((x["file"], frame(words[x["at_word"]]["start"]), x.get("volume"), 0))

        phrases = ([(c["start_word"], c["end_word"], c["keyword"]) for c in s["captions"]] if s.get("captions")
                   else [(a, b, s.get("caption_keyword")) for a, b in _phrase_split(words, s["start_word"], s["end_word"])])
        for a, b, kw in phrases:
            captions.append({"from": frame(words[a]["start"]), "to": frame(words[b]["end"]) + CAPTION_TAIL,
                             "text": " ".join(words[i]["w"] for i in range(a, b + 1)),
                             "keyword": _keyword(words, a, b, kw)})

    for c, nxt in zip(captions, captions[1:]):
        c["to"] = max(c["from"] + 1, min(c["to"], nxt["from"]))
    captions[-1]["to"] = min(captions[-1]["to"], duration_frames)

    props: dict[str, Any] = {
        "composition": composition, "width": 1920 if composition == "Explainer" else 1080,
        "height": 1080 if composition == "Explainer" else 1920, "fps": FPS, "duration_frames": duration_frames,
        "language": sb["language"], "voice": {"src": asset(voice), "volume": 1.0},
        "music": None, "progress_bar": True,
        "sponsor_badge": {"text": sponsor, "from": 0, "duration": 150} if sponsor else None,
        "scenes": scenes, "captions": captions,
        "sfx": _sfx(sfx, sfx_files, lib, duration_frames),
    }
    mus = library.music()
    if mus and (lib / "sfx" / mus[0]["file"]).is_file():
        props["music"] = {"src": asset(lib / "sfx" / mus[0]["file"]), "volume": MUSIC_VOLUME}
    return props


def _sfx(items: list[tuple[str, int, float | None, int]], files: dict[str, str], lib: Path,
         duration_frames: int) -> list[dict[str, Any]]:
    """Explicit storyboard SFX first, then auto whooshes, then auto pops; >= 0.25 s apart, <= 24/min."""
    cap = max(1, int(SFX_PER_MIN * duration_frames / (60 * FPS)))
    kept: list[tuple[str, int, float | None]] = []
    for name, f, vol, _prio in sorted(items, key=lambda x: (x[3], x[1])):
        if name not in files or len(kept) >= cap:
            continue
        if any(abs(f - k[1]) < SFX_MIN_GAP for k in kept):
            continue
        kept.append((name, f, vol))
    return [{"src": asset(lib / "sfx" / files[n]), "from": max(0, f),
             "volume": v if v is not None else DEFAULT_VOLUME.get(n, 0.7)}
            for n, f, v in sorted(kept, key=lambda k: k[1])]
