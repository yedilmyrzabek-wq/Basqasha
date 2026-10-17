"""FastAPI app: `uv run uvicorn app.main:app` from backend/."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError

from app import app_settings
from app.api.routers import content, growth, media, ops, production, projects, source
from app.config import get_settings
from app.db import session_scope
from app.pipeline import steps  # noqa: F401 - registers step handlers
from app.pipeline.orchestrator import StepConflict
from app.providers.interfaces import BudgetExceeded

cfg = get_settings()
logging.basicConfig(level=cfg.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("basqasha")

app = FastAPI(title="Basqasha local API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://localhost:{cfg.frontend_port}", f"http://127.0.0.1:{cfg.frontend_port}"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

for r in (projects.router, source.router, content.router, media.router, production.router, ops.router,
          growth.router):
    app.include_router(r)

cfg.data_path.mkdir(parents=True, exist_ok=True)
app.mount("/files/data", StaticFiles(directory=cfg.data_path, check_dir=False), name="data")
app.mount("/files/library", StaticFiles(directory=cfg.library_path, check_dir=False), name="library")


@app.middleware("http")
async def _download(request: Request, call_next):
    """/files/...?download=1 -> Content-Disposition: attachment («Скачать» in the UI)."""
    response = await call_next(request)
    if request.url.path.startswith("/files/") and request.query_params.get("download") == "1":
        name = request.url.path.rsplit("/", 1)[-1]
        response.headers["Content-Disposition"] = f'attachment; filename="{name}"'
    return response


@app.exception_handler(StepConflict)
async def _conflict(_: Request, e: StepConflict):
    return JSONResponse({"detail": str(e)}, status_code=409)


@app.exception_handler(BudgetExceeded)
async def _budget(_: Request, e: BudgetExceeded):
    return JSONResponse({"detail": str(e)}, status_code=409)


@app.exception_handler(OperationalError)
async def _db_down(_: Request, e: OperationalError):
    log.error("DB error: %s", str(e).splitlines()[0][:300])
    return JSONResponse({"detail": "Database unreachable. " + ops.DB_HINT}, status_code=503)


@app.on_event("startup")
def _startup() -> None:
    """Keep-alive ping + settings seed. A paused Supabase must not stop the app from starting."""
    try:
        with session_scope() as db:
            app_settings.load(db)
        log.info("DB ok; settings loaded")
    except Exception as e:  # noqa: BLE001
        log.error("DB unreachable at startup (%s). %s", type(e).__name__, ops.DB_HINT)
