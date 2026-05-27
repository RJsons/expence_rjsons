from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import BudgetLimitDB, UserDB
from app.schemas import BudgetLimitCreate, BudgetLimitResponse, BudgetStatusResponse
from app.services.budget import calculate_budget_status

router = APIRouter(prefix="/api/budgets", tags=["Budgets"])


@router.get("", response_model=List[BudgetLimitResponse])
def get_budgets(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Return all budget limits for the authenticated user."""
    return db.query(BudgetLimitDB).filter(BudgetLimitDB.user_id == current_user.id).all()


@router.post("", response_model=BudgetLimitResponse, status_code=status.HTTP_201_CREATED)
def create_budget(
    budget: BudgetLimitCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Create a budget limit. Returns 409 if one already exists for the same category/month/year."""
    existing = db.query(BudgetLimitDB).filter(
        BudgetLimitDB.user_id == current_user.id,
        BudgetLimitDB.category == budget.category,
        BudgetLimitDB.month == budget.month,
        BudgetLimitDB.year == budget.year,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Budget limit already exists for this category and period",
        )
    new_budget = BudgetLimitDB(
        user_id=current_user.id,
        category=budget.category,
        limit_amount=budget.limit_amount,
        month=budget.month,
        year=budget.year,
        alert_threshold=budget.alert_threshold,
    )
    db.add(new_budget)
    db.commit()
    db.refresh(new_budget)
    return new_budget


# NOTE: /status must be declared BEFORE /{budget_id} to avoid route shadowing
@router.get("/status", response_model=List[BudgetStatusResponse])
def get_budget_status(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2000),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Return real-time spending status for all budget limits in a given month/year."""
    budgets = db.query(BudgetLimitDB).filter(
        BudgetLimitDB.user_id == current_user.id,
        BudgetLimitDB.month == month,
        BudgetLimitDB.year == year,
    ).all()
    result = []
    for b in budgets:
        status_resp = calculate_budget_status(db, current_user.id, b.category, month, year)
        if status_resp is not None:
            result.append(status_resp)
    return result


@router.put("/{budget_id}", response_model=BudgetLimitResponse)
def update_budget(
    budget_id: int,
    budget: BudgetLimitCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Update a budget limit."""
    db_budget = db.query(BudgetLimitDB).filter(
        BudgetLimitDB.id == budget_id,
        BudgetLimitDB.user_id == current_user.id,
    ).first()
    if not db_budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget limit not found or access denied",
        )
    db_budget.category = budget.category
    db_budget.limit_amount = budget.limit_amount
    db_budget.month = budget.month
    db_budget.year = budget.year
    db_budget.alert_threshold = budget.alert_threshold
    db.commit()
    db.refresh(db_budget)
    return db_budget


@router.delete("/{budget_id}", status_code=200)
def delete_budget(
    budget_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Delete a budget limit."""
    db_budget = db.query(BudgetLimitDB).filter(
        BudgetLimitDB.id == budget_id,
        BudgetLimitDB.user_id == current_user.id,
    ).first()
    if not db_budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget limit not found or access denied",
        )
    db.delete(db_budget)
    db.commit()
    return {"detail": "Budget limit deleted successfully"}
