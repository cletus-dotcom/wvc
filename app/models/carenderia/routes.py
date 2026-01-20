from flask import render_template, redirect, url_for, session, request, jsonify, flash, send_file, current_app
from app.decorators.auth_decorators import login_required, department_required, role_required
from app.models.core import Employee, Department
from app.extensions import db
from sqlalchemy.orm import joinedload
from . import carenderia_bp
from .models import CarenderiaWage, CarenderiaTransaction
from datetime import datetime, date
from sqlalchemy import extract, func
import calendar
import io

def check_carenderia_access():
    """Check if user has access to Carenderia. Returns True if allowed, False otherwise."""
    user_dept = (session.get("department") or "").lower()
    allowed_departments = ["carenderia", "corporate"]
    return user_dept in allowed_departments

# --- Redirect /carenderia to /carenderia/home ---
@carenderia_bp.route("")
@login_required
def carenderia_root():
    if not check_carenderia_access():
        return redirect(url_for("core.dashboard"))
    return redirect(url_for("carenderia.carenderia_home"))


@carenderia_bp.route("/home")
@login_required
def carenderia_home():
    if not check_carenderia_access():
        return redirect(url_for("core.dashboard"))
    return render_template("carenderia/home.html")


@carenderia_bp.route("/manage-employee")
@login_required
@department_required("Carenderia", "Corporate")
def manage_employee():
    """Manage employees for Carenderia department."""
    # Get Carenderia department
    carenderia_dept = Department.query.filter_by(name="Carenderia").first()
    
    if not carenderia_dept:
        # If Carenderia department doesn't exist, return empty list
        employees = []
    else:
        # Eager load the department relationship to prevent N+1 queries
        # Filter to only show employees from Carenderia department
        employees = Employee.query.filter_by(department_id=carenderia_dept.id) \
                                  .options(joinedload(Employee.department)) \
                                  .order_by(Employee.name.asc()).all()
    
    departments = Department.query.order_by(Department.name.asc()).all()

    return render_template(
        "carenderia/manage_employee.html",
        employees=employees,
        departments=departments
    )


@carenderia_bp.route("/add-employee", methods=["POST"])
@login_required
@department_required("Carenderia", "Corporate")
def add_employee():
    """Add a new employee."""
    name = request.form.get("name", "").strip()
    role = request.form.get("role", "").strip()
    rate = request.form.get("rate_per_day", 0)
    dept_id = request.form.get("department_id")

    if not name or not dept_id:
        return jsonify({"success": False, "error": "Name and Department are required."})

    dept = Department.query.get(int(dept_id))
    if not dept:
        return jsonify({"success": False, "error": "Invalid department."})

    new_emp = Employee(
        name=name,
        role=role,
        rate_per_day=float(rate) if rate else None,
        department_id=int(dept_id)
    )
    db.session.add(new_emp)
    db.session.commit()

    return jsonify({
        "success": True,
        "employee": {
            "id": new_emp.id,
            "name": new_emp.name,
            "role": new_emp.role,
            "rate_per_day": new_emp.rate_per_day,
            "department_id": new_emp.department_id,
            "department_name": dept.name
        }
    })


@carenderia_bp.route("/edit-employee/<int:emp_id>", methods=["POST"])
@login_required
@department_required("Carenderia", "Corporate")
def edit_employee(emp_id):
    """Edit an existing employee."""
    emp = Employee.query.get_or_404(emp_id)
    
    emp.name = request.form.get("name", emp.name).strip()
    emp.role = request.form.get("role", emp.role).strip()
    emp.rate_per_day = float(request.form.get("rate_per_day", emp.rate_per_day) or 0)
    emp.department_id = int(request.form.get("department_id", emp.department_id))

    dept = Department.query.get(emp.department_id)

    db.session.commit()

    # Check for AJAX request
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "success": True,
            "employee": {
                "id": emp.id,
                "name": emp.name,
                "role": emp.role,
                "rate_per_day": emp.rate_per_day,
                "department_id": emp.department_id,
                "department_name": dept.name if dept else ""
            }
        })

    flash("Employee updated successfully!", "success")
    return redirect(url_for("carenderia.manage_employee"))


@carenderia_bp.route("/delete-employee/<int:emp_id>")
@login_required
@department_required("Carenderia", "Corporate")
def delete_employee(emp_id):
    """Delete an employee."""
    emp = Employee.query.get_or_404(emp_id)
    try:
        db.session.delete(emp)
        db.session.commit()
        flash("Employee deleted successfully!", "success")
    except:
        db.session.rollback()
        flash("Cannot delete employee. It may be linked to projects or records.", "danger")
    return redirect(url_for("carenderia.manage_employee"))


@carenderia_bp.route("/employee-names")
@login_required
@department_required("Carenderia", "Corporate")
def employee_names():
    """Get list of employee names for autocomplete (Carenderia department only)."""
    carenderia_dept = Department.query.filter_by(name="Carenderia").first()
    if not carenderia_dept:
        return jsonify({"names": []})
    
    names = [emp.name for emp in Employee.query.filter_by(department_id=carenderia_dept.id) \
                                          .order_by(Employee.name.asc()).all()]
    return jsonify({"names": names})


@carenderia_bp.route("/get-carenderia-employees")
@login_required
@department_required("Carenderia", "Corporate")
def get_carenderia_employees():
    """Get employees from Carenderia department only."""
    carenderia_dept = Department.query.filter_by(name="Carenderia").first()
    if not carenderia_dept:
        return jsonify({"employees": []})
    
    employees = Employee.query.filter_by(department_id=carenderia_dept.id)\
                              .options(joinedload(Employee.department))\
                              .order_by(Employee.name.asc()).all()
    
    return jsonify({
        "employees": [
            {
                "id": e.id,
                "name": e.name,
                "rate_per_day": float(e.rate_per_day) if e.rate_per_day else None,
                "department": e.department.name if e.department else None,
                "department_id": e.department_id,
                "role": e.role
            }
            for e in employees
        ]
    })


@carenderia_bp.post("/save-wages")
@login_required
@department_required("Carenderia", "Corporate")
def save_wages():
    """Save wages entries to carenderia_wages table."""
    data = request.get_json() or {}
    entry_date = data.get("date")
    entries = data.get("entries", [])

    if not entry_date:
        return jsonify({"success": False, "error": "Date is required."}), 400

    if not entries:
        return jsonify({"success": False, "error": "No wage entries provided."}), 400

    try:
        parsed_date = datetime.strptime(entry_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date format."}), 400

    try:
        for entry in entries:
            wage = CarenderiaWage(
                emp_id=entry.get("employeeId"),
                emp_name=entry.get("employeeName"),
                dept_id=entry.get("departmentId"),
                emp_role=entry.get("employeeRole"),
                emp_rate=entry.get("ratePerDay"),
                date=parsed_date,
                amount=entry.get("totalAmount") or 0
            )
            db.session.add(wage)

        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@carenderia_bp.post("/save-transactions")
@login_required
@department_required("Carenderia", "Corporate")
def save_transactions():
    """Save transactions to carenderia_transaction table."""
    data = request.get_json() or {}
    transactions = data.get("transactions", [])

    if not transactions:
        return jsonify({"success": False, "error": "No transactions provided."}), 400

    try:
        for trans in transactions:
            trans_date = trans.get("date")
            trans_type = trans.get("transactionType")
            amount = trans.get("amount")

            if not trans_date or not trans_type or amount is None:
                continue

            try:
                parsed_date = datetime.strptime(trans_date, "%Y-%m-%d").date()
            except ValueError:
                continue

            transaction = CarenderiaTransaction(
                date=parsed_date,
                trans_type=trans_type,
                amount=float(amount) if amount else 0
            )
            db.session.add(transaction)

        db.session.commit()
        return jsonify({"success": True, "message": f"Successfully saved {len(transactions)} transaction(s)."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@carenderia_bp.route("/manage-department")
@login_required
@department_required("Corporate")
def manage_department():
    """Manage departments for Carenderia/Corporate."""
    departments = Department.query.order_by(Department.name.asc()).all()
    return render_template("carenderia/manage_department.html", departments=departments)


@carenderia_bp.route("/add-department", methods=["POST"])
@login_required
@department_required("Corporate")
def add_department():
    """Add a new department."""
    name = request.form.get("name", "").strip()

    if not name:
        flash("Department name cannot be empty.", "danger")
        return redirect(url_for("carenderia.manage_department"))

    # Check if department already exists
    existing = Department.query.filter_by(name=name).first()
    if existing:
        flash("Department already exists.", "warning")
        return redirect(url_for("carenderia.manage_department"))

    # Create new department
    new_dept = Department(name=name)
    db.session.add(new_dept)
    db.session.commit()

    flash("Department added successfully!", "success")
    return redirect(url_for("carenderia.manage_department"))


@carenderia_bp.route("/edit-department/<int:dept_id>", methods=["POST"])
@login_required
@department_required("Corporate")
def edit_department(dept_id):
    """Edit an existing department."""
    dept = Department.query.get_or_404(dept_id)
    new_name = request.form.get("name", "").strip()

    if not new_name:
        flash("Department name cannot be empty.", "danger")
        return redirect(url_for("carenderia.manage_department"))

    # Check for duplicates (excluding itself)
    exists = Department.query.filter(
        Department.name == new_name,
        Department.id != dept_id
    ).first()

    if exists:
        flash("Another department with this name already exists.", "warning")
        return redirect(url_for("carenderia.manage_department"))

    dept.name = new_name
    db.session.commit()

    flash("Department updated successfully!", "success")
    return redirect(url_for("carenderia.manage_department"))


@carenderia_bp.route("/delete-department/<int:dept_id>")
@login_required
@department_required("Corporate")
def delete_department(dept_id):
    """Delete a department."""
    dept = Department.query.get_or_404(dept_id)

    try:
        db.session.delete(dept)
        db.session.commit()
        flash("Department deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Cannot delete department. It may be linked to employees or other records.", "danger")

    return redirect(url_for("carenderia.manage_department"))


@carenderia_bp.route("/view-transactions")
@login_required
def view_transactions():
    """View and edit transactions per date. Accessible to Admin role or Corporate department."""
    user_role = (session.get("role") or "").lower()
    user_dept = (session.get("department") or "").lower()
    
    if user_role != "admin" and user_dept != "corporate":
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("carenderia.carenderia_home"))
    
    return render_template("carenderia/view_transactions.html")


@carenderia_bp.route("/get-transactions-by-date")
@login_required
def get_transactions_by_date():
    """Get transactions for a specific date. Accessible to Admin role or Corporate department."""
    user_role = (session.get("role") or "").lower()
    user_dept = (session.get("department") or "").lower()
    
    if user_role != "admin" and user_dept != "corporate":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    date_str = request.args.get("date")
    if not date_str:
        return jsonify({"success": False, "error": "Date parameter is required."}), 400
    
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date format."}), 400
    
    transactions = CarenderiaTransaction.query.filter_by(date=parsed_date)\
                                              .order_by(CarenderiaTransaction.id.asc()).all()
    
    return jsonify({
        "success": True,
        "transactions": [
            {
                "id": t.id,
                "date": t.date.isoformat() if t.date else None,
                "trans_type": t.trans_type,
                "amount": float(t.amount) if t.amount else 0
            }
            for t in transactions
        ]
    })


@carenderia_bp.route("/update-transaction/<int:trans_id>", methods=["PUT"])
@login_required
def update_transaction(trans_id):
    """Update a transaction. Accessible to Admin role or Corporate department."""
    user_role = (session.get("role") or "").lower()
    user_dept = (session.get("department") or "").lower()
    
    if user_role != "admin" and user_dept != "corporate":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    transaction = CarenderiaTransaction.query.get_or_404(trans_id)
    data = request.get_json() or {}
    
    trans_date = data.get("date")
    trans_type = data.get("trans_type")
    amount = data.get("amount")
    
    if not trans_date or not trans_type or amount is None:
        return jsonify({"success": False, "error": "Missing required fields."}), 400
    
    try:
        parsed_date = datetime.strptime(trans_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date format."}), 400
    
    try:
        transaction.date = parsed_date
        transaction.trans_type = trans_type
        transaction.amount = float(amount) if amount else 0
        db.session.commit()
        
        return jsonify({
            "success": True,
            "transaction": {
                "id": transaction.id,
                "date": transaction.date.isoformat() if transaction.date else None,
                "trans_type": transaction.trans_type,
                "amount": float(transaction.amount) if transaction.amount else 0
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@carenderia_bp.route("/delete-transaction/<int:trans_id>", methods=["DELETE"])
@login_required
def delete_transaction(trans_id):
    """Delete a transaction. Accessible to Admin role or Corporate department."""
    user_role = (session.get("role") or "").lower()
    user_dept = (session.get("department") or "").lower()
    
    if user_role != "admin" and user_dept != "corporate":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    transaction = CarenderiaTransaction.query.get_or_404(trans_id)
    
    try:
        db.session.delete(transaction)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@carenderia_bp.route("/monthly-trial-balance")
@login_required
def monthly_trial_balance():
    """Monthly trial balance sheet. Accessible to Admin role or Corporate department."""
    user_role = (session.get("role") or "").lower()
    user_dept = (session.get("department") or "").lower()
    
    if user_role != "admin" and user_dept != "corporate":
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("carenderia.carenderia_home"))
    
    return render_template("carenderia/monthly_trial_balance.html")


@carenderia_bp.route("/get-transactions-by-month")
@login_required
def get_transactions_by_month():
    """Get transactions grouped by date for a specific month. Accessible to Admin role or Corporate department."""
    user_role = (session.get("role") or "").lower()
    user_dept = (session.get("department") or "").lower()
    
    if user_role != "admin" and user_dept != "corporate":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    month_str = request.args.get("month")
    if not month_str:
        return jsonify({"success": False, "error": "Month parameter is required."}), 400
    
    try:
        # Parse month string (format: YYYY-MM)
        year, month = map(int, month_str.split("-"))
    except ValueError:
        return jsonify({"success": False, "error": "Invalid month format. Use YYYY-MM."}), 400
    
    # Get all transactions for the month
    transactions = CarenderiaTransaction.query.filter(
        extract('year', CarenderiaTransaction.date) == year,
        extract('month', CarenderiaTransaction.date) == month
    ).order_by(CarenderiaTransaction.date.asc(), CarenderiaTransaction.id.asc()).all()
    
    # Group transactions by date and calculate daily totals
    monthly_data = {}
    
    for trans in transactions:
        date_str = trans.date.isoformat() if trans.date else None
        if not date_str:
            continue
        
        if date_str not in monthly_data:
            monthly_data[date_str] = {
                "date": date_str,
                "daily_collection": 0,
                "wages": 0,
                "electric_bill": 0,
                "water_bill": 0,
                "maintenance": 0,
                "mayors_permit": 0,
                "rental": 0,
                "bir": 0,
                "sss": 0,
                "pag_ibig": 0,
                "purchases": 0,
                "total_deductions": 0,
                "net_amount": 0,
                "transactions": []
            }
        
        amount = float(trans.amount) if trans.amount else 0
        trans_type = trans.trans_type or ""
        
        # Add transaction to list
        monthly_data[date_str]["transactions"].append({
            "id": trans.id,
            "trans_type": trans_type,
            "amount": amount
        })
        
        # Calculate totals by type
        if trans_type == "Daily Sales":
            monthly_data[date_str]["daily_collection"] += amount
        elif trans_type == "Wages":
            monthly_data[date_str]["wages"] += amount
        elif trans_type == "Electric Bill":
            monthly_data[date_str]["electric_bill"] += amount
        elif trans_type == "Water Bill":
            monthly_data[date_str]["water_bill"] += amount
        elif trans_type == "Maintenance":
            monthly_data[date_str]["maintenance"] += amount
        elif trans_type == "Mayor's Permit":
            monthly_data[date_str]["mayors_permit"] += amount
        elif trans_type == "Rental":
            monthly_data[date_str]["rental"] += amount
        elif trans_type == "BIR":
            monthly_data[date_str]["bir"] += amount
        elif trans_type == "SSS":
            monthly_data[date_str]["sss"] += amount
        elif trans_type == "PAG-IBIG":
            monthly_data[date_str]["pag_ibig"] += amount
        elif trans_type == "Purchases":
            monthly_data[date_str]["purchases"] += amount
    
    # Calculate total deductions and net amount for each date
    for date_str in monthly_data:
        day_data = monthly_data[date_str]
        day_data["total_deductions"] = (
            day_data["wages"] +
            day_data["electric_bill"] +
            day_data["water_bill"] +
            day_data["maintenance"] +
            day_data["mayors_permit"] +
            day_data["rental"] +
            day_data["bir"] +
            day_data["sss"] +
            day_data["pag_ibig"] +
            day_data["purchases"]
        )
        day_data["net_amount"] = day_data["daily_collection"] - day_data["total_deductions"]
    
    return jsonify({
        "success": True,
        "monthly_data": monthly_data
    })


@carenderia_bp.route("/view-wages-report")
@login_required
def view_wages_report():
    """View wages report. Accessible to Admin role or Corporate department."""
    user_role = (session.get("role") or "").lower()
    user_dept = (session.get("department") or "").lower()
    
    if user_role != "admin" and user_dept != "corporate":
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("carenderia.carenderia_home"))
    
    return render_template("carenderia/view_wages_report.html")


@carenderia_bp.route("/get-wages-by-month")
@login_required
def get_wages_by_month():
    """Get wages grouped by date for a specific month. Accessible to Admin role or Corporate department."""
    user_role = (session.get("role") or "").lower()
    user_dept = (session.get("department") or "").lower()
    
    if user_role != "admin" and user_dept != "corporate":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    month_str = request.args.get("month")
    if not month_str:
        return jsonify({"success": False, "error": "Month parameter is required."}), 400
    
    try:
        # Parse month string (format: YYYY-MM)
        year, month = map(int, month_str.split("-"))
    except ValueError:
        return jsonify({"success": False, "error": "Invalid month format. Use YYYY-MM."}), 400
    
    # Get all wages for the month
    wages = CarenderiaWage.query.filter(
        extract('year', CarenderiaWage.date) == year,
        extract('month', CarenderiaWage.date) == month
    ).order_by(CarenderiaWage.date.asc(), CarenderiaWage.id.asc()).all()
    
    # Group wages by date
    monthly_data = {}
    
    for wage in wages:
        date_str = wage.date.isoformat() if wage.date else None
        if not date_str:
            continue
        
        if date_str not in monthly_data:
            monthly_data[date_str] = {
                "date": date_str,
                "total_wages": 0,
                "wages": []
            }
        
        amount = float(wage.amount) if wage.amount else 0
        
        # Add wage entry to list
        monthly_data[date_str]["wages"].append({
            "id": wage.id,
            "emp_id": wage.emp_id,
            "emp_name": wage.emp_name or "N/A",
            "emp_role": wage.emp_role or "N/A",
            "emp_rate": float(wage.emp_rate) if wage.emp_rate else 0,
            "amount": amount
        })
        
        # Add to total wages for the date
        monthly_data[date_str]["total_wages"] += amount
    
    return jsonify({
        "success": True,
        "monthly_data": monthly_data
    })


@carenderia_bp.route("/export-trial-balance")
@login_required
def export_trial_balance():
    """Export trial balance (PDF). Accessible to Admin role or Corporate department."""
    user_role = (session.get("role") or "").lower()
    user_dept = (session.get("department") or "").lower()

    if user_role != "admin" and user_dept != "corporate":
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("carenderia.carenderia_home"))

    return render_template("carenderia/export_trial_balance.html")


@carenderia_bp.route("/export-trial-balance/pdf")
@login_required
def export_trial_balance_pdf():
    """Generate a Trial Balance PDF for selected month (start-of-month up to today)."""
    # Local import to avoid hard dependency at app import-time
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
    from reportlab.lib.units import inch
    import os
    user_role = (session.get("role") or "").lower()
    user_dept = (session.get("department") or "").lower()

    if user_role != "admin" and user_dept != "corporate":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    month_str = request.args.get("month")
    if not month_str:
        return jsonify({"success": False, "error": "Month parameter is required."}), 400

    try:
        year, month = map(int, month_str.split("-"))
    except ValueError:
        return jsonify({"success": False, "error": "Invalid month format. Use YYYY-MM."}), 400

    start_date = date(year, month, 1)
    today = date.today()

    if start_date > today:
        return jsonify({"success": False, "error": "Selected month is in the future."}), 400

    last_day = calendar.monthrange(year, month)[1]
    month_end = date(year, month, last_day)
    end_date = min(today, month_end)

    # Fetch transactions within date range
    txns = CarenderiaTransaction.query.filter(
        CarenderiaTransaction.date >= start_date,
        CarenderiaTransaction.date <= end_date
    ).order_by(CarenderiaTransaction.date.asc(), CarenderiaTransaction.id.asc()).all()

    # Group and compute daily totals
    daily = {}
    for t in txns:
        d = t.date.isoformat()
        if d not in daily:
            daily[d] = {
                "daily_collection": 0.0,
                "wages": 0.0,
                "electric_bill": 0.0,
                "water_bill": 0.0,
                "maintenance": 0.0,
                "mayors_permit": 0.0,
                "rental": 0.0,
                "bir": 0.0,
                "sss": 0.0,
                "pag_ibig": 0.0,
                "purchases": 0.0,
                "transactions": []
            }

        amt = float(t.amount) if t.amount else 0.0
        typ = t.trans_type or ""

        daily[d]["transactions"].append({"type": typ, "amount": amt})

        if typ == "Daily Sales":
            daily[d]["daily_collection"] += amt
        elif typ == "Wages":
            daily[d]["wages"] += amt
        elif typ == "Electric Bill":
            daily[d]["electric_bill"] += amt
        elif typ == "Water Bill":
            daily[d]["water_bill"] += amt
        elif typ == "Maintenance":
            daily[d]["maintenance"] += amt
        elif typ == "Mayor's Permit":
            daily[d]["mayors_permit"] += amt
        elif typ == "Rental":
            daily[d]["rental"] += amt
        elif typ == "BIR":
            daily[d]["bir"] += amt
        elif typ == "SSS":
            daily[d]["sss"] += amt
        elif typ == "PAG-IBIG":
            daily[d]["pag_ibig"] += amt
        elif typ == "Purchases":
            daily[d]["purchases"] += amt

    def fmt_money(x: float) -> str:
        return f"{x:,.2f}"
    
    def fmt_date(date_str: str) -> str:
        """Format date string (YYYY-MM-DD) to 'mmm dd, yyyy' format (e.g., 'Jan 19, 2025')."""
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            return f"{months[d.month - 1]} {d.day}, {d.year}"
        except:
            return date_str
    
    def fmt_month(month_str: str) -> str:
        """Format month string (YYYY-MM) to 'mmm yyyy' format (e.g., 'Jan 2025')."""
        try:
            year, month = map(int, month_str.split("-"))
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            return f"{months[month - 1]} {year}"
        except:
            return month_str

    # Build PDF
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="Trial Balance", topMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []

    # Get logo path
    logo_path = os.path.join(current_app.root_path, 'static', 'images', 'wvc_logo.png')
    
    # Create custom styles
    company_style = ParagraphStyle(
        'CompanyStyle',
        parent=styles['Normal'],
        fontSize=16,
        fontName='Helvetica-Bold',
        spaceAfter=0,  # No space after company name
        leading=18  # Set line height to match font size
    )
    
    address_style = ParagraphStyle(
        'AddressStyle',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        spaceBefore=0,  # No space before address
        spaceAfter=12,
        leading=10  # Set line height to match font size
    )
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontSize=18,
        fontName='Helvetica-Bold',
        spaceAfter=12,
        alignment=1  # Center alignment
    )

    # Header with logo and company info in two columns
    # Load logo
    if os.path.exists(logo_path):
        # Adjust logo size
        logo = Image(logo_path, width=0.65*inch, height=0.75*inch)
    else:
        # Fallback if logo not found
        logo = Paragraph("", styles['Normal'])
    
    # Create header table: logo on left (vertically centered), company info on right
    # Combine company name, address, and separator in a nested table for better control
    from reportlab.platypus import KeepTogether
    
    # Create a nested table for the right column content
    right_col_data = [
        [Paragraph("St. Michael Builders Corporation", company_style)],
        [Paragraph("Canjulao, Jagna, Bohol", address_style)],
        [""]  # Separator line row
    ]
    
    right_col_table = Table(right_col_data, colWidths=[5.5*inch])
    right_col_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Left align all text
        ('VALIGN', (0, 0), (0, -1), 'TOP'),  # Top align for compact spacing
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (0, 0), 0),  # No top padding for company name
        ('BOTTOMPADDING', (0, 0), (0, 0), 0),  # No bottom padding for company name
        ('TOPPADDING', (0, 1), (0, 1), 0),  # No top padding for address
        ('BOTTOMPADDING', (0, 1), (0, 1), 0),  # No bottom padding for address
        ('LINEBELOW', (0, 2), (0, 2), 1, colors.black),  # Separator line
        ('TOPPADDING', (0, 2), (0, 2), 0),  # No top padding for separator
        ('BOTTOMPADDING', (0, 2), (0, 2), 0),  # No bottom padding for separator
        ('ROWHEIGHTS', (0, 0), (0, 0), None),  # Auto height for company name
        ('ROWHEIGHTS', (0, 1), (0, 1), None),  # Auto height for address
        ('ROWHEIGHTS', (0, 2), (0, 2), 0.01*inch),  # Minimal height for separator
    ]))
    
    # Main header table with logo and nested right column table
    header_data = [
        [logo, right_col_table]
    ]
    
    header_table = Table(header_data, colWidths=[1.0*inch, 6.0*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),  # Logo vertically centered
        ('VALIGN', (1, 0), (1, 0), 'MIDDLE'),  # Right column content vertically centered
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 12))
    
    # Report title
    story.append(Paragraph("Carenderia Trial Balance", title_style))
    story.append(Paragraph(f"Month: {fmt_month(month_str)}", styles["Normal"]))
    story.append(Paragraph(f"Range: {fmt_date(start_date.isoformat())} to {fmt_date(end_date.isoformat())}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Summary table
    header = ["Date", "Daily Collection", "Total Deductions", "Net Amount"]
    rows = [header]

    total_collection = 0.0
    total_deductions = 0.0

    for d in sorted(daily.keys()):
        dd = daily[d]
        deductions = (
            dd["wages"] + dd["electric_bill"] + dd["water_bill"] + dd["maintenance"] +
            dd["mayors_permit"] + dd["rental"] + dd["bir"] + dd["sss"] +
            dd["pag_ibig"] + dd["purchases"]
        )
        net = dd["daily_collection"] - deductions
        total_collection += dd["daily_collection"]
        total_deductions += deductions
        rows.append([fmt_date(d), fmt_money(dd["daily_collection"]), fmt_money(deductions), fmt_money(net)])

    rows.append(["TOTAL", fmt_money(total_collection), fmt_money(total_deductions), fmt_money(total_collection - total_deductions)])

    table = Table(rows, hAlign="LEFT", colWidths=[90, 120, 120, 120])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
    ]))
    story.append(table)

    story.append(Spacer(1, 14))
    story.append(Paragraph("Details (Transactions by Date)", styles["Heading2"]))
    story.append(Spacer(1, 6))

    for d in sorted(daily.keys()):
        story.append(Paragraph(f"{fmt_date(d)}", styles["Heading3"]))
        tx_rows = [["Type", "Amount"]]
        for tx in daily[d]["transactions"]:
            tx_rows.append([tx["type"], fmt_money(tx["amount"])])
        tx_table = Table(tx_rows, hAlign="LEFT", colWidths=[260, 120])
        tx_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d1e7dd")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ]))
        story.append(tx_table)
        story.append(Spacer(1, 10))

    doc.build(story)
    buf.seek(0)

    filename = f"trial_balance_{month_str}_{start_date.isoformat()}_{end_date.isoformat()}.pdf"
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )
