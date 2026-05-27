import datetime

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base, engine


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    mobile_number = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    expenses = relationship("ExpenseDB", back_populates="owner", cascade="all, delete-orphan")
    categories = relationship("CategoryDB", back_populates="owner", cascade="all, delete-orphan")
    budget_limits = relationship("BudgetLimitDB", back_populates="owner", cascade="all, delete-orphan")
    recurring_templates = relationship("RecurringTemplateDB", back_populates="owner", cascade="all, delete-orphan")


class ExpenseDB(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    category = Column(String, nullable=False)
    is_income = Column(Boolean, default=False, nullable=False)
    notes = Column(String, default="")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    owner = relationship("UserDB", back_populates="expenses")


class CategoryDB(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    color = Column(String, default="#607D8B")
    icon = Column(String, default="category")
    is_default = Column(Boolean, default=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    owner = relationship("UserDB", back_populates="categories")


class BudgetLimitDB(Base):
    __tablename__ = "budget_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category = Column(String, nullable=False)
    limit_amount = Column(Float, nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    alert_threshold = Column(Float, default=0.8)

    owner = relationship("UserDB", back_populates="budget_limits")


class RecurringTemplateDB(Base):
    __tablename__ = "recurring_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    is_income = Column(Boolean, default=False)
    notes = Column(String, default="")
    frequency = Column(String, nullable=False)
    start_date = Column(Date, nullable=False)
    next_due_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)

    owner = relationship("UserDB", back_populates="recurring_templates")


# Ensure all tables exist (safe to call multiple times)
Base.metadata.create_all(bind=engine)
