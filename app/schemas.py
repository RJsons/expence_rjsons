import datetime
import re
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ─── Auth ─────────────────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    name: str = Field(..., min_length=2)
    mobile_number: str
    password: str = Field(..., min_length=6)

    @field_validator("mobile_number")
    @classmethod
    def validate_mobile_number(cls, v: str) -> str:
        digits = re.sub(r"[\s\-()]", "", v)
        # strip optional leading +91 or 0
        if digits.startswith("+91"):
            digits = digits[3:]
        elif digits.startswith("91") and len(digits) == 12:
            digits = digits[2:]
        elif digits.startswith("0") and len(digits) == 11:
            digits = digits[1:]
        if not digits.isdigit():
            raise ValueError("Mobile number must contain only digits")
        if len(digits) != 10:
            raise ValueError("Mobile number must be exactly 10 digits")
        if not re.match(r"^[6-9]", digits):
            raise ValueError("Mobile number must start with 6, 7, 8, or 9")
        return digits


class UserLogin(BaseModel):
    mobile_number: str
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    mobile_number: str

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# ─── Expenses ─────────────────────────────────────────────────────────────────


class ExpenseCreate(BaseModel):
    title: str
    amount: float
    date: datetime.datetime
    category: str
    is_income: bool
    notes: Optional[str] = ""


class ExpenseResponse(BaseModel):
    id: int
    title: str
    amount: float
    date: datetime.datetime
    category: str
    is_income: bool
    notes: str
    user_id: int

    model_config = ConfigDict(from_attributes=True)


# ─── All-members expense view ─────────────────────────────────────────────────


class ExpenseWithUser(BaseModel):
    id: int
    title: str
    amount: float
    date: datetime.datetime
    category: str
    is_income: bool
    notes: str
    user_id: int
    user_name: str

    model_config = ConfigDict(from_attributes=True)


# ─── Categories ───────────────────────────────────────────────────────────────


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: Optional[str] = "#607D8B"
    icon: Optional[str] = "category"


class CategoryResponse(BaseModel):
    id: int
    name: str
    color: str
    icon: str
    is_default: bool
    user_id: int

    model_config = ConfigDict(from_attributes=True)


DEFAULT_CATEGORIES = [
    {"name": "Food & Dining",  "color": "#FF5722", "icon": "restaurant"},
    {"name": "Transport",      "color": "#2196F3", "icon": "directions_car"},
    {"name": "Shopping",       "color": "#9C27B0", "icon": "shopping_bag"},
    {"name": "Entertainment",  "color": "#FF9800", "icon": "movie"},
    {"name": "Health",         "color": "#4CAF50", "icon": "local_hospital"},
    {"name": "Utilities",      "color": "#607D8B", "icon": "bolt"},
    {"name": "Salary",         "color": "#00BCD4", "icon": "work"},
    {"name": "Other",          "color": "#9E9E9E", "icon": "more_horiz"},
]

# ─── Budgets ──────────────────────────────────────────────────────────────────


class BudgetLimitCreate(BaseModel):
    category: str
    limit_amount: float = Field(..., gt=0)
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2000)
    alert_threshold: float = Field(default=0.8, ge=0.0, le=1.0)


class BudgetLimitResponse(BaseModel):
    id: int
    category: str
    limit_amount: float
    month: int
    year: int
    alert_threshold: float
    user_id: int

    model_config = ConfigDict(from_attributes=True)


class BudgetStatusResponse(BaseModel):
    category: str
    limit_amount: float
    spent_amount: float
    remaining_amount: float
    usage_percentage: float
    alert_level: str  # "ok" | "warning" | "exceeded"
    month: int
    year: int


# ─── Reports ──────────────────────────────────────────────────────────────────


class MonthlySummaryResponse(BaseModel):
    month: int
    year: int
    total_income: float
    total_expenses: float
    net_balance: float
    transaction_count: int
    top_expense_category: Optional[str]


class CategoryBreakdownResponse(BaseModel):
    category: str
    total_amount: float
    transaction_count: int
    percentage_of_total: float


class MonthlyTrendResponse(BaseModel):
    month: int
    year: int
    total_income: float
    total_expenses: float
    net_balance: float


class ChartDataResponse(BaseModel):
    chart_type: str        # "pie" | "bar" | "line"
    labels: List[str]
    datasets: List[dict]   # [{label, data, colors}]


# ─── Recurring ────────────────────────────────────────────────────────────────


class RecurringTemplateCreate(BaseModel):
    title: str
    amount: float = Field(..., gt=0)
    category: str
    is_income: bool = False
    notes: Optional[str] = ""
    frequency: str = Field(..., pattern="^(daily|weekly|monthly)$")
    start_date: datetime.date


class RecurringTemplateResponse(BaseModel):
    id: int
    title: str
    amount: float
    category: str
    is_income: bool
    notes: str
    frequency: str
    start_date: datetime.date
    next_due_date: datetime.date
    is_active: bool
    user_id: int

    model_config = ConfigDict(from_attributes=True)
