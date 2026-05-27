from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import RecurringTemplateDB, UserDB
from app.schemas import RecurringTemplateCreate, RecurringTemplateResponse

router = APIRouter(prefix="/api/recurring", tags=["Recurring Expenses"])


@router.get("", response_model=List[RecurringTemplateResponse])
def get_recurring(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Return all recurring expense templates for the authenticated user."""
    return (
        db.query(RecurringTemplateDB)
        .filter(RecurringTemplateDB.user_id == current_user.id)
        .all()
    )


@router.post("", response_model=RecurringTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_recurring(
    template_in: RecurringTemplateCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Create a recurring expense template. First expense fires on start_date."""
    new_template = RecurringTemplateDB(
        user_id=current_user.id,
        title=template_in.title,
        amount=template_in.amount,
        category=template_in.category,
        is_income=template_in.is_income,
        notes=template_in.notes or "",
        frequency=template_in.frequency,
        start_date=template_in.start_date,
        next_due_date=template_in.start_date,  # first run triggers on start_date
        is_active=True,
    )
    db.add(new_template)
    db.commit()
    db.refresh(new_template)
    return new_template


@router.put("/{template_id}", response_model=RecurringTemplateResponse)
def update_recurring(
    template_id: int,
    template_in: RecurringTemplateCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Update a recurring template's editable fields."""
    template = db.query(RecurringTemplateDB).filter(
        RecurringTemplateDB.id == template_id,
        RecurringTemplateDB.user_id == current_user.id,
    ).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring template not found or access denied",
        )
    template.title = template_in.title
    template.amount = template_in.amount
    template.category = template_in.category
    template.is_income = template_in.is_income
    template.notes = template_in.notes or ""
    template.frequency = template_in.frequency
    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_200_OK)
def delete_recurring(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Permanently delete a recurring template."""
    template = db.query(RecurringTemplateDB).filter(
        RecurringTemplateDB.id == template_id,
        RecurringTemplateDB.user_id == current_user.id,
    ).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring template not found or access denied",
        )
    db.delete(template)
    db.commit()
    return {"detail": "Recurring template deleted successfully"}


@router.post("/{template_id}/pause", response_model=RecurringTemplateResponse)
def pause_recurring(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Pause a recurring template (set is_active=False)."""
    template = db.query(RecurringTemplateDB).filter(
        RecurringTemplateDB.id == template_id,
        RecurringTemplateDB.user_id == current_user.id,
    ).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring template not found or access denied",
        )
    template.is_active = False
    db.commit()
    db.refresh(template)
    return template


@router.post("/{template_id}/resume", response_model=RecurringTemplateResponse)
def resume_recurring(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """Resume a paused recurring template (set is_active=True)."""
    template = db.query(RecurringTemplateDB).filter(
        RecurringTemplateDB.id == template_id,
        RecurringTemplateDB.user_id == current_user.id,
    ).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recurring template not found or access denied",
        )
    template.is_active = True
    db.commit()
    db.refresh(template)
    return template
