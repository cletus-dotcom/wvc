from ...extensions import db
from datetime import datetime

class CateringRequest(db.Model):
    __tablename__ = "catering_requests"

    id = db.Column(db.Integer, primary_key=True)
    requestor_name = db.Column(db.String(150), nullable=False)
    customer_address = db.Column(db.String(255), nullable=False)
    contact_number = db.Column(db.String(50), nullable=False)
    email_address = db.Column(db.String(150), nullable=True)
    event_date = db.Column(db.Date, nullable=False)
    event_time = db.Column(db.Time, nullable=False)
    items_requested = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CateringMenu(db.Model):
    __tablename__ = "catering_menu"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CateringEquipment(db.Model):
    __tablename__ = "catering_equipment"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(255), nullable=False)
    rent_price = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CateringTransaction(db.Model):
    __tablename__ = "catering_transaction"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('catering_requests.id'), nullable=True)  # Nullable for expenses
    booking_amount = db.Column(db.Numeric(10, 2), nullable=True)  # Nullable for expenses
    trans_description = db.Column(db.String(255), nullable=False)
    trans_amount = db.Column(db.Numeric(10, 2), nullable=False)
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    booking = db.relationship("CateringRequest", backref="transactions")


class CateringExpense(db.Model):
    __tablename__ = "catering_expense"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    expense_type = db.Column(db.String(50), nullable=False)  # Wages, Expenses, Miscellaneous, Purchases
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text, nullable=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)  # For wages
    employee_name = db.Column(db.String(150), nullable=True)  # For wages
    remarks = db.Column(db.Text, nullable=True)
    reference_number = db.Column(db.String(100), nullable=True)  # For Purchases: PUR-YYYY-MM-DD-###
    booking_id = db.Column(db.Integer, db.ForeignKey('catering_requests.id'), nullable=True)  # Optional link to booking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    employee = db.relationship("Employee", backref="catering_expenses")
    booking = db.relationship("CateringRequest", backref="expenses")
    purchase_items = db.relationship(
        "CateringPurchaseItem",
        backref="expense",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )


class CateringPurchaseItem(db.Model):
    __tablename__ = "catering_purchase_items"

    id = db.Column(db.Integer, primary_key=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('catering_expense.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    qty = db.Column(db.Numeric(10, 2), nullable=False)
    unit = db.Column(db.String(50), nullable=True)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CateringWage(db.Model):
    __tablename__ = "catering_wages"

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    employee_name = db.Column(db.String(150), nullable=False)
    rate_per_day = db.Column(db.Numeric(10, 2), nullable=False)
    number_of_days = db.Column(db.Numeric(10, 2), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)  # rate_per_day * number_of_days
    description = db.Column(db.String(255), default="Wages")
    expense_id = db.Column(db.Integer, db.ForeignKey('catering_expense.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    employee = db.relationship("Employee", backref="catering_wages")
    expense = db.relationship("CateringExpense", backref="wage_entries")