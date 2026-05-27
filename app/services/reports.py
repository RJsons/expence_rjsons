from typing import List

from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.models import ExpenseDB
from app.schemas import (
    CategoryBreakdownResponse,
    ChartDataResponse,
    MonthlySummaryResponse,
    MonthlyTrendResponse,
)


def compute_monthly_summary(
    db: Session, user_id: int, month: int, year: int
) -> MonthlySummaryResponse:
    """Aggregate income/expense totals for a given user/month/year."""
    total_income = (
        db.query(func.sum(ExpenseDB.amount))
        .filter(
            ExpenseDB.user_id == user_id,
            ExpenseDB.is_income == True,
            extract("month", ExpenseDB.date) == month,
            extract("year", ExpenseDB.date) == year,
        )
        .scalar()
    ) or 0.0

    total_expenses = (
        db.query(func.sum(ExpenseDB.amount))
        .filter(
            ExpenseDB.user_id == user_id,
            ExpenseDB.is_income == False,
            extract("month", ExpenseDB.date) == month,
            extract("year", ExpenseDB.date) == year,
        )
        .scalar()
    ) or 0.0

    transaction_count = (
        db.query(func.count(ExpenseDB.id))
        .filter(
            ExpenseDB.user_id == user_id,
            extract("month", ExpenseDB.date) == month,
            extract("year", ExpenseDB.date) == year,
        )
        .scalar()
    ) or 0

    top_row = (
        db.query(ExpenseDB.category, func.sum(ExpenseDB.amount).label("total"))
        .filter(
            ExpenseDB.user_id == user_id,
            ExpenseDB.is_income == False,
            extract("month", ExpenseDB.date) == month,
            extract("year", ExpenseDB.date) == year,
        )
        .group_by(ExpenseDB.category)
        .order_by(func.sum(ExpenseDB.amount).desc())
        .first()
    )

    return MonthlySummaryResponse(
        month=month,
        year=year,
        total_income=float(total_income),
        total_expenses=float(total_expenses),
        net_balance=float(total_income) - float(total_expenses),
        transaction_count=int(transaction_count),
        top_expense_category=top_row.category if top_row else None,
    )


def compute_category_breakdown(
    db: Session, user_id: int, month: int, year: int
) -> List[CategoryBreakdownResponse]:
    """Group non-income expenses by category for a given month/year."""
    rows = (
        db.query(
            ExpenseDB.category,
            func.sum(ExpenseDB.amount).label("total"),
            func.count(ExpenseDB.id).label("count"),
        )
        .filter(
            ExpenseDB.user_id == user_id,
            ExpenseDB.is_income == False,
            extract("month", ExpenseDB.date) == month,
            extract("year", ExpenseDB.date) == year,
        )
        .group_by(ExpenseDB.category)
        .all()
    )

    grand_total = sum(row.total for row in rows) if rows else 0.0
    if grand_total == 0:
        grand_total = 1.0  # avoid division by zero

    result = [
        CategoryBreakdownResponse(
            category=row.category,
            total_amount=float(row.total),
            transaction_count=int(row.count),
            percentage_of_total=(float(row.total) / grand_total) * 100,
        )
        for row in rows
    ]
    return sorted(result, key=lambda x: x.total_amount, reverse=True)


def compute_income_vs_expense(
    db: Session, user_id: int, year: int
) -> List[MonthlyTrendResponse]:
    """Group income and expenses by month for a given year (only months with data)."""
    income_rows = (
        db.query(
            extract("month", ExpenseDB.date).label("month"),
            func.sum(ExpenseDB.amount).label("total"),
        )
        .filter(
            ExpenseDB.user_id == user_id,
            ExpenseDB.is_income == True,
            extract("year", ExpenseDB.date) == year,
        )
        .group_by(extract("month", ExpenseDB.date))
        .all()
    )

    expense_rows = (
        db.query(
            extract("month", ExpenseDB.date).label("month"),
            func.sum(ExpenseDB.amount).label("total"),
        )
        .filter(
            ExpenseDB.user_id == user_id,
            ExpenseDB.is_income == False,
            extract("year", ExpenseDB.date) == year,
        )
        .group_by(extract("month", ExpenseDB.date))
        .all()
    )

    income_map: dict[int, float] = {int(r.month): float(r.total) for r in income_rows}
    expense_map: dict[int, float] = {int(r.month): float(r.total) for r in expense_rows}
    months = sorted(set(income_map.keys()) | set(expense_map.keys()))

    return [
        MonthlyTrendResponse(
            month=m,
            year=year,
            total_income=income_map.get(m, 0.0),
            total_expenses=expense_map.get(m, 0.0),
            net_balance=income_map.get(m, 0.0) - expense_map.get(m, 0.0),
        )
        for m in months
    ]


def build_chart_data(
    db: Session,
    user_id: int,
    chart_type: str,
    month: int,
    year: int,
) -> ChartDataResponse:
    """Build chart-ready data for pie, bar, or line chart types."""
    if chart_type in ("pie", "bar"):
        breakdown = compute_category_breakdown(db, user_id, month, year)
        return ChartDataResponse(
            chart_type=chart_type,
            labels=[item.category for item in breakdown],
            datasets=[{"label": "Expenses", "data": [item.total_amount for item in breakdown]}],
        )
    elif chart_type == "line":
        trends = compute_income_vs_expense(db, user_id, year)
        return ChartDataResponse(
            chart_type="line",
            labels=[str(t.month) for t in trends],
            datasets=[
                {"label": "Income",   "data": [t.total_income for t in trends]},
                {"label": "Expenses", "data": [t.total_expenses for t in trends]},
            ],
        )
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="chart_type must be 'pie', 'bar', or 'line'")
