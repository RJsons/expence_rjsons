from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ExpenseDB, UserDB
from app.schemas import ExpenseCreate, ExpenseResponse, ExpenseWithUser

router = APIRouter(prefix="/api/expenses", tags=["Expenses"])


@router.get("/all", response_model=List[ExpenseWithUser])
def get_all_expenses(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return every expense in the system joined with the owner's name, newest first."""
    rows = (
        db.query(ExpenseDB, UserDB.name.label("user_name"), UserDB.id.label("uid"))
        .join(UserDB, ExpenseDB.user_id == UserDB.id)
        .order_by(ExpenseDB.date.desc())
        .all()
    )
    return [
        ExpenseWithUser(
            id=expense.id,
            title=expense.title,
            amount=expense.amount,
            date=expense.date,
            category=expense.category,
            is_income=expense.is_income,
            notes=expense.notes or "",
            user_id=uid,
            user_name=user_name,
        )
        for expense, user_name, uid in rows
    ]


@router.get("", response_model=List[ExpenseResponse])
def get_expenses(
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all expenses for the authenticated user, newest first."""
    return (
        db.query(ExpenseDB)
        .filter(ExpenseDB.user_id == current_user.id)
        .order_by(ExpenseDB.date.desc())
        .all()
    )


@router.post("", response_model=ExpenseResponse, status_code=201)
def add_expense(
    expense_in: ExpenseCreate,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new expense or income record."""
    new_expense = ExpenseDB(
        title=expense_in.title,
        amount=expense_in.amount,
        date=expense_in.date,
        category=expense_in.category,
        is_income=expense_in.is_income,
        notes=expense_in.notes,
        user_id=current_user.id,
    )
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    return new_expense


@router.put("/{expense_id}", response_model=ExpenseResponse)
def update_expense(
    expense_id: int,
    expense_in: ExpenseCreate,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing expense record."""
    expense = db.query(ExpenseDB).filter(
        ExpenseDB.id == expense_id,
        ExpenseDB.user_id == current_user.id,
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense record not found or access denied")

    expense.title = expense_in.title
    expense.amount = expense_in.amount
    expense.date = expense_in.date
    expense.category = expense_in.category
    expense.is_income = expense_in.is_income
    expense.notes = expense_in.notes
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=200)
def delete_expense(
    expense_id: int,
    current_user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an expense record."""
    expense = db.query(ExpenseDB).filter(
        ExpenseDB.id == expense_id,
        ExpenseDB.user_id == current_user.id,
    ).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense record not found or access denied")

    db.delete(expense)
    db.commit()
    return {"detail": "Expense record deleted successfully"}
