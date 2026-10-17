"""Manual run of steps 6 (storyboard), 7 (one background) and 10 (metadata) without the DB.

uv run python -m ai.smoke_p2 --src ../data/_ai_smoke_claude --out ../data/_ai_smoke_p2 [--reuse] [--no-image]

--src must hold script.md (smoke output with the script JSON block) or script.json, facts.json and
tts.txt. words.json is synthesized from tts.txt with proportional timing at --wpm (no audio needed).
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path

from app.config import get_settings
from app.providers.interfaces import CallContext
from ai.factory import build_ai
from ai.local_ledger import LocalCostLedger
from ai.schemas import validate_doc
from ai.storyboard import _Timeline, check_rules


def synth_words(tts_text: str, language: str, wpm: float) -> dict:
    """words.schema.json doc: sentence pauses 0.35 s, paragraph pauses 0.7 s, words by letters+1."""
    words, sentences = [], []
    paras = [p.split() for p in tts_text.split("\n\n") if p.strip()]
    n = sum(len(p) for p in paras)
    n_sent = sum(sum(1 for w in p if re.search(r"[.!?…]$", w)) or 1 for p in paras)
    pause_total = 0.35 * n_sent + 0.35 * len(paras)
    speech = max(n * 60 / wpm - pause_total, n * 0.3)
    per_char = speech / sum(len(re.sub(r"\W", "", w)) + 1 for p in paras for w in p)
    t, s, i = 0.3, 0, 0
    for p in paras:
        sent_start = i
        for k, w in enumerate(p):
            d = (len(re.sub(r"\W", "", w)) + 1) * per_char
            words.append({"i": i, "w": w, "start": round(t, 3), "end": round(t + d, 3), "s": s})
            t += d
            i += 1
            if re.search(r"[.!?…]$", w) or k == len(p) - 1:
                sentences.append({"i": s, "start_word": sent_start, "end_word": i - 1,
                                  "start": words[sent_start]["start"], "end": words[i - 1]["end"], "anchored": True})
                s += 1
                sent_start = i
                t += 0.35
        t += 0.35
    duration = round(t + 0.2, 3)
    return {"language": language, "duration": duration, "aligner": "pause", "words": words,
            "sentences": sentences, "quality": {"anchored_ratio": 1.0, "ok": True,
                                                "wpm_measured": round(n / (duration / 60), 1),
                                                "warnings": ["synthetic timing (smoke)"]}}


def load_script(src: Path) -> dict:
    if (src / "script.json").exists():
        return json.loads((src / "script.json").read_text(encoding="utf-8"))
    md = (src / "script.md").read_text(encoding="utf-8")
    return json.loads(md.split("```json", 1)[1].rsplit("```", 1)[0])


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--wpm", type=float, default=110)
    ap.add_argument("--reuse", action="store_true", help="reuse storyboard.json from --out")
    ap.add_argument("--no-image", action="store_true")
    ap.add_argument("--no-metadata", action="store_true")
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    s = get_settings()
    ledger = LocalCostLedger()
    ai = build_ai(ledger)
    script = load_script(src)
    lang = script["language"]
    facts = json.loads((src / "facts.json").read_text(encoding="utf-8"))
    words = synth_words((src / "tts.txt").read_text(encoding="utf-8"), lang, a.wpm)
    validate_doc("words", words)
    (out / "words.json").write_text(json.dumps(words, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[words] {len(words['words'])} words, {words['duration']} s")
    poses = json.loads((s.library_path / "poses" / "poses.json").read_text(encoding="utf-8"))["poses"]
    sfx = [x["name"] for x in json.loads((s.library_path / "sfx" / "sfx.json").read_text(encoding="utf-8"))["sfx"]]
    t0 = time.time()

    sb_path = out / "storyboard.json"
    if a.reuse and sb_path.exists():
        sb = json.loads(sb_path.read_text(encoding="utf-8"))
    else:
        sb = ai.storyboard(script, words, poses, sfx, language=lang, ctx=CallContext(None, "storyboard"))
        sb_path.write_text(json.dumps(sb, ensure_ascii=False, indent=1), encoding="utf-8")
    validate_doc("storyboard", sb)
    warn = check_rules(sb, _Timeline(words))
    n_ov = sum(len(x.get("overlays", [])) for x in sb["scenes"])
    n_sfx = sum(len(x.get("sfx", [])) for x in sb["scenes"])
    print(f"[storyboard] schema OK · scenes={len(sb['scenes'])} backgrounds={len(sb['backgrounds'])} "
          f"overlays={n_ov} sfx={n_sfx} rule warnings={warn}  ({time.time() - t0:.0f} s)")

    if not a.no_metadata:
        t1 = time.time()
        meta = ai.metadata(script, facts, sb, language=lang, ctx=CallContext(None, "metadata"), words_doc=words)
        (out / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[metadata] schema OK · titles={meta['titles']} chapters={len(meta['chapters'])} "
              f"desc={len(meta['description'])} chars  ({time.time() - t1:.0f} s)")

    if not a.no_image:
        bg = sb["backgrounds"][0]
        r = ai.background_image(bg["prompt"], out / "images" / f"{bg['id']}.png", ctx=CallContext(None, "images"))
        (out / "image_result.json").write_text(json.dumps(r, ensure_ascii=False, indent=1, default=str),
                                               encoding="utf-8")
        print(f"[image] {r}")

    cost = {"total_usd": float(ledger.total()), "seconds": round(time.time() - t0), "entries": ledger.entries}
    (out / "cost.json").write_text(json.dumps(cost, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[done] total ${ledger.total():.4f} -> {out}")


if __name__ == "__main__":
    main()
