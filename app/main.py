import logging
import os
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.models import Base
from app.routers import auth, budgets, categories, expenses, exports, recurring, reports
from app.services.recurring import generate_due_recurring_expenses

logger = logging.getLogger("uvicorn.error")

_scheduler = BackgroundScheduler(timezone="UTC")
_scheduler.add_job(
    generate_due_recurring_expenses,
    trigger="cron",
    hour=0,
    minute=5,
    id="recurring_expenses_job",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    Base.metadata.create_all(bind=engine)
    _scheduler.start()
    logger.info("Scheduler started — recurring expenses generated daily at 00:05 UTC")
    try:
        result = generate_due_recurring_expenses()
        logger.info("Startup recurring check: %s", result)
    except Exception as exc:
        logger.error("Startup recurring check failed: %s", exc)

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    _scheduler.shutdown(wait=False)
    logger.info("Scheduler stopped")


app = FastAPI(
    title="Expense Tracker API",
    description=(
        "A comprehensive expense tracking API with custom categories, "
        "budget limits & alerts, recurring expenses, analytics reports, "
        "and CSV/PDF export."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
# allow_origins=["*"] and allow_credentials=True cannot be used together —
# browsers reject it. Use explicit origins if you need credentials (cookies).
# JWT tokens travel in the Authorization header, so credentials=False is fine.
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(expenses.router)
app.include_router(categories.router)
app.include_router(budgets.router)
app.include_router(recurring.router)
app.include_router(reports.router)
app.include_router(exports.router)


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        logger.error("Health check DB failure: %s", exc)
        db_status = "error"
    return {"status": "ok", "version": "2.0.0", "db": db_status}
