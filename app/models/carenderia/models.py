# app/models/carenderia/models.py
from ...extensions import db
from datetime import datetime


class MenuItem(db.Model):
    __tablename__ = "menu_items"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)

class CarenderiaDailySummary(db.Model):
    __tablename__ = "carenderia_daily_summary"
    id = db.Column(db.BigInteger, primary_key=True)
    venture_id = db.Column(db.SmallInteger)
    summary_date = db.Column(db.Date, nullable=False)
    total_sales = db.Column(db.Numeric(14,2), default=0)
    total_expenses = db.Column(db.Numeric(14,2), default=0)
    notes = db.Column(db.Text)
    created_by = db.Column(db.BigInteger, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.now)
    is_synced = db.Column(db.Boolean, default=False)
    expenses = db.relationship("CarenderiaExpense", backref="summary", cascade="all, delete-orphan")
    __table_args__ = (db.UniqueConstraint("venture_id", "summary_date", name="uix_venture_summary_date"),)

class CarenderiaExpense(db.Model):
    __tablename__ = "carenderia_expenses"
    id = db.Column(db.BigInteger, primary_key=True)
    summary_id = db.Column(db.BigInteger, db.ForeignKey("carenderia_daily_summary.id"), nullable=False)
    account_id = db.Column(db.BigInteger)
    amount = db.Column(db.Numeric(14,2), nullable=False)
    description = db.Column(db.Text)
    receipt_url = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)


class CarenderiaWage(db.Model):
    __tablename__ = "carenderia_wages"

    id = db.Column(db.BigInteger, primary_key=True)
    emp_id = db.Column(db.BigInteger, nullable=False)
    emp_name = db.Column(db.String(150), nullable=False)
    dept_id = db.Column(db.BigInteger, nullable=True)
    emp_role = db.Column(db.String(100), nullable=True)
    emp_rate = db.Column(db.Numeric(14, 2), nullable=True)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


class CarenderiaTransaction(db.Model):
    __tablename__ = "carenderia_transaction"

    id = db.Column(db.BigInteger, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    trans_type = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(14, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)


class CarenderiaDailyExpense(db.Model):
    __tablename__ = "carenderia_daily_expenses"
    
    id = db.Column(db.Integer, primary_key=True)
    expense_type = db.Column(db.String(100), nullable=False, unique=True)
    amount = db.Column(db.Numeric(14, 2), default=0)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)