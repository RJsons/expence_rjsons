from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import UserDB
from app.schemas import (
    CategoryBreakdownResponse,
    ChartDataResponse,
    MonthlySummaryResponse,
    MonthlyTrendResponse,
)
from app.services.reports import (
    build_chart_data,
    compute_category_breakdown,
    compute_income_vs_expense,
    compute_monthly_summary,
)

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/monthly-summary", response_model=MonthlySummaryResponse)
def get_monthly_summary(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Aggregate income/expense totals for a given month and year."""
    return compute_monthly_summary(db, current_user.id, month, year)


@router.get("/category-breakdown", response_model=List[CategoryBreakdownResponse])
def get_category_breakdown(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Return non-income expense totals grouped by category for a given month/year."""
    return compute_category_breakdown(db, current_user.id, month, year)


@router.get("/income-vs-expense", response_model=List[MonthlyTrendResponse])
def get_income_vs_expense(
    year: int = Query(..., ge=2000),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Return monthly income vs expense totals for every month with data in the given year."""
    return compute_income_vs_expense(db, current_user.id, year)


@router.get("/chart-data", response_model=ChartDataResponse)
def get_chart_data(
    chart_type: str = Query(..., pattern="^(pie|bar|line)$"),
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """
    Return chart-ready data.
    - pie / bar → category breakdown for the given month/year
    - line      → income vs expense trend across months for the given year
    """
    return build_chart_data(db, current_user.id, chart_type, month, year)
