"""Step 6: storyboard (schemas/storyboard.schema.json) from words.json + the approved script.

Code does everything deterministic: scene split on sentence/clause boundaries (DP over word
boundaries), caption phrases, camera moves, layout, whoosh/pop SFX and rule fixes
(video_craft R7-R12, R14). The LLM only designs the backgrounds, picks poses (1 call) and writes
overlays / pose changes / keywords (1 call per <= 30 scenes) -> 2-3 calls per storyboard.
"""
from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from typing import Any, Mapping, Sequence

from app.providers.interfaces import CallContext, ILLM
from ai.prompts import LANGUAGE_NAMES, load_prompt
from ai.schemas import SceneDetailOut, StoryboardDetailsOut, StoryboardPlanOut, validate_doc
from ai.textnorm_kk import NUMBER_WORDS, normalize_kk, num_words

log = logging.getLogger("ai.storyboard")

SEC_PER_SCENE = 5.2
MIN_SCENE, MAX_SCENE, HARD_MAX = 2.5, 7.5, 9.0
HOOK_SECONDS, HOOK_SCENE_MAX, HOOK_TARGET = 15.0, 4.0, 3.3
MAX_EVENT_GAP, FIRST_EVENT = 3.0, 0.6
CHUNK = 30
WINDOW = 40                     # max words per scene considered by the DP
SFX_PER_MIN = 20

# Character: bigger (owner 2026-10-18: "too small") — ~60% of the frame height, feet just above the captions.
CHAR = {"x": 300, "y": 950, "height": 640, "flip": False}
FOCUS = [(0.5, 0.5), (0.68, 0.42), (0.32, 0.6), (0.5, 0.25)]   # pairwise >= 0.15 apart
ZOOM = [(1.0, 1.08), (1.1, 1.02), (1.0, 1.06), (1.08, 1.0)]
# Labels go to the calm upper band next to the character's head (backgrounds keep the subject in the
# right two-thirds and the top calm), not onto the main object in the middle of the picture.
TEXT_SLOTS = [(820, 130), (1300, 130), (820, 270)]
STAMP_XY, NOTE_XY = (1480, 640), (1520, 270)
ARROW = (980, 400, 600, 560)
COINS = (1500, 180, 400, 720)
# Poses are chosen by TAGS (poses.json), so any character library works.
HOOK_TAGS = ("shock", "surprise", "question", "curious", "think")   # scene 1
FILLER_TAGS = ("explain", "point", "think", "shrug", "teach")       # extra pose change to keep motion
DEFAULT_TAGS = ("explain", "neutral", "default")


def poses_with(poses: list[dict], tags: Sequence[str]) -> list[str]:
    """Pose names that carry one of ``tags``, in tag order."""
    out: list[str] = []
    for t in tags:
        out += [p["name"] for p in poses if t in p.get("tags", []) and p["name"] not in out]
    return out


def max_pose_uses(n_scenes: int) -> int:
    """No pose in more than ~1/8 of the scenes (owner feedback: think_chin was in 14 of 47)."""
    return max(3, math.ceil(n_scenes / 8))


def spread_poses(chosen: list[str], poses: list[dict], limit: int) -> list[str]:
    """Replace over-used poses (beyond ``limit``) by the least used pose that shares a tag."""
    tags = {p["name"]: set(p.get("tags", [])) for p in poses}
    used = Counter(chosen)
    out = list(chosen)
    for i, name in enumerate(out):
        if used[name] <= limit:
            continue
        alt = sorted((n for n in tags if n != name and tags[n] & tags.get(name, set()) and used[n] < limit),
                     key=lambda n: used[n])
        if alt:
            used[name] -= 1
            used[alt[0]] += 1
            out[i] = alt[0]
    return out
_CLAUSE_END = re.compile(r"[,;:—–]$")
_SENT_END = re.compile(r"[.!?…]$")


# ------------------------------------------------------------------ helpers
def _clean(w: str) -> str:
    return re.sub(r"[^\w-]", "", w).strip("-")


def scene_count(seconds: float) -> int:
    return max(8, min(400, round(seconds / SEC_PER_SCENE)))  # any length (1-60 min), ~5 s per scene


def bg_count(n_scenes: int, wanted: int = 30) -> int:
    """Unique backgrounds (setting backgrounds_count), never more than scenes and at least 4."""
    return max(4, min(int(wanted), n_scenes))


def bg_min_uses(n_scenes: int, n_bg: int) -> int:
    """Each background is reused 2+ times when there are few of them, otherwise once is fine."""
    return 2 if n_bg * 2 <= n_scenes else 1


class _Timeline:
    def __init__(self, words_doc: Mapping[str, Any]):
        self.words = list(words_doc["words"])
        self.n = len(self.words)
        self.duration = float(words_doc["duration"])
        num = NUMBER_WORDS if words_doc.get("language") == "kk" else set()
        self._num = [_clean(w["w"]).lower() in num for w in self.words]

    def inside_number(self, j: int) -> bool:
        """Breaking after word j would split a spoken number ("он | жеті")."""
        return j + 1 < self.n and self._num[j] and self._num[j + 1]

    def start(self, a: int) -> float:
        return 0.0 if a == 0 else float(self.words[a]["start"])

    def end(self, b: int) -> float:
        return self.duration if b >= self.n - 1 else float(self.words[b + 1]["start"])

    def t(self, i: int) -> float:
        return float(self.words[i]["start"])

    def text(self, a: int, b: int) -> str:
        return " ".join(w["w"] for w in self.words[a:b + 1])

    def boundary_penalty(self, j: int) -> float:
        """Cost of ending a scene after word j: sentence end 0, clause end 1, mid-clause 8."""
        if j >= self.n - 1 or self.words[j]["s"] != self.words[j + 1]["s"] or _SENT_END.search(self.words[j]["w"]):
            return 0.0
        if _CLAUSE_END.search(self.words[j]["w"]):
            return 1.0
        return 20.0 if self.inside_number(j) else 8.0


# ------------------------------------------------------------------ scene split (code)
def split_scenes(tl: _Timeline, n_scenes: int, beats: Sequence[str]) -> list[tuple[int, int]]:
    """Exactly n_scenes contiguous (start_word, end_word) ranges, preferring sentence/clause ends,
    never across a beat boundary, 2.5-7.5 s each, scenes inside the first 15 s <= 4 s (video_craft R7, R9)."""
    n = tl.n
    n_scenes = min(n_scenes, n)
    target = max(4.0, (tl.duration - HOOK_SECONDS) / max(1, n_scenes - round(HOOK_SECONDS / HOOK_TARGET)))
    cost: dict[tuple[int, int], float] = {}
    for a in range(n):
        st = tl.start(a)
        for b in range(a, min(n, a + WINDOW)):
            d = tl.end(b) - st
            if d > HARD_MAX + 3:
                break
            hook = st < HOOK_SECONDS - 0.5
            c = (d - (HOOK_TARGET if hook else target)) ** 2 + tl.boundary_penalty(b)
            if beats[a] != beats[b]:
                c += 40
            if d < MIN_SCENE:
                c += 30 + 20 * (MIN_SCENE - d)
            if d > MAX_SCENE:
                c += 30 + 20 * (d - MAX_SCENE)
            if hook and d > HOOK_SCENE_MAX:
                c += 30 + 20 * (d - HOOK_SCENE_MAX)
            cost[(a, b)] = c
    inf = float("inf")
    # f[k][j]: best cost covering words 0..j with k scenes; back[k][j] = start of the k-th scene
    f = [[inf] * n for _ in range(n_scenes + 1)]
    back = [[-1] * n for _ in range(n_scenes + 1)]
    for j in range(n):
        if (0, j) in cost:
            f[1][j], back[1][j] = cost[(0, j)], 0
    for k in range(2, n_scenes + 1):
        fk, fprev = f[k], f[k - 1]
        for j in range(n):
            best, arg = inf, -1
            for a in range(max(1, j - WINDOW + 1), j + 1):
                c = cost.get((a, j))
                if c is None or fprev[a - 1] == inf:
                    continue
                v = fprev[a - 1] + c
                if v < best:
                    best, arg = v, a
            fk[j], back[k][j] = best, arg
    if f[n_scenes][n - 1] == inf:
        raise ValueError(f"cannot split {n} words into {n_scenes} scenes")
    out, j = [], n - 1
    for k in range(n_scenes, 0, -1):
        a = back[k][j]
        out.append((a, j))
        j = a - 1
    return out[::-1]


def _fits_two_lines(words: Sequence[str], width: int = 42) -> bool:
    lines, cur = 1, 0
    for w in words:
        add = len(w) + (1 if cur else 0)
        if cur + add > width:
            lines, cur = lines + 1, len(w)
        else:
            cur += add
    return lines <= 2 and all(len(w) <= width for w in words)


def split_phrases(tl: _Timeline, a: int, b: int) -> list[tuple[int, int]]:
    """Caption phrases inside a scene: 2-7 words, <= 2 lines of 42 chars, <= 17 chars/s,
    1.2-6 s on screen, preferring punctuation breaks (video_craft R12)."""
    if b - a + 1 <= 2:
        return [(a, b)]
    words = [w["w"] for w in tl.words]

    def cost(s: int, e: int) -> float:
        nw = e - s + 1
        chars = len(" ".join(words[s:e + 1]))
        dur = max(0.1, float(tl.words[e]["end"]) - float(tl.words[s]["start"]))
        c = 0.5 * (nw - 4.5) ** 2 + (0 if e == b or _CLAUSE_END.search(words[e]) or _SENT_END.search(words[e]) else 2)
        if e < b and tl.inside_number(e):
            c += 15
        if nw < 2 or nw > 7 or not _fits_two_lines(words[s:e + 1]):
            c += 50
        if chars / dur > 17 or dur > 6:
            c += 20
        if dur < 1.2:
            c += 5
        return c

    g = {a - 1: (0.0, -1)}
    for e in range(a, b + 1):
        g[e] = min(((g[s - 1][0] + cost(s, e), s) for s in range(max(a, e - 8), e + 1)), key=lambda x: x[0])
    out, e = [], b
    while e >= a:
        s = g[e][1]
        out.append((s, e))
        e = s - 1
    return out[::-1]


def beat_of_words(script_doc: Mapping[str, Any], n_words: int) -> list[str]:
    """Beat id for every words.json index (via the TTS text of each beat; proportional fallback)."""
    lang = script_doc["language"]
    counts = [len((normalize_kk(b["text"]) if lang == "kk" else b["text"]).split()) for b in script_doc["beats"]]
    total = sum(counts) or 1
    if total != n_words:  # voiced text differs from the script: scale proportionally
        counts = [round(c * n_words / total) for c in counts]
        counts[-1] += n_words - sum(counts)
    out: list[str] = []
    for b, c in zip(script_doc["beats"], counts):
        out += [b["beat"]] * max(0, c)
    return (out + [script_doc["beats"][-1]["beat"]] * n_words)[:n_words]


# ------------------------------------------------------------------ background balance (code)
def balance_backgrounds(assign: list[str], bg_ids: list[str], min_uses: int = 2,
                        min_bg: int = 4) -> tuple[list[str], list[str]]:
    """Make every background used min_uses..4 times (video_craft R10)."""
    assign, bg_ids = list(assign), list(bg_ids)
    for _ in range(1000):
        cnt = Counter(assign)
        under = [b for b in bg_ids if cnt[b] < min_uses]
        over = [b for b in bg_ids if cnt[b] > 4]
        if not under and not over:
            break
        if under:
            b = min(under, key=lambda x: cnt[x])
            occ = [i for i, x in enumerate(assign) if x == b]
            donors = [i for i, x in enumerate(assign) if x != b and cnt[x] > min_uses]
            if not donors:
                if len(bg_ids) > min_bg:
                    for i in occ:  # drop b: give its scene to a neighbour
                        nb = assign[i - 1] if i > 0 else assign[i + 1]
                        assign[i] = nb
                    bg_ids.remove(b)
                    continue
                break
            if occ:
                i = min(donors, key=lambda d: min(abs(d - o) for o in occ))
            else:
                i = max(donors, key=lambda d: (cnt[assign[d]], d > 0 and assign[d - 1] != assign[d]))
            assign[i] = b
        else:
            b = over[0]
            occ = [i for i, x in enumerate(assign) if x == b]
            edge = [i for i in occ if (i > 0 and assign[i - 1] != b) or (i + 1 < len(assign) and assign[i + 1] != b)] or occ
            i = edge[-1]
            nbs = [assign[j] for j in (i - 1, i + 1) if 0 <= j < len(assign) and assign[j] != b and cnt[assign[j]] < 4]
            assign[i] = nbs[0] if nbs else min((x for x in bg_ids if x != b), key=lambda x: cnt[x])
    return assign, [b for b in bg_ids if b in set(assign)]


# ------------------------------------------------------------------ numbers spoken in a scene
def spoken_number_at(value: float, tl: _Timeline, a: int, b: int, language: str) -> int | None:
    """Index of the first word where ``value`` is spoken in words a..b, or None."""
    if language != "kk":
        digits = str(int(value)) if float(value).is_integer() else str(value)
        return next((i for i in range(a, b + 1) if digits in tl.words[i]["w"]), None)
    if not float(value).is_integer():
        return None
    target = num_words(int(value)).split()
    toks = [_clean(tl.words[i]["w"]).lower() for i in range(a, b + 1)]
    for s in range(len(toks) - len(target) + 1):
        if all(toks[s + k] == target[k] for k in range(len(target) - 1)) and toks[s + len(target) - 1].startswith(target[-1]):
            return a + s
    return None


# ------------------------------------------------------------------ LLM calls
def _scene_lines(tl: _Timeline, ranges: list[tuple[int, int]], beats: list[str]) -> str:
    return "\n".join(f"S{k + 1} [{beats[a]}] {tl.end(b) - tl.start(a):.1f}s: {tl.text(a, b)}"
                     for k, (a, b) in enumerate(ranges))


def _plan(llm: ILLM, model: str, ctx: CallContext, *, language: str, title: str, tl: _Timeline,
          ranges: list[tuple[int, int]], beats: list[str], poses: list[dict], n_bg: int,
          operator_comments: str | None) -> StoryboardPlanOut:
    p = load_prompt("storyboard_plan")
    prompt = p.render(language_name=LANGUAGE_NAMES.get(language, language), title=title,
                      scene_count=str(len(ranges)), bg_count=str(n_bg),
                      min_uses=str(bg_min_uses(len(ranges), n_bg)),
                      scenes_text=_scene_lines(tl, ranges, beats),
                      poses_json=json.dumps([{"name": x["name"], "tags": x.get("tags", [])} for x in poses],
                                            ensure_ascii=False),
                      hook_poses=" or ".join(poses_with(poses, HOOK_TAGS)[:4]) or poses[0]["name"],
                      max_pose_uses=str(max_pose_uses(len(ranges))),
                      operator_comments=operator_comments or "")
    problems = ""
    for attempt in range(2):  # 1 repair
        out = llm.generate_json(prompt=prompt + problems, response_model=StoryboardPlanOut, model=model,
                                ctx=ctx, max_output_tokens=8000).value
        errs = []
        if abs(len(out.backgrounds) - n_bg) > 2:
            errs.append(f"you returned {len(out.backgrounds)} backgrounds, need exactly {n_bg}")
        missing = set(range(1, len(ranges) + 1)) - {s.id for s in out.scenes}
        if missing:
            errs.append(f"missing scene ids: {sorted(missing)[:20]}")
        if not errs or attempt == 1:
            if errs:
                log.warning("storyboard plan still has problems after repair: %s", errs)
            return out
        problems = "\n\nYour previous answer had problems: " + "; ".join(errs) + ". Return the full corrected JSON."
    raise AssertionError("unreachable")


def _details(llm: ILLM, model: str, ctx: CallContext, *, language: str, title: str, tl: _Timeline,
             scenes: list[dict], phrases: list[list[tuple[int, int]]], bg_prompt: dict[str, str],
             sfx_names: list[str], operator_comments: str | None) -> dict[int, SceneDetailOut]:
    p = load_prompt("storyboard_scenes")
    chunks = [scenes[i:i + CHUNK] for i in range(0, len(scenes), CHUNK)]
    if len(chunks) > 1:  # equal halves read better than 30 + 7
        size = math.ceil(len(scenes) / len(chunks))
        chunks = [scenes[i:i + size] for i in range(0, len(scenes), size)]
    result: dict[int, SceneDetailOut] = {}
    for ci, chunk in enumerate(chunks):
        lines = []
        for sc in chunk:
            a, b = sc["start_word"], sc["end_word"]
            words = " ".join(f"[{i}]{tl.words[i]['w']}" for i in range(a, b + 1))
            ph = ", ".join(f"P{k + 1} {s}-{e}" for k, (s, e) in enumerate(phrases[sc["id"] - 1]))
            lines.append(f"S{sc['id']} [{sc['beat']}] {tl.end(b) - tl.start(a):.1f}s · words {a}-{b} · "
                         f"pose: {sc['character']['pose']} · background: {bg_prompt[sc['background']][:90]}\n"
                         f"  {words}\n  caption phrases: {ph}")
        note = (f"This is part {ci + 1} of {len(chunks)} (scenes {chunk[0]['id']}-{chunk[-1]['id']} of {len(scenes)})."
                if len(chunks) > 1 else "")
        prompt = p.render(language_name=LANGUAGE_NAMES.get(language, language), title=title,
                          scenes_text="\n".join(lines), sfx_names=", ".join(sfx_names),
                          operator_comments=operator_comments or "", chunk_note=note)
        out = llm.generate_json(prompt=prompt, response_model=StoryboardDetailsOut, model=model, ctx=ctx,
                                max_output_tokens=16000).value
        got = {s.id: s for s in out.scenes}
        missing = [sc["id"] for sc in chunk if sc["id"] not in got]
        if missing:
            log.warning("storyboard details: %d scenes missing in part %d (filled by code)", len(missing), ci + 1)
        result.update(got)
    return result


# ------------------------------------------------------------------ assembly + fixes (code)
def _keyword(tl: _Timeline, s: int, e: int, pick: int | None) -> str:
    cands = [pick] if pick is not None and s <= pick <= e else []
    cands += sorted(range(s, e + 1), key=lambda i: -len(_clean(tl.words[i]["w"])))
    phrase = [_clean(tl.words[i]["w"]).lower() for i in range(s, e + 1)]
    for i in cands:
        kw = _clean(tl.words[i]["w"])
        if len(kw) >= 3 and sum(1 for w in phrase if w.startswith(kw.lower())) == 1:
            return kw
    return max((_clean(tl.words[i]["w"]) for i in range(s, e + 1)), key=len)


def _numbers_ok(text: str, tl: _Timeline, a: int, b: int, language: str) -> bool:
    return all(spoken_number_at(float(n), tl, a, b, language) is not None for n in re.findall(r"\d+", text))


def _build_overlays(det: SceneDetailOut | None, tl: _Timeline, a: int, b: int, language: str) -> list[dict]:
    out: list[dict] = []
    last_label_t = -99.0
    slots = iter(TEXT_SLOTS)
    for o in sorted(det.overlays if det else [], key=lambda o: o.at_word):
        at = min(max(o.at_word, a), b)
        item: dict[str, Any] = {"type": o.type, "at_word": at}
        if o.color:
            item["color"] = o.color
        if o.type in ("label", "stamp"):
            text = (o.text or "").strip()
            if (not text or len(text) > 24 or len(text.split()) > 5 or not _numbers_ok(text, tl, a, b, language)
                    or tl.t(at) - last_label_t < 2.0 or sum(x["type"] in ("label", "stamp") for x in out) >= 2):
                log.info("drop %s %r in words %d-%d", o.type, text, a, b)
                continue
            last_label_t = tl.t(at)
            xy = STAMP_XY if o.type == "stamp" else next(slots, None)
            if xy is None:
                continue
            item.update(text=text, x=xy[0], y=xy[1])
        elif o.type == "counter":
            spoken = spoken_number_at(o.value, tl, a, b, language) if o.value is not None else None
            xy = next(slots, None) if spoken is not None else None
            if xy is None:
                log.info("drop counter %r (not spoken in words %d-%d)", o.value, a, b)
                continue
            item.update(at_word=spoken, value=int(o.value) if float(o.value).is_integer() else o.value,
                        x=xy[0], y=xy[1], color=o.color or "yellow")
            if o.suffix and len(o.suffix) <= 8:
                item["suffix"] = o.suffix
        elif o.type == "arrow":
            item.update(x=ARROW[0], y=ARROW[1], x2=ARROW[2], y2=ARROW[3])
        elif o.type == "coins":
            item.update(x=COINS[0], y=COINS[1], x2=COINS[2], y2=COINS[3], count=6)
        elif o.type == "note":
            text = (o.text or "").strip()[:80]
            if not text:
                continue
            item.update(text=text, x=NOTE_XY[0], y=NOTE_XY[1])
        out.append(item)
    return out[:6]


def _events(scene: dict) -> list[int]:
    ev = [o["at_word"] for o in scene.get("overlays", []) if o["type"] != "note"]
    ev += [p["at_word"] for p in (scene.get("character") or {}).get("pose_changes", [])]
    if scene["camera"].get("punch_at_word") is not None:
        ev.append(scene["camera"]["punch_at_word"])
    return sorted(ev)


def _pose_at(scene: dict, word: int) -> str:
    ch = scene["character"]
    pose = ch["pose"]
    for pc in ch.get("pose_changes", []):
        if pc["at_word"] <= word:
            pose = pc["pose"]
    return pose


def _add_filler(scene: dict, word: int, fillers: list[str]) -> bool:
    """Add one visual event at ``word``: punch-in first, then a pose change."""
    cam, ch = scene["camera"], scene["character"]
    if cam.get("punch_at_word") is None:
        cam["punch_at_word"] = word
        return True
    pcs = ch.setdefault("pose_changes", [])
    if len(pcs) >= 4 or any(p["at_word"] == word for p in pcs):
        return False
    cur = _pose_at(scene, word)
    pose = next((p for p in fillers if p != cur), None)
    if pose is None:
        return False
    pcs.append({"at_word": word, "pose": pose})
    pcs.sort(key=lambda p: p["at_word"])
    return True


def _fix_events(scene: dict, tl: _Timeline, fillers: list[str]) -> None:
    """>= 2 events, first <= 0.6 s after the scene start, gaps <= 3 s (video_craft R8)."""
    a, b = scene["start_word"], scene["end_word"]
    st, en = tl.start(a), tl.end(b)
    ev = _events(scene)
    if not ev or tl.t(ev[0]) - st > FIRST_EVENT:
        movable = [o for o in scene["overlays"] if o["type"] in ("label", "arrow", "stamp")]
        if movable:
            movable[0]["at_word"] = a
        else:
            early = next((i for i in range(a + 1, b + 1) if tl.t(i) - st <= FIRST_EVENT), a)
            _add_filler(scene, early, fillers)
    for _ in range(6):
        ev = _events(scene)
        times = [st] + [tl.t(i) for i in ev] + [en + FIRST_EVENT]
        gaps = [(times[k + 1] - times[k], k) for k in range(len(times) - 1)]
        big = max(gaps)
        if len(ev) >= 2 and big[0] <= MAX_EVENT_GAP:
            break
        lo, hi = times[big[1]], times[big[1] + 1]
        mid = (lo + hi) / 2
        cand = [i for i in range(a + 1, b + 1) if i not in ev]
        if not cand or not _add_filler(scene, min(cand, key=lambda i: abs(tl.t(i) - mid)), fillers):
            break


def _add_sfx(scenes: list[dict], dets: dict[int, SceneDetailOut], tl: _Timeline, sfx_names: list[str]) -> None:
    names = set(sfx_names)
    prio = {"whoosh": 0, "pop": 3}
    allsfx: list[tuple[float, int, int, dict]] = []  # (time, priority, scene index, item)
    prev_bg = None
    for k, sc in enumerate(scenes):
        a, b = sc["start_word"], sc["end_word"]
        items: list[dict] = []
        if sc["background"] != prev_bg and "whoosh" in names:
            items.append({"file": "whoosh", "at_word": a})
        prev_bg = sc["background"]
        det = dets.get(sc["id"])
        for s in (det.sfx if det else []):
            if s.file in names and s.file not in ("whoosh", "pop"):
                items.append({"file": s.file, "at_word": min(max(s.at_word, a), b)})
        for o in sc["overlays"]:
            if o["type"] in ("label", "stamp") and "pop" in names:
                items.append({"file": "pop", "at_word": o["at_word"]})
            if o["type"] == "counter" and "ding" in names and not any(i["at_word"] == o["at_word"] for i in items):
                items.append({"file": "ding", "at_word": o["at_word"]})
        for it in items:
            allsfx.append((tl.t(it["at_word"]), prio.get(it["file"], 1), k, it))
    # <= 1 per 0.25 s (keep the higher priority), then cap the rate by dropping pops first
    allsfx.sort(key=lambda x: (x[0], x[1]))
    kept: list[tuple[float, int, int, dict]] = []
    for x in allsfx:
        if kept and x[0] - kept[-1][0] < 0.25:
            if x[1] < kept[-1][1]:
                kept[-1] = x
            continue
        kept.append(x)
    limit = int(SFX_PER_MIN * tl.duration / 60)
    while len(kept) > limit:
        pops = [x for x in kept if x[3]["file"] == "pop"] or [x for x in kept if x[3]["file"] != "whoosh"]
        if not pops:
            break
        kept.remove(pops[len(pops) // 2])
    for sc in scenes:
        sc["sfx"] = []
    for _, _, k, it in kept:
        scenes[k]["sfx"].append(it)


def check_rules(doc: Mapping[str, Any], tl: _Timeline) -> list[str]:
    """Soft rule report (the backend validator is authoritative)."""
    errs: list[str] = []
    cnt = Counter(s["background"] for s in doc["scenes"])
    errs += [f"{b} used {c}x" for b, c in cnt.items() if not 2 <= c <= 4]
    for s in doc["scenes"]:
        d = tl.end(s["end_word"]) - tl.start(s["start_word"])
        ev = _events(s)
        if not (MIN_SCENE - 0.05 <= d <= (HARD_MAX if len(ev) >= 3 else MAX_SCENE) + 0.05):
            errs.append(f"scene {s['id']} {d:.1f}s")
        if len(ev) < 2:
            errs.append(f"scene {s['id']} has {len(ev)} events")
    hook = [s for s in doc["scenes"] if tl.start(s["start_word"]) < HOOK_SECONDS]
    if len(hook) < 4:
        errs.append(f"hook has {len(hook)} scenes")
    return errs


def build_storyboard(llm: ILLM, model: str, script_doc: Mapping[str, Any], words_doc: Mapping[str, Any],
                     poses: list[dict], sfx_names: list[str], *, language: str, ctx: CallContext,
                     operator_comments: str | None = None, n_backgrounds: int = 30) -> dict[str, Any]:
    tl = _Timeline(words_doc)
    pose_names = {p["name"] for p in poses}
    default_pose = (poses_with(poses, DEFAULT_TAGS) or [poses[0]["name"]])[0]
    hook_poses = poses_with(poses, HOOK_TAGS)
    fillers = poses_with(poses, FILLER_TAGS)
    n_scenes = scene_count(tl.duration)
    beats = beat_of_words(script_doc, tl.n)
    ranges = split_scenes(tl, n_scenes, beats)
    n_bg = bg_count(len(ranges), n_backgrounds)
    title = script_doc.get("title", "")

    plan = _plan(llm, model, ctx, language=language, title=title, tl=tl, ranges=ranges, beats=beats,
                 poses=poses, n_bg=n_bg, operator_comments=operator_comments)
    id_map = {b.id: f"bg{k + 1:02d}" for k, b in enumerate(plan.backgrounds[:n_bg + 2])}
    bg_prompt = {id_map[b.id]: b.prompt.strip() for b in plan.backgrounds[:n_bg + 2]}
    by_id = {s.id: s for s in plan.scenes}
    assign, poses_out = [], []
    for k in range(len(ranges)):
        ps = by_id.get(k + 1)
        bg = id_map.get(ps.background) if ps else None
        assign.append(bg or (assign[-1] if assign else next(iter(bg_prompt))))
        pose = ps.pose if ps and ps.pose in pose_names else default_pose
        poses_out.append(pose)
    poses_out = spread_poses(poses_out, poses, max_pose_uses(len(poses_out)))
    if hook_poses and poses_out[0] not in hook_poses:
        poses_out[0] = hook_poses[0]
    assign, _ = balance_backgrounds(assign, list(bg_prompt), bg_min_uses(len(ranges), n_bg))

    # renumber backgrounds bg01.. in order of first use
    order = list(dict.fromkeys(assign))
    ren = {old: f"bg{k + 1:02d}" for k, old in enumerate(order)}
    backgrounds = [{"id": ren[old], "prompt": bg_prompt[old]} for old in order]
    assign = [ren[x] for x in assign]

    phrases = [split_phrases(tl, a, b) for a, b in ranges]
    uses: Counter[str] = Counter()
    scenes: list[dict] = []
    for k, (a, b) in enumerate(ranges):
        occ = uses[assign[k]]
        uses[assign[k]] += 1
        zf, zt = ZOOM[occ % len(ZOOM)]
        fx, fy = FOCUS[occ % len(FOCUS)]
        scenes.append({"id": k + 1, "text": tl.text(a, b), "start_word": a, "end_word": b,
                       "background": assign[k], "beat": beats[a],
                       "camera": {"zoom_from": zf, "zoom_to": zt, "focus": [fx, fy], "punch_at_word": None},
                       "character": {"pose": poses_out[k], **CHAR, "pose_changes": []}})

    dets = _details(llm, model, ctx, language=language, title=title, tl=tl, scenes=scenes, phrases=phrases,
                    bg_prompt={ren[o]: bg_prompt[o] for o in order}, sfx_names=sfx_names,
                    operator_comments=operator_comments)

    for k, sc in enumerate(scenes):
        a, b = sc["start_word"], sc["end_word"]
        det = dets.get(sc["id"])
        ch = sc["character"]
        cur = ch["pose"]
        for pc in sorted(det.pose_changes if det else [], key=lambda p: p.at_word)[:2]:
            if a < pc.at_word <= b and pc.pose in pose_names and pc.pose != cur:
                ch["pose_changes"].append({"at_word": pc.at_word, "pose": pc.pose})
                cur = pc.pose
        if det and det.punch_at_word is not None and a <= det.punch_at_word <= b:
            sc["camera"]["punch_at_word"] = det.punch_at_word
        sc["overlays"] = _build_overlays(det, tl, a, b, language)
        if k == 0:  # hook: number/question label within 0.5 s (video_craft R9)
            first = next((o for o in sc["overlays"] if o["type"] in ("label", "counter")), None)
            if first and first["type"] == "label":
                first["at_word"] = a
        picks = list(det.keywords) if det else []
        caps = []
        for pi, (s, e) in enumerate(phrases[k]):
            pick = next((w for w in picks if s <= w <= e), None)
            caps.append({"start_word": s, "end_word": e, "keyword": _keyword(tl, s, e, pick)})
        sc["captions"] = caps
        sc["caption_keyword"] = caps[0]["keyword"]
        _fix_events(sc, tl, fillers)
        if not ch["pose_changes"]:
            del ch["pose_changes"]

    _add_sfx(scenes, dets, tl, sfx_names)
    doc = {"language": language, "fps": 30, "backgrounds": backgrounds, "scenes": scenes}
    validate_doc("storyboard", doc)
    problems = check_rules(doc, tl)
    if problems:
        log.warning("storyboard rule warnings: %s", problems[:20])
    return doc
