"""Storyboard repair + rule validation (ARCHITECTURE §5). Mechanical problems (gaps in the word
tiling, at_word outside its scene, unknown pose / sfx / background) are repaired and reported as
fixes; the remaining rule violations go to storyboard.errors and never block the pipeline."""
from __future__ import annotations

import copy
import re
from collections import defaultdict
from typing import Any

FPS = 30


def _stem_match(stem: str, word: str) -> bool:
    w = re.sub(r"[^\w-]", "", word).lower()
    return w.startswith(stem.lower())


def repair(sb: dict[str, Any], words: list[dict], poses: set[str], sfx: set[str]) -> tuple[dict, list[str]]:
    """Return (fixed copy, list of fixes)."""
    sb = copy.deepcopy(sb)
    fixes: list[str] = []
    n = len(words)
    sb["fps"] = FPS
    scenes = [s for s in sb.get("scenes", []) if isinstance(s, dict)]   # array order is authoritative
    bg_ids = [b["id"] for b in sb.get("backgrounds", []) if isinstance(b, dict) and "id" in b]
    if not scenes or not bg_ids:
        raise ValueError("Storyboard has no scenes or no backgrounds")

    # contiguous tiling 0..n-1
    out: list[dict] = []
    for s in scenes:
        start = out[-1]["end_word"] + 1 if out else 0
        end = min(int(s.get("end_word", start)), n - 1)
        if s.get("start_word") != start:
            fixes.append(f"scene {s.get('id')}: start_word {s.get('start_word')} -> {start}")
        if end < start:
            if out:
                fixes.append(f"scene {s.get('id')}: empty after tiling, merged into the previous scene")
            continue
        s["start_word"], s["end_word"] = start, end
        out.append(s)
    if out and out[-1]["end_word"] != n - 1:
        fixes.append(f"last scene end_word {out[-1]['end_word']} -> {n - 1}")
        out[-1]["end_word"] = n - 1
    if not out:
        raise ValueError("Storyboard scenes cover no words")

    default_pose = sorted(poses)[0] if poses else None
    for idx, s in enumerate(out, start=1):
        if s.get("id") != idx:
            s["id"] = idx
        a, b = s["start_word"], s["end_word"]
        s["text"] = " ".join(w["w"] for w in words[a:b + 1])
        clamp = lambda v: min(max(int(v), a), b)  # noqa: E731
        if s.get("background") not in bg_ids:
            fixes.append(f"scene {idx}: unknown background {s.get('background')} -> {bg_ids[0]}")
            s["background"] = bg_ids[0]
        cam = s.setdefault("camera", {"zoom_from": 1.0, "zoom_to": 1.08, "focus": [0.5, 0.5]})
        if cam.get("punch_at_word") is not None:
            cam["punch_at_word"] = clamp(cam["punch_at_word"])
        ch = s.get("character")
        if ch:
            if ch.get("pose") not in poses and default_pose:
                fixes.append(f"scene {idx}: unknown pose {ch.get('pose')} -> {default_pose}")
                ch["pose"] = default_pose
            keep = []
            for pc in ch.get("pose_changes", []) or []:
                if pc.get("pose") not in poses:
                    fixes.append(f"scene {idx}: dropped pose change to unknown pose {pc.get('pose')}")
                    continue
                pc["at_word"] = clamp(pc["at_word"])
                keep.append(pc)
            ch["pose_changes"] = keep
        for o in s.get("overlays", []) or []:
            if "at_word" in o:
                o["at_word"] = clamp(o["at_word"])
        kept_sfx = []
        for x in s.get("sfx", []) or []:
            if x.get("file") not in sfx:
                fixes.append(f"scene {idx}: dropped unknown sfx {x.get('file')}")
                continue
            x["at_word"] = clamp(x.get("at_word", a))
            kept_sfx.append(x)
        if "sfx" in s:
            s["sfx"] = kept_sfx
        caps = []
        for c in s.get("captions", []) or []:
            c["start_word"], c["end_word"] = clamp(c["start_word"]), clamp(c["end_word"])
            if c["end_word"] >= c["start_word"]:
                caps.append(c)
        if "captions" in s:
            s["captions"] = caps
    sb["scenes"] = out
    return sb, fixes


def check(sb: dict[str, Any], words: list[dict], poses: set[str]) -> list[str]:
    """Rule violations (shown in the UI under the storyboard)."""
    errs: list[str] = []
    scenes = sb["scenes"]
    t = lambda i: words[i]["start"]  # noqa: E731
    expect = 0
    for s in scenes:
        if s["start_word"] != expect:
            errs.append(f"scene {s['id']}: words not contiguous (starts at {s['start_word']}, expected {expect})")
        expect = s["end_word"] + 1
    if expect != len(words):
        errs.append(f"scenes cover words 0..{expect - 1} of {len(words)}")

    bg_uses: dict[str, list[dict]] = defaultdict(list)
    for i, s in enumerate(scenes):
        a, b = s["start_word"], s["end_word"]
        start = t(a)
        end = t(scenes[i + 1]["start_word"]) if i + 1 < len(scenes) else words[-1]["end"]
        dur = end - start
        events = _events(s)
        limit = 9.0 if len(events) >= 3 else 7.5
        if dur < 2.5 or dur > limit:
            errs.append(f"scene {s['id']}: {dur:.1f} s (allowed 2.5-{limit:g} s)")
        if len(events) < 2:
            errs.append(f"scene {s['id']}: {len(events)} visual event(s), need >= 2")
        if events and min(t(w) for w in events) - start > 0.6:
            errs.append(f"scene {s['id']}: first event {min(t(w) for w in events) - start:.1f} s after scene start (max 0.6)")
        bg_uses[s["background"]].append(s)
        ch = s.get("character")
        if ch:
            for p in [ch.get("pose")] + [pc["pose"] for pc in ch.get("pose_changes", []) or []]:
                if p not in poses:
                    errs.append(f"scene {s['id']}: pose '{p}' not in poses.json")
        for c in _captions(s):
            phrase = words[c["start_word"]:c["end_word"] + 1]
            if not 2 <= len(phrase) <= 7:
                errs.append(f"scene {s['id']}: caption of {len(phrase)} words (2-7)")
            if len(" ".join(w["w"] for w in phrase)) > 42 * 2:
                errs.append(f"scene {s['id']}: caption longer than 2 lines of 42 chars")
            hits = sum(_stem_match(c["keyword"], w["w"]) for w in phrase)
            if hits != 1:
                errs.append(f"scene {s['id']}: keyword '{c['keyword']}' matches {hits} words of its phrase")

    for bg in sb["backgrounds"]:
        uses = bg_uses.get(bg["id"], [])
        if not 2 <= len(uses) <= 4:
            errs.append(f"{bg['id']}: used {len(uses)} times (2-4)")
        for x, y in zip(uses, uses[1:]):
            cx, cy = x["camera"], y["camera"]
            df = max(abs(cx["focus"][0] - cy["focus"][0]), abs(cx["focus"][1] - cy["focus"][1]))
            dz = abs(cx["zoom_to"] - cy["zoom_to"])
            if df < 0.15 and dz < 0.05:
                errs.append(f"{bg['id']}: scenes {x['id']} and {y['id']} reuse it without a new focus/zoom")

    hook = [s for s in scenes if t(s["start_word"]) < 15.0]
    short = [s for i, s in enumerate(scenes[:len(hook)])
             if (t(scenes[i + 1]["start_word"]) if i + 1 < len(scenes) else words[-1]["end"]) - t(s["start_word"]) <= 4.0]
    if len(short) < 4:
        errs.append(f"hook (first 15 s): {len(short)} scenes of <= 4 s (need >= 4)")
    return errs


def _events(s: dict) -> list[int]:
    """Word indices of visual events: overlays, pose changes, punch-in."""
    ev = [o["at_word"] for o in s.get("overlays", []) or [] if "at_word" in o]
    ch = s.get("character") or {}
    ev += [pc["at_word"] for pc in ch.get("pose_changes", []) or []]
    if s.get("camera", {}).get("punch_at_word") is not None:
        ev.append(s["camera"]["punch_at_word"])
    return ev


def _captions(s: dict) -> list[dict]:
    if s.get("captions"):
        return s["captions"]
    return [{"start_word": s["start_word"], "end_word": s["end_word"], "keyword": s.get("caption_keyword", "")}]

