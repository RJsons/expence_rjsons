from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.models import BudgetLimitDB, ExpenseDB
from app.schemas import BudgetStatusResponse


def determine_alert_level(usage_pct: float, alert_threshold: float) -> str:
    """Return alert level based on usage percentage vs. threshold."""
    if usage_pct >= 1.0:
        return "exceeded"
    elif usage_pct >= alert_threshold:
        return "warning"
    else:
        return "ok"


def calculate_budget_status(
    db: Session,
    user_id: int,
    category: str,
    month: int,
    year: int,
) -> BudgetStatusResponse | None:
    """Fetch budget limit and compute real-time spending status."""
    budget = db.query(BudgetLimitDB).filter(
        BudgetLimitDB.user_id == user_id,
        BudgetLimitDB.category == category,
        BudgetLimitDB.month == month,
        BudgetLimitDB.year == year,
    ).first()
    if not budget:
        return None

    spent = (
        db.query(func.sum(ExpenseDB.amount))
        .filter(
            ExpenseDB.user_id == user_id,
            ExpenseDB.is_income == False,
            ExpenseDB.category == category,
            extract("month", ExpenseDB.date) == month,
            extract("year", ExpenseDB.date) == year,
        )
        .scalar()
    ) or 0.0

    limit_amount: float = float(budget.limit_amount)
    alert_threshold: float = float(budget.alert_threshold)
    spent_amount: float = float(spent)
    usage_pct: float = spent_amount / limit_amount if limit_amount > 0 else 0.0
    remaining: float = limit_amount - spent_amount
    alert_level: str = determine_alert_level(usage_pct, alert_threshold)

    return BudgetStatusResponse(
        category=category,
        limit_amount=limit_amount,
        spent_amount=spent_amount,
        remaining_amount=remaining,
        usage_percentage=usage_pct,
        alert_level=alert_level,
        month=month,
        year=year,
    )
