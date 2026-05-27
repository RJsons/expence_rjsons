import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import UserDB
from app.services.export import generate_csv_export, generate_pdf_export

router = APIRouter(prefix="/api/export", tags=["Export"])


@router.get("/csv")
def export_csv(
    start_date: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
    category: Optional[str] = Query(default=None, description="Filter by category name"),
    is_income: Optional[bool] = Query(default=None, description="True = income only, False = expenses only"),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """
    Download a CSV of expense records within the given date range.
    Optional filters: category, is_income.
    """
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be <= end_date")

    buffer = generate_csv_export(db, current_user.id, start_date, end_date, category, is_income)
    filename = f"expenses_{start_date}_{end_date}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/pdf")
def export_pdf(
    start_date: datetime.date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: datetime.date = Query(..., description="End date (YYYY-MM-DD)"),
    category: Optional[str] = Query(default=None, description="Filter by category name"),
    is_income: Optional[bool] = Query(default=None, description="True = income only, False = expenses only"),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    """
    Download a formatted PDF report within the given date range.
    Includes summary totals and a detailed transaction table.
    Returns HTTP 500 if reportlab is not installed.
    """
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be <= end_date")

    buffer = generate_pdf_export(
        db, current_user.id, current_user.name, start_date, end_date, category, is_income
    )
    filename = f"expenses_{start_date}_{end_date}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
