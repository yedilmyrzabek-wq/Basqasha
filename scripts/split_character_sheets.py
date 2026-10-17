"""Split character sheets (figures on a plain light background) into transparent pose PNGs.

uv run --with scipy python scripts/split_character_sheets.py

Background = pixels close to the border colour AND connected to the border, so white faces/hands
inside the dark outline stay opaque. Small bits (question marks, light bulbs, motion lines) are
attached to the nearest figure. Names come from SHEETS (left→right, top→bottom).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "incoming" / "character"
POSES = ROOT / "library" / "poses"
BUSTS = ROOT / "library" / "character" / "expressions"

# name, tags — in reading order. kind "pose" = full body (feet at bottom), "bust" = head+shoulders.
SHEETS: dict[str, tuple[str, list[tuple[str, list[str]]]]] = {
    "reference_sheet.jpg": ("pose", [
        ("neutral", ["neutral", "default", "explain"]),
        ("side_view", ["side", "walk_in"]),
        ("three_quarter", ["neutral", "listen"]),
        ("back_view", ["back", "look_away"]),
        ("wave_hello", ["hello", "intro", "outro", "happy"]),
    ]),
    "pose_grid_b.jpg": ("pose", [
        ("walk", ["walk", "journey", "neutral"]),
        ("run_determined", ["run", "hurry", "determined", "discipline"]),
        ("jump_joy", ["jump", "joy", "success", "payoff"]),
        ("sit_chair", ["sit", "wait", "calm"]),
        ("meditate", ["calm", "focus", "mindfulness"]),
        ("sleep_lying", ["sleep", "rest", "tired"]),
        ("fall_surprised", ["fall", "fail", "surprise", "shock"]),
        ("cheer_arms_up", ["cheer", "win", "excited", "payoff"]),
    ]),
    "expr_sheet_9.jpg": ("pose", [
        ("think_chin", ["think", "question", "curious"]),
        ("worried_scratch_head", ["worried", "unsure", "problem"]),
        ("confused_shrug", ["confused", "shrug", "why"]),
        ("facepalm", ["facepalm", "mistake", "fail"]),
        ("idea_lightbulb", ["idea", "insight", "solution"]),
    ]),
    "pose_grid_a.jpg": ("pose", [
        ("read_book", ["read", "study", "learn", "research"]),
        ("laptop_work", ["work", "computer", "study"]),
        ("phone_scroll", ["phone", "distraction", "social_media"]),
        ("money_cash", ["money", "price", "rich"]),
        ("shrug_smile", ["shrug", "explain", "so_what"]),
        ("present_whiteboard", ["teach", "explain", "plan", "list"]),
        ("magnify_search", ["search", "investigate", "research"]),
        ("drink_tea", ["tea", "break", "calm"]),
        ("drink_tea_relaxed", ["tea", "relax", "rest"]),
        ("carry_box_heavy", ["heavy", "burden", "effort", "struggle"]),
    ]),
    "still_confused.jpg": ("pose", [
        ("puzzled", ["puzzled", "skeptical", "neutral"]),
        ("unsure", ["unsure", "doubt", "sad"]),
        ("scratch_head_skeptical", ["skeptical", "think", "doubt"]),
        ("explain_open_hand", ["explain", "surprised", "point"]),
        ("confused_questions", ["confused", "question", "why"]),
    ]),
    "still_celebrate.jpg": ("pose", [
        ("happy_dance", ["happy", "dance", "fun"]),
        ("jump_fist_pump", ["win", "yes", "excited"]),
        ("jump_cheer", ["joy", "excited", "payoff"]),
        ("happy_step", ["happy", "walk", "fun"]),
        ("wave_smile", ["hello", "goodbye", "outro"]),
    ]),
    "expr_sheet_b.jpg": ("bust", [
        ("happy_wave", ["happy", "hello"]),
        ("laugh", ["laugh", "joy"]),
        ("surprised", ["surprise", "wow"]),
        ("shock_scared", ["shock", "fear"]),
        ("angry_fist", ["angry", "frustrated"]),
        ("angry", ["angry", "serious"]),
        ("panic", ["panic", "stress", "anxiety"]),
        ("sad", ["sad", "disappointed"]),
        ("confused_question", ["confused", "question"]),
        ("bored", ["bored", "lazy", "procrastination"]),
    ]),
}


# standing pose per sheet = scale 1.0; other poses keep their size relative to it (lying is shorter,
# arms-up is taller), so the engine draws every pose at the same body scale.
STANDING = {"reference_sheet.jpg": "neutral", "pose_grid_b.jpg": "walk", "expr_sheet_9.jpg": "think_chin",
            "pose_grid_a.jpg": "shrug_smile", "still_confused.jpg": "puzzled", "still_celebrate.jpg": "wave_smile"}


def extract(img: Image.Image, expected: int) -> list[Image.Image]:
    rgb = np.asarray(img.convert("RGB")).astype(np.int32)
    h, w, _ = rgb.shape
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]])
    bg = np.median(border, axis=0)
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
    # light, low-contrast pixels = paper or ground shadow; dark outlines stop the flood
    close = dist < 75
    lab, _ = ndimage.label(close)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bgmask = np.isin(lab, edge[edge > 0])
    fg = ~bgmask
    fg = ndimage.binary_opening(fg, iterations=1)

    comps, n = ndimage.label(fg, structure=np.ones((3, 3)))
    areas = ndimage.sum(fg, comps, range(1, n + 1))
    boxes = ndimage.find_objects(comps)
    order = np.argsort(-areas)
    big = [int(i) for i in order[:expected]]
    small_min = 30
    groups: dict[int, list[int]] = {b: [b] for b in big}
    for i in range(n):
        if i in groups or areas[i] < small_min:
            continue
        cy = (boxes[i][0].start + boxes[i][0].stop) / 2
        cx = (boxes[i][1].start + boxes[i][1].stop) / 2

        def gap(b: int) -> float:
            ys, xs = boxes[b]
            dy = max(ys.start - cy, 0, cy - ys.stop)
            dx = max(xs.start - cx, 0, cx - xs.stop)
            return float(np.hypot(dx, dy))
        nearest = min(big, key=gap)
        if gap(nearest) < 0.08 * w:
            groups[nearest].append(i)

    rgba = np.dstack([rgb.astype(np.uint8), np.zeros((h, w), np.uint8)])
    figs = []
    for b, members in groups.items():
        m = np.isin(comps, [k + 1 for k in members])
        ys, xs = np.where(m)
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        crop = rgba[y0:y1, x0:x1].copy()
        crop[..., 3] = (m[y0:y1, x0:x1] * 255).astype(np.uint8)
        # soften the 1-px alpha edge a little
        a = Image.fromarray(crop[..., 3]).filter(__import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(0.6))
        crop[..., 3] = np.asarray(a)
        figs.append(((y0 + y1) / 2, (x0 + x1) / 2, y1 - y0, Image.fromarray(crop, "RGBA")))

    # reading order: rows by centre-y (row break when the jump is > 1/4 of the typical figure height)
    figs.sort(key=lambda f: f[0])
    typical = float(np.median([f[2] for f in figs]))
    rows: list[list] = []
    for f in figs:
        if rows and abs(f[0] - np.mean([g[0] for g in rows[-1]])) < typical * 0.5:
            rows[-1].append(f)
        else:
            rows.append([f])
    out = []
    for r in rows:
        out += [f[3] for f in sorted(r, key=lambda f: f[1])]
    return out


def main() -> None:
    POSES.mkdir(parents=True, exist_ok=True)
    BUSTS.mkdir(parents=True, exist_ok=True)
    poses, busts = [], []
    for sheet, (kind, names) in SHEETS.items():
        figs = extract(Image.open(SRC / sheet), len(names))
        if len(figs) != len(names):
            print(f"!! {sheet}: found {len(figs)} figures, expected {len(names)}")
        ref_h = None
        if sheet in STANDING:
            ref_h = next(im.height for (n, _), im in zip(names, figs) if n == STANDING[sheet])
        for (name, tags), im in zip(names, figs):
            target = POSES if kind == "pose" else BUSTS
            fname = f"{name}.png"
            im.save(target / fname, optimize=True)
            row = {"name": name, "file": fname, "tags": tags, "width": im.width, "height": im.height,
                   "scale": round(im.height / ref_h, 3) if ref_h else 1.0, "source": sheet}
            (poses if kind == "pose" else busts).append(row)
            print(f"{kind:4} {name:24} {im.width}x{im.height} scale={row['scale']}")
    (POSES / "poses.json").write_text(json.dumps({"character": "kalpak_stickman", "poses": poses},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    (BUSTS / "expressions.json").write_text(json.dumps({"expressions": busts}, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    print(f"{len(poses)} poses, {len(busts)} busts")


if __name__ == "__main__":
    main()
