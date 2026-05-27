import csv
import datetime
import io
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import ExpenseDB


def generate_csv_export(
    db: Session,
    user_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    category: Optional[str] = None,
    is_income: Optional[bool] = None,
) -> io.StringIO:
    """Build a filtered CSV export of expense records."""
    start_dt = datetime.datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0)
    end_dt = datetime.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)

    query = db.query(ExpenseDB).filter(
        ExpenseDB.user_id == user_id,
        ExpenseDB.date >= start_dt,
        ExpenseDB.date <= end_dt,
    )
    if category is not None:
        query = query.filter(ExpenseDB.category == category)
    if is_income is not None:
        query = query.filter(ExpenseDB.is_income == is_income)
    expenses = query.order_by(ExpenseDB.date.asc()).all()

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["id", "title", "amount", "date", "category", "is_income", "notes"],
    )
    writer.writeheader()
    for expense in expenses:
        writer.writerow({
            "id": expense.id,
            "title": expense.title,
            "amount": expense.amount,
            "date": expense.date.strftime("%Y-%m-%d"),
            "category": expense.category,
            "is_income": expense.is_income,
            "notes": expense.notes,
        })
    buffer.seek(0)
    return buffer


def generate_pdf_export(
    db: Session,
    user_id: int,
    user_name: str,
    start_date: datetime.date,
    end_date: datetime.date,
    category: Optional[str] = None,
    is_income: Optional[bool] = None,
) -> io.BytesIO:
    """Generate a PDF expense report using reportlab."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="PDF export is not available. Install reportlab.",
        )

    # Build filtered query
    start_dt = datetime.datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0)
    end_dt = datetime.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)
    query = db.query(ExpenseDB).filter(
        ExpenseDB.user_id == user_id,
        ExpenseDB.date >= start_dt,
        ExpenseDB.date <= end_dt,
    )
    if category is not None:
        query = query.filter(ExpenseDB.category == category)
    if is_income is not None:
        query = query.filter(ExpenseDB.is_income == is_income)
    expenses = query.order_by(ExpenseDB.date.asc()).all()

    total_income = sum(e.amount for e in expenses if e.is_income)
    total_expenses = sum(e.amount for e in expenses if not e.is_income)
    net_balance = total_income - total_expenses

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # Title section
    story.append(Paragraph(f"Expense Report — {user_name}", styles["Title"]))
    story.append(Paragraph(f"Period: {start_date} to {end_date}", styles["Normal"]))
    story.append(Spacer(1, 0.4 * cm))

    # Summary table
    summary_data = [
        ["Summary", "Amount"],
        ["Total Income",   f"${total_income:,.2f}"],
        ["Total Expenses", f"${total_expenses:,.2f}"],
        ["Net Balance",    f"${net_balance:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[8 * cm, 5 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#607D8B")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN",         (1, 0), (1, -1), "RIGHT"),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.5 * cm))

    # Transaction detail table
    if expenses:
        story.append(Paragraph("Transaction Details", styles["Heading2"]))
        rows = [["Date", "Title", "Category", "Amount", "Type", "Notes"]]
        for e in expenses:
            rows.append([
                e.date.strftime("%Y-%m-%d"),
                str(e.title)[:30],
                e.category,
                f"${e.amount:,.2f}",
                "Income" if e.is_income else "Expense",
                str(e.notes or "")[:40],
            ])
        detail_table = Table(
            rows,
            colWidths=[2.5 * cm, 4 * cm, 3 * cm, 2.5 * cm, 2.5 * cm, 4 * cm],
        )
        detail_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#455A64")),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ("ALIGN",         (3, 0), (3, -1), "RIGHT"),
        ]))
        story.append(detail_table)
    else:
        story.append(Paragraph("No records found for the selected filters.", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer
