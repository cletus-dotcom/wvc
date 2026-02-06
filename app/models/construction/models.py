from ...extensions import db
from datetime import datetime
from sqlalchemy import event, text

class ConstructionRequest(db.Model):
    __tablename__ = "construction_requests"

    id = db.Column(db.Integer, primary_key=True)
    project_name = db.Column(db.String(150), nullable=False)
    requested_by = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(100))
    date_requested = db.Column(db.DateTime, default=db.func.now())
    status = db.Column(db.String(50), default="Pending")
    remarks = db.Column(db.Text)

class ConstructionContract(db.Model):
    __tablename__ = "construction_contracts"
    id = db.Column(db.BigInteger, primary_key=True)
    contractor_name = db.Column(db.String(255), nullable=False)
    contractor_address = db.Column(db.Text)
    project_name = db.Column(db.String(255), nullable=False)
    project_site = db.Column(db.Text)
    ntp_date = db.Column(db.Date)
    completion_date = db.Column(db.Date)
    contract_duration = db.Column(db.Integer, nullable=False) 
    contract_price = db.Column(db.Numeric(16,2))
    status = db.Column(db.String(50), default="planning")
    created_at = db.Column(db.DateTime, default=datetime.now)

from datetime import datetime
from app.extensions import db


class ProjectExpense(db.Model):
    __tablename__ = "project_expenses"

    id = db.Column(db.BigInteger, primary_key=True)

    contract_id = db.Column(
        db.BigInteger,
        db.ForeignKey("construction_contracts.id"),
        nullable=False
    )

    # -----------------------------
    # COMMON FIELDS
    # -----------------------------
    expense_type = db.Column(db.String(100))
    expense_date = db.Column(db.Date)

    # -----------------------------
    # MATERIAL FIELDS
    # -----------------------------
    item = db.Column(db.Text)
    qty = db.Column(db.Numeric(12, 3))
    unit = db.Column(db.String(50))
    unit_price = db.Column(db.Numeric(14, 2))
    material_amount = db.Column(db.Numeric(14, 2))

    # -----------------------------
    # LABOR FIELDS (NEW)
    # -----------------------------
    labor_id = db.Column(
        db.BigInteger,
        db.ForeignKey("employees.id"),
        nullable=True
    )
    rate_per_day = db.Column(db.Numeric(14, 2), nullable=True)
    days = db.Column(db.Numeric(12, 3), nullable=True)
    labor_charge = db.Column(db.Numeric(14, 2))  # (rate_per_day * days) + overtime_amount
    overtime_hours = db.Column(db.Numeric(12, 3), nullable=True)
    overtime_amount = db.Column(db.Numeric(14, 2), nullable=True)  # (rate_per_day/8) * overtime_hours

    # -----------------------------
    # GASOLINE FIELDS
    # -----------------------------
    gasoline_amount = db.Column(db.Numeric(14, 2))

    # -----------------------------
    # DOCUMENT FIELDS
    # -----------------------------
    document_ref = db.Column(db.String(255))
    document_amount = db.Column(db.Numeric(14, 2))

    # -----------------------------
    # OBLIGATION FIELDS
    # -----------------------------
    obligation_ref = db.Column(db.String(255))
    obligation_amount = db.Column(db.Numeric(14, 2))

    # -----------------------------
    # ACTIVITY FIELDS
    # -----------------------------
    activity_date = db.Column(db.DateTime)
    activity = db.Column(db.String(255))
    activity_status = db.Column(db.String(50), default="Pending")

    # -----------------------------
    # SYSTEM FIELDS
    # -----------------------------
    invoice_number = db.Column(db.String(50))

    created_by = db.Column(
        db.BigInteger,
        db.ForeignKey("users.id")
    )
    created_at = db.Column(db.DateTime, default=datetime.now)


class DailyInvoiceCounter(db.Model):
    __tablename__ = "daily_invoice_counter"
    invoice_date = db.Column(db.Date, primary_key=True)
    last_seq = db.Column(db.Integer, default=0)
