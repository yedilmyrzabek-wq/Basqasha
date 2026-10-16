"""Gemini client (google-genai) implementing ILLM: structured JSON, grounding, embeddings,
retries with backoff, cost ledger per call, model fallback when a model is not available
on the key's tier (e.g. free tier: gemini-4-argon and Search grounding have limit 0)."""
from __future__ import annotations

import logging
import re
import time
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Sequence, TypeVar

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from app.providers.interfaces import BudgetExceeded, CallContext, ICostLedger, LLMResult

log = logging.getLogger("ai.gemini")
M = TypeVar("M", bound=BaseModel)
R = TypeVar("R")

EMBED_PREFIX = "task: sentence similarity | query: "
MAX_OUT = {"gemini-4-argon": 20_000}  # tools_costs R7; everything else 16k
_RETRY_IN = re.compile(r"retry in (?:(\d+)h)?(?:(\d+)m)?([\d.]+)s", re.I)
_BACKOFF = (2.0, 6.0, 18.0)


class ModelUnavailable(Exception):
    """Model (or tool) is not usable with this API key: free-tier limit 0, quota exhausted
    for hours, model not found. Not retryable; callers may fall back to another model."""


class GroundingUnavailable(ModelUnavailable):
    """Google Search grounding refused (free tier / quota). Facts step uses its doc fallback."""


def _classify(e: errors.APIError) -> tuple[str, float]:
    """-> (kind, delay): kind in budget | unavailable | transient | fatal."""
    msg = str(e).lower()
    if e.code == 402 or "spending cap" in msg or "spend cap" in msg or "prepaid" in msg:
        return "budget", 0
    if e.code == 429:
        m = _RETRY_IN.search(msg)
        delay = (int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + float(m.group(3))) if m else 0
        if "limit: 0" in msg or (delay == 0 and "quota" in msg) or delay > 90:
            return "unavailable", 0
        return "transient", max(delay, 2.0)
    if e.code == 404:
        return "unavailable", 0
    if e.code in (500, 502, 503, 504):
        return "transient", 0
    return "fatal", 0


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    return t


class GeminiLLM:
    """ILLM implementation. ``fallbacks`` maps model -> model to use when the first is unavailable
    or keeps failing (e.g. {"gemini-4-argon": "gemini-3.8-flash"})."""

    def __init__(self, api_key: str, ledger: ICostLedger, fallbacks: dict[str, str] | None = None):
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=600_000,
                                           retry_options=types.HttpRetryOptions(attempts=1)))
        self.ledger = ledger
        self.fallbacks = fallbacks or {}
        self.unavailable: set[str] = set()  # models refused for this key in this process (skip to fallback)

    # ------------------------------------------------------------ helpers
    def list_model_ids(self) -> set[str]:
        return {m.name.removeprefix("models/") for m in self.client.models.list()}

    def _with_retries(self, fn: Callable[[], R], *, grounding: bool = False) -> R:
        for attempt in range(len(_BACKOFF) + 1):
            try:
                return fn()
            except errors.APIError as e:
                kind, delay = _classify(e)
                if kind == "budget":
                    raise BudgetExceeded(f"Gemini: {e.code} {e.status}") from e
                if kind == "unavailable":
                    cls = GroundingUnavailable if grounding else ModelUnavailable
                    raise cls(f"{e.code} {e.status}: {str(e)[:1500]}") from e
                if kind == "fatal" or attempt == len(_BACKOFF):
                    if kind == "transient":
                        raise ModelUnavailable(f"still failing after retries: {e.code} {e.status}") from e
                    raise
                wait = max(delay, _BACKOFF[attempt])
                log.warning("Gemini %s %s, retry in %.0fs", e.code, e.status, wait)
                time.sleep(wait)
        raise AssertionError("unreachable")

    def _record(self, ctx: CallContext, model: str, resp: Any) -> dict[str, int]:
        u = resp.usage_metadata
        usage = {
            "input_tokens": (u.prompt_token_count or 0) + (u.tool_use_prompt_token_count or 0) if u else 0,
            "output_tokens": (u.candidates_token_count or 0) if u else 0,
            "thinking_tokens": (u.thoughts_token_count or 0) if u else 0,
        }
        self.ledger.record(ctx, "google", model, {
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"] + usage["thinking_tokens"]})
        gm = resp.candidates[0].grounding_metadata if resp.candidates else None
        if gm and gm.web_search_queries:
            self.ledger.record(ctx, "google", "google_search_grounding",
                               {"search_query": len(gm.web_search_queries)})
        return usage

    def _guard(self, ctx: CallContext, model: str, prompt_chars: int, max_out: int) -> None:
        est = self.ledger.estimate("google", model, {"input_tokens": prompt_chars / 3,
                                                     "output_tokens": max_out})
        self.ledger.guard(ctx, est)

    @staticmethod
    def _grounding_urls(resp: Any) -> tuple[str, ...]:
        gm = resp.candidates[0].grounding_metadata if resp.candidates else None
        if not gm or not gm.grounding_chunks:
            return ()
        return tuple(c.web.uri for c in gm.grounding_chunks if c.web and c.web.uri)

    # ------------------------------------------------------------ ILLM
    def generate_json(self, *, prompt: str, response_model: type[M], model: str, ctx: CallContext,
                      system: str | None = None, grounding: bool = False,
                      images: Sequence[Path] = (), max_output_tokens: int | None = None) -> LLMResult[M]:
        # Follow the fallback chain (free-tier quotas are per model, e.g. 20 requests/day).
        tried: set[str] = set()
        while True:
            tried.add(model)
            fb = self.fallbacks.get(model)
            if model in self.unavailable and fb and fb not in tried:
                model = fb
                continue
            try:
                return self._generate_json(prompt, response_model, model, ctx, system, grounding,
                                           images, max_output_tokens)
            except GroundingUnavailable:
                raise
            except ModelUnavailable as e:
                self.unavailable.add(model)  # refused for this key (tier/daily quota): skip for this process
                if not fb or fb in tried:
                    raise
                log.warning("model %s unavailable (%s) -> fallback %s", model, str(e)[:200], fb)
                model = fb

    def _generate_json(self, prompt: str, response_model: type[M], model: str, ctx: CallContext,
                       system: str | None, grounding: bool, images: Sequence[Path],
                       max_output_tokens: int | None) -> LLMResult[M]:
        max_out = min(max_output_tokens or MAX_OUT.get(model, 16_000), MAX_OUT.get(model, 16_000))
        self._guard(ctx, model, len(prompt), max_out)
        parts: list[Any] = [types.Part.from_bytes(data=p.read_bytes(), mime_type=_mime(p)) for p in images]
        parts.append(prompt)
        cfg = types.GenerateContentConfig(
            system_instruction=system, max_output_tokens=max_out,
            response_mime_type="application/json", response_schema=response_model,
            tools=[types.Tool(google_search=types.GoogleSearch())] if grounding else None)

        usage_total = {"input_tokens": 0, "output_tokens": 0, "thinking_tokens": 0}
        contents: list[Any] = parts
        for attempt in range(2):  # 1 JSON-repair retry (tools_costs R7)
            resp = self._with_retries(
                lambda: self.client.models.generate_content(model=model, contents=contents, config=cfg),
                grounding=grounding)
            for k, v in self._record(ctx, model, resp).items():
                usage_total[k] += v
            text = resp.text or ""
            try:
                value = resp.parsed if isinstance(resp.parsed, response_model) else \
                    response_model.model_validate_json(_strip_fences(text))
                return LLMResult(value=value, model=model, usage=usage_total,
                                 grounding_urls=self._grounding_urls(resp))
            except ValidationError as ve:
                if attempt == 1:
                    raise
                log.warning("invalid JSON from %s, repair retry: %s", model, str(ve)[:200])
                contents = parts + [f"\n\nYour previous answer was not valid for the schema:\n{str(ve)[:1500]}\n"
                                    f"Previous answer:\n{text[:6000]}\n\nReturn corrected JSON only."]
        raise AssertionError("unreachable")

    def embed(self, texts: Sequence[str], *, model: str, ctx: CallContext, dim: int = 768) -> list[list[float]]:
        out: list[list[float]] = []
        chars = sum(len(t) for t in texts)
        self.ledger.guard(ctx, self.ledger.estimate("google", model, {"input_tokens": chars / 2}))
        for i in range(0, len(texts), 100):
            # gemini-embedding-2 merges a list of plain strings into ONE embedding; wrap each text
            # in its own Content to get one vector per text.
            batch = [types.Content(parts=[types.Part(text=EMBED_PREFIX + t)]) for t in texts[i:i + 100]]
            resp = self._with_retries(lambda: self.client.models.embed_content(
                model=model, contents=batch, config=types.EmbedContentConfig(output_dimensionality=dim)))
            if len(resp.embeddings) != len(batch):
                raise RuntimeError(f"embed: got {len(resp.embeddings)} vectors for {len(batch)} texts")
            out.extend(list(e.values) for e in resp.embeddings)
        # The Gemini API returns no token count for embeddings: estimate ~2.5 chars/token (Cyrillic-heavy).
        self.ledger.record(ctx, "google", model, {"input_tokens": round(chars / 2.5)})
        return out


def _mime(p: Path) -> str:
    return {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}.get(
        p.suffix.lower(), "application/octet-stream")


def usd(ledger: ICostLedger) -> Decimal | None:
    """Total spent, when the ledger can tell (LocalCostLedger)."""
    total = getattr(ledger, "total", None)
    return total() if callable(total) else None
