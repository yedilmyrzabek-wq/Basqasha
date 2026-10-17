"""ICostLedger implementation: pricing lookup (latest effective_from <= today), budget guard,
cost_entry insert. Each call uses its own short transaction so spend is recorded even if the
step later fails."""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Mapping

from sqlalchemy import func, select

from app import app_settings, cancel
from app.db import session_scope
from app.models import CostEntry, JobLog, Pricing, Project
from app.providers.interfaces import BudgetExceeded, CallContext

log = logging.getLogger(__name__)

PROVIDER_ALIASES = {"gemini": "google", "google_genai": "google", "google-genai": "google", "claude": "anthropic"}
GROUNDING_FREE_PER_MONTH = 5000
M = Decimal(1_000_000)


def _provider(p: str) -> str:
    return PROVIDER_ALIASES.get(p.lower(), p.lower())


def _month_start() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class CostLedger:
    def _price(self, db, provider: str, model: str, unit: str) -> Decimal | None:
        row = db.scalar(
            select(Pricing.usd_per_unit)
            .where(Pricing.provider == provider, Pricing.model == model, Pricing.unit == unit,
                   Pricing.effective_from <= date.today())
            .order_by(Pricing.effective_from.desc()).limit(1))
        return Decimal(row) if row is not None else None

    def _compute(self, db, provider: str, model: str, units: Mapping[str, float]) -> tuple[Decimal, list[str]]:
        provider = _provider(provider)
        if provider == "anthropic":
            return Decimal(0), []
        usd, missing = Decimal(0), []

        def add(unit: str, qty: Decimal, mdl: str = model) -> None:
            nonlocal usd
            if qty <= 0:
                return
            price = self._price(db, provider, mdl, unit)
            if price is None:
                missing.append(f"{provider}/{mdl}/{unit}")
            else:
                usd += price * qty

        inp = Decimal(str(units.get("input_tokens", 0) or 0))
        out = Decimal(str((units.get("output_tokens", 0) or 0) + (units.get("thinking_tokens", 0) or 0)))
        add("1M_input_tokens", inp / M)
        add("1M_output_tokens", out / M)

        images = Decimal(str(units.get("images", 0) or 0))
        if images:
            size = str(units.get("image_size", "1K"))
            unit = f"image_{size}"
            if self._price(db, provider, model, unit) is None and size in ("1K", "2K"):
                unit = "image_1K_2K"
            add(unit, images)

        queries = int(units.get("search_queries", 0) or units.get("search_query", 0) or 0)
        if queries:
            used = db.scalar(
                select(func.coalesce(func.sum(CostEntry.units["search_queries"].as_float()), 0))
                .where(CostEntry.created_at >= _month_start())) or 0
            billable = max(0, queries - max(0, GROUNDING_FREE_PER_MONTH - int(used)))
            add("search_query", Decimal(billable), "google_search_grounding")
        return usd.quantize(Decimal("0.000001")), missing

    # ------------------------------------------------------------- ICostLedger
    def estimate(self, provider: str, model: str, units: Mapping[str, float]) -> Decimal:
        with session_scope() as db:
            return self._compute(db, provider, model, units)[0]

    def guard(self, ctx: CallContext, estimated_usd: Decimal) -> None:
        est = Decimal(str(estimated_usd))
        with session_scope() as db:
            cfg = app_settings.load(db)
            month = db.scalar(select(func.coalesce(func.sum(CostEntry.usd), 0))
                              .where(CostEntry.created_at >= _month_start())) or Decimal(0)
            stop = Decimal(str(cfg["budget_month_stop_usd"]))
            if month + est >= stop:
                raise BudgetExceeded(f"Monthly stop ${stop}: spent ${month:.2f} + estimate ${est:.4f}")
            if ctx.project_id is not None:
                p = db.get(Project, ctx.project_id)
                if p is not None and Decimal(p.cost_usd) + est > Decimal(p.budget_usd):
                    raise BudgetExceeded(
                        f"Project budget ${p.budget_usd}: spent ${Decimal(p.cost_usd):.4f} + estimate ${est:.4f}")

    def record(self, ctx: CallContext, provider: str, model: str,
               units: Mapping[str, float], tier: str = "standard") -> Decimal:
        with session_scope() as db:
            usd, missing = self._compute(db, provider, model, units)
            if tier in ("batch", "flex"):
                usd = (usd / 2).quantize(Decimal("0.000001"))
            db.add(CostEntry(project_id=ctx.project_id, step=ctx.step, provider=_provider(provider),
                             model=model, tier=tier, units=dict(units), usd=usd))
            if missing:
                db.add(JobLog(project_id=ctx.project_id, step=ctx.step, level="warning",
                              message=f"No pricing row for {', '.join(missing)}; recorded without it"))
        cancel.check()  # «Остановить»: checkpoint after every paid / AI call, once the spend is committed
        return usd


ledger = CostLedger()
