"""In-memory ICostLedger for standalone runs (smoke scripts). The app uses the DB ledger.

Prices mirror the `pricing` seed in supabase/migrations/0001_init.sql (USD; *_tokens per 1M).
Unit keys used by backend/ai: input_tokens, output_tokens (thinking included), search_query,
images + image_size.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Mapping

from app.providers.interfaces import BudgetExceeded, CallContext

# (provider, model) -> list of (effective_from, {unit: usd_per_unit})
PRICES: dict[tuple[str, str], list[tuple[date, dict[str, Decimal]]]] = {
    ("google", "gemini-4-argon"): [
        (date(2026, 10, 16), {"input_tokens": Decimal("2.00"), "output_tokens": Decimal("10.00")}),
        (date(2026, 12, 1), {"input_tokens": Decimal("4.00"), "output_tokens": Decimal("20.00")})],
    ("google", "gemini-3.8-flash"): [
        (date(2026, 10, 16), {"input_tokens": Decimal("0.75"), "output_tokens": Decimal("3.75")}),
        (date(2027, 1, 1), {"input_tokens": Decimal("1.50"), "output_tokens": Decimal("7.50")})],
    ("google", "gemini-3.6-flash"): [
        (date(2026, 10, 16), {"input_tokens": Decimal("0.75"), "output_tokens": Decimal("3.75")}),
        (date(2027, 1, 1), {"input_tokens": Decimal("1.50"), "output_tokens": Decimal("7.50")})],
    ("google", "gemini-3.5-flash-lite"): [
        (date(2026, 10, 16), {"input_tokens": Decimal("0.30"), "output_tokens": Decimal("2.50")})],
    ("google", "gemini-3.1-flash-lite"): [
        (date(2026, 10, 16), {"input_tokens": Decimal("0.25"), "output_tokens": Decimal("1.50")})],
    ("google", "gemini-embedding-2"): [
        (date(2026, 10, 16), {"input_tokens": Decimal("0.20")})],
    ("google", "google_search_grounding"): [
        (date(2026, 10, 16), {"search_query": Decimal("0.014")})],
    ("google", "gemini-nano-banana-2.1"): [
        (date(2026, 10, 16), {"input_tokens": Decimal("1.50"), "image_1K": Decimal("0.0336"),
                              "image_2K": Decimal("0.0504"), "image_4K": Decimal("0.113")})],
    ("google", "gemini-3.1-flash-image"): [
        (date(2026, 10, 16), {"input_tokens": Decimal("0.50"), "image_1K": Decimal("0.067"),
                              "image_2K": Decimal("0.101")})],
    ("anthropic", "claude-code-cli"): [(date(2026, 10, 16), {})],
}
_PER_MILLION = {"input_tokens", "output_tokens"}


@dataclass
class LocalCostLedger:
    budget_usd: Decimal = Decimal("5.00")
    entries: list[dict] = field(default_factory=list)

    def estimate(self, provider: str, model: str, units: Mapping[str, float]) -> Decimal:
        rows = [r for r in PRICES.get((provider, model), []) if r[0] <= date.today()]
        if not rows:
            return Decimal(0)
        prices = max(rows, key=lambda r: r[0])[1]
        usd = Decimal(0)
        if units.get("images"):  # {"images": n, "image_size": "2K"} -> unit image_2K
            usd += prices.get(f"image_{units.get('image_size', '1K')}", Decimal(0)) * Decimal(str(units["images"]))
        for unit, qty in units.items():
            p = prices.get(unit)
            if p is not None:
                usd += p * Decimal(str(qty)) / (Decimal(1_000_000) if unit in _PER_MILLION else 1)
        return usd.quantize(Decimal("0.000001"))

    def guard(self, ctx: CallContext, estimated_usd: Decimal) -> None:
        if self.total() + estimated_usd > self.budget_usd:
            raise BudgetExceeded(f"local budget {self.budget_usd} exceeded")

    def record(self, ctx: CallContext, provider: str, model: str,
               units: Mapping[str, float], tier: str = "standard") -> Decimal:
        usd = self.estimate(provider, model, units)
        self.entries.append({"step": ctx.step, "provider": provider, "model": model,
                             "units": dict(units), "usd": float(usd)})
        return usd

    def total(self) -> Decimal:
        return sum((Decimal(str(e["usd"])) for e in self.entries), Decimal(0))
