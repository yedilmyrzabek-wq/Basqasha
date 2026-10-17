"""Step 7: background images. GeminiImageProvider (IImageProvider, one attempt) + the
generate -> vision QA -> retry loop (max 3 attempts, tools_costs R3).

Quota / free tier (HTTP 429, "limit: 0") or a missing key -> qa_status "needs_manual" at once
(the operator uploads an image from Flow); spend cap / 402 -> BudgetExceeded.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Sequence

from google.genai import errors, types

from app.providers.interfaces import (BudgetExceeded, CallContext, GeneratedImage, ICostLedger, ILLM,
                                      ImageRequest)
from ai.gemini import GeminiLLM, ModelUnavailable, _mime
from ai.prompts import load_prompt
from ai.schemas import ImageQAOut

log = logging.getLogger("ai.images")
MAX_ATTEMPTS = 3
MAX_REFS = 3
_PNG = b"\x89PNG"


class ImageQuotaError(Exception):
    """The image model is not usable with this key right now (429 / free tier / not found)."""


def _size(data: bytes) -> tuple[int, int]:
    if data.startswith(_PNG) and len(data) >= 24:
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    return 0, 0


class GeminiImageProvider:
    kind = "gemini"

    def __init__(self, gemini: GeminiLLM, ledger: ICostLedger, model: str):
        self.client = gemini.client
        self.ledger = ledger
        self.model = model

    def generate(self, req: ImageRequest, ctx: CallContext) -> GeneratedImage:
        units = {"images": 1, "image_size": req.image_size}
        self.ledger.guard(ctx, self.ledger.estimate("google", self.model, units))
        parts: list[Any] = [types.Part.from_bytes(data=p.read_bytes(), mime_type=_mime(p))
                            for p in req.reference_images]
        refs = (" Match the drawing style, line weight and palette of the reference images; "
                "do not copy their objects.") if req.reference_images else ""
        parts.append(f"{req.prompt.strip()} {req.style_suffix.strip()}{refs}")
        cfg = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=req.aspect_ratio, image_size=req.image_size))
        resp = None
        for attempt in range(2):  # one retry on 5xx only
            try:
                resp = self.client.models.generate_content(model=self.model, contents=parts, config=cfg)
                break
            except errors.APIError as e:
                msg = str(e).lower()
                if e.code == 402 or "spend cap" in msg or "spending cap" in msg or "prepaid" in msg:
                    raise BudgetExceeded(f"Gemini image: {e.code} {e.status}") from e
                if e.code in (500, 502, 503, 504) and attempt == 0:
                    time.sleep(5)
                    continue
                if e.code in (429, 403, 404) or "quota" in msg:
                    raise ImageQuotaError(f"{e.code} {e.status}: {str(e)[:300]}") from e
                raise
        u = resp.usage_metadata if resp else None
        rec = dict(units)
        if u:
            rec["input_tokens"] = u.prompt_token_count or 0
            rec["thinking_tokens"] = u.thoughts_token_count or 0
        self.ledger.record(ctx, "google", self.model, rec)
        data, mime = None, ""
        for cand in (resp.candidates or []) if resp else []:
            for part in (cand.content.parts if cand.content else None) or []:
                if part.inline_data and part.inline_data.data:
                    data, mime = part.inline_data.data, part.inline_data.mime_type or ""
                    break
            if data:
                break
        if not data:
            reason = resp.candidates[0].finish_reason if resp and resp.candidates else "no candidates"
            raise RuntimeError(f"no image in response ({reason})")
        out = req.out_path
        out.parent.mkdir(parents=True, exist_ok=True)
        if data.startswith(_PNG):
            out.write_bytes(data)
        elif _to_png(data, out) is None:  # no Pillow: keep the original format
            out = out.with_suffix(".jpg" if "jpeg" in mime else ".webp" if "webp" in mime else ".img")
            out.write_bytes(data)
        w, h = _size(out.read_bytes()[:32])
        return GeneratedImage(path=out, width=w, height=h, model=self.model)


def _to_png(data: bytes, out: Path) -> Path | None:
    """Convert to PNG with Pillow when it is installed; None otherwise."""
    try:
        import io

        from PIL import Image
    except ImportError:
        return None
    Image.open(io.BytesIO(data)).save(out, "PNG")
    return out


def qa_image(llm: ILLM, image: Path, prompt: str, refs: Sequence[Path], *, model: str,
             ctx: CallContext) -> ImageQAOut:
    p = load_prompt("image_qa")
    note = (f"The next {len(refs)} image(s) are style references of the channel." if refs else
            "There are no reference images.")
    return llm.generate_json(prompt=p.render(prompt=prompt, has_refs=note), response_model=ImageQAOut,
                             model=model, ctx=ctx, images=[image, *refs], max_output_tokens=1000).value


def generate_background(provider: GeminiImageProvider, llm: ILLM, prompt: str, out_path: Path, *,
                        style_suffix: str, style_refs: Sequence[Path], qa_model: str,
                        ctx: CallContext, image_size: str = "2K") -> dict[str, Any]:
    refs = list(style_refs)[:MAX_REFS]
    notes: list[str] = []
    extra = ""
    result: dict[str, Any] = {"path": None, "model": provider.model, "qa_status": "needs_manual",
                              "qa_notes": "", "attempts": 0, "is_photoreal": False, "depicts_real_person": False}
    for attempt in range(1, MAX_ATTEMPTS + 1):
        result["attempts"] = attempt
        req = ImageRequest(slot=out_path.stem, prompt=prompt + extra, out_path=out_path,
                           style_suffix=style_suffix, reference_images=refs, image_size=image_size)
        try:
            img = provider.generate(req, ctx)
        except ImageQuotaError as e:
            notes.append(f"image model unavailable: {e}")
            break
        except RuntimeError as e:  # blocked / empty response: try again with the same prompt
            notes.append(f"attempt {attempt}: {e}")
            continue
        result.update(path=img.path, width=img.width, height=img.height)
        try:
            qa = qa_image(llm, img.path, prompt, refs[:1], model=qa_model, ctx=ctx)
        except ModelUnavailable as e:
            notes.append(f"vision QA unavailable ({str(e)[:120]}); review manually")
            result["qa_status"] = "needs_manual"
            break
        result["is_photoreal"] = qa.is_photoreal
        if not (qa.has_text or qa.has_people or not qa.style_match or qa.is_photoreal):
            result["qa_status"] = "ok"
            notes.append(f"attempt {attempt}: ok")
            break
        problems = [k for k, bad in (("text/letters", qa.has_text), ("people", qa.has_people),
                                     ("style mismatch", not qa.style_match), ("photoreal", qa.is_photoreal)) if bad]
        notes.append(f"attempt {attempt}: {', '.join(problems)} — {qa.notes}")
        result["qa_status"] = "failed"
        extra = (f" IMPORTANT: the previous image had {', '.join(problems)} ({qa.notes}). "
                 "Absolutely no text, letters, numbers or people.")
    result["qa_notes"] = " | ".join(notes)
    if result["path"] is not None:
        result["path"] = Path(result["path"])
    return result
