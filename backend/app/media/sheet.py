"""Contact sheet (Pillow grid of the mid-scene stills) and the font glyph check (fontTools)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from app.config import get_settings

COLS = 4
TILE = (480, 270)
PAD = 12
LABEL_H = 34
PAPER = (246, 241, 231)
INK = (34, 30, 28)


def _font_dir() -> Path:
    return get_settings().engine_path / "public" / "fonts"


def _font(size: int) -> ImageFont.ImageFont:
    fonts = sorted(_font_dir().glob("Inter*.ttf"))
    try:
        return ImageFont.truetype(str(fonts[0]), size) if fonts else ImageFont.load_default()
    except OSError:
        return ImageFont.load_default()


def contact_sheet(tiles: list[tuple[int, Path, str]], out: Path) -> Path:
    """tiles = [(scene_id, png, caption)] -> grid PNG with the scene number and time on each tile."""
    rows = (len(tiles) + COLS - 1) // COLS
    w = COLS * TILE[0] + (COLS + 1) * PAD
    h = rows * (TILE[1] + LABEL_H) + (rows + 1) * PAD
    sheet = Image.new("RGB", (w, h), PAPER)
    draw = ImageDraw.Draw(sheet)
    font, small = _font(22), _font(18)
    for k, (sid, png, cap) in enumerate(tiles):
        x = PAD + (k % COLS) * (TILE[0] + PAD)
        y = PAD + (k // COLS) * (TILE[1] + LABEL_H + PAD)
        with Image.open(png) as im:
            sheet.paste(im.convert("RGB").resize(TILE, Image.LANCZOS), (x, y))
        draw.rectangle([x, y, x + 54, y + 34], fill=INK)
        draw.text((x + 8, y + 4), f"{sid:02d}", fill=PAPER, font=font)
        draw.text((x + 2, y + TILE[1] + 6), cap[:60], fill=INK, font=small)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, optimize=True)
    return out


@lru_cache
def _cmap(prefix: str) -> frozenset[int]:
    from fontTools.ttLib import TTFont

    fonts = sorted(_font_dir().glob(f"{prefix}*.ttf"))
    if not fonts:
        return frozenset()
    with TTFont(str(fonts[0]), lazy=True) as f:
        return frozenset(f.getBestCmap().keys())


def missing_glyphs(props: dict[str, Any]) -> list[str]:
    """Characters of on-screen text not covered by the engine fonts (Inter: captions/labels/notes,
    Rubik: counters/stamps). Empty list = OK."""
    texts: list[tuple[str, str]] = [(c["text"], "Inter") for c in props["captions"]]
    for s in props["scenes"]:
        for o in s.get("overlays", []):
            font = "Rubik" if o["type"] in ("counter", "stamp") else "Inter"
            for k in ("text", "prefix", "suffix"):
                if o.get(k):
                    v = str(o[k])
                    texts.append((v.upper() if o["type"] == "stamp" else v, font))
    miss: set[str] = set()
    for text, font in texts:
        cmap = _cmap(font)
        if not cmap:
            continue
        miss.update(ch for ch in text if not ch.isspace() and ord(ch) not in cmap)
    return sorted(miss)
