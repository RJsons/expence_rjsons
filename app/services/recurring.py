import calendar
import datetime

from app.database import SessionLocal
from app.models import ExpenseDB, RecurringTemplateDB


def compute_next_due_date(frequency: str, current_due_date: datetime.date) -> datetime.date:
    """Compute the next due date based on frequency."""
    if frequency == "daily":
        return current_due_date + datetime.timedelta(days=1)
    elif frequency == "weekly":
        return current_due_date + datetime.timedelta(weeks=1)
    elif frequency == "monthly":
        next_month = current_due_date.month + 1
        next_year = current_due_date.year
        if next_month > 12:
            next_month = 1
            next_year += 1
        last_day = calendar.monthrange(next_year, next_month)[1]
        target_day = min(current_due_date.day, last_day)
        return datetime.date(next_year, next_month, target_day)
    else:
        raise ValueError(f"Unknown frequency: {frequency}")


def generate_due_recurring_expenses() -> dict:
    """Scheduler job: generate expense records for all due recurring templates."""
    db = SessionLocal()
    generated = 0
    errors = 0
    try:
        today = datetime.date.today()
        due_templates = db.query(RecurringTemplateDB).filter(
            RecurringTemplateDB.is_active == True,
            RecurringTemplateDB.next_due_date <= today,
        ).all()

        for template in due_templates:
            try:
                while template.is_active and template.next_due_date <= today:
                    due_date = template.next_due_date
                    new_expense = ExpenseDB(
                        title=template.title,
                        amount=template.amount,
                        date=datetime.datetime(due_date.year, due_date.month, due_date.day),
                        category=template.category,
                        is_income=template.is_income,
                        notes=(template.notes or "") + " [auto-generated]",
                        user_id=template.user_id,
                    )
                    db.add(new_expense)
                    template.next_due_date = compute_next_due_date(
                        template.frequency, template.next_due_date
                    )
                    db.commit()
                    generated += 1
            except Exception as e:
                db.rollback()
                print(f"Error generating expense for template {template.id}: {e}")
                errors += 1
    finally:
        db.close()
    return {"generated": generated, "errors": errors}
