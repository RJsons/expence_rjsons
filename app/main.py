from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, budgets, categories, expenses, exports, recurring, reports
from app.services.recurring import generate_due_recurring_expenses

app = FastAPI(
    title="Expense Tracker API",
    description=(
        "A comprehensive expense tracking API with custom categories, "
        "budget limits & alerts, recurring expenses, analytics reports, "
        "and CSV/PDF export."
    ),
    version="2.0.0",
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── APScheduler ──────────────────────────────────────────────────────────────
# Runs generate_due_recurring_expenses() every day at 00:05
_scheduler = BackgroundScheduler()
_scheduler.add_job(
    generate_due_recurring_expenses,
    trigger="cron",
    hour=0,
    minute=5,
    id="recurring_expenses_job",
)


@app.on_event("startup")
def startup_event() -> None:
    _scheduler.start()
    print("INFO:     Scheduler started — recurring expenses generated daily at 00:05")
    try:
        from app.services.recurring import generate_due_recurring_expenses
        res = generate_due_recurring_expenses()
        print(f"INFO:     Startup recurring expense generation check: {res}")
    except Exception as e:
        print(f"ERROR:    Failed to run startup recurring check: {e}")


@app.on_event("shutdown")
def shutdown_event() -> None:
    _scheduler.shutdown(wait=False)
    print("INFO:     Scheduler stopped")


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
    return {"status": "ok", "version": "2.0.0"}
