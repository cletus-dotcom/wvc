from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session, flash, send_file, current_app
from ...extensions import db
from .models import CateringRequest, CateringMenu, CateringEquipment, CateringTransaction, CateringExpense, CateringWage
from app.decorators.auth_decorators import login_required, role_required, department_required
from app.models.core import Employee, Department
from sqlalchemy.orm import joinedload
from sqlalchemy import func, extract
from datetime import datetime
from decimal import Decimal, InvalidOperation
from collections import defaultdict

# Import Employee for CateringExpense relationship
from app.models.core import Employee, Department

from . import catering_bp

def check_catering_access():
    """Check if user has access to Catering. Returns True if allowed, False otherwise."""
    user_dept = (session.get("department") or "").lower()
    allowed_departments = ["catering", "corporate"]
    return user_dept in allowed_departments

# --- Redirect /catering to /catering/home ---
@catering_bp.route("")
@login_required
def catering_root():
    if not check_catering_access():
        return redirect(url_for("core.dashboard"))
    return redirect(url_for("catering.catering_home"))

# Create a new request
@catering_bp.route("/request", methods=["POST"])
@login_required
def create_request():
    data = request.get_json()
    new_request = CateringRequest(
        requestor_name=data.get("requestor_name"),
        event_date=data.get("event_date"),
        event_time=data.get("event_time"),
        items_requested=data.get("items_requested")
    )
    db.session.add(new_request)
    db.session.commit()
    return jsonify({"message": "Catering request created successfully"}), 201

# Get all requests
@catering_bp.route("/requests", methods=["GET"])
@login_required
def get_requests():
    # Adjust this to your real way of identifying requestor/user
    # For now return all (admins vs user filtering can be added)
    requests = CateringRequest.query.all()
    return jsonify([{
        "id": r.id,
        "requestor_name": r.requestor_name,
        "event_date": r.event_date.isoformat() if r.event_date else None,
        "event_time": str(r.event_time) if r.event_time else None,
        "items_requested": r.items_requested,
        "status": r.status
    } for r in requests])

# Update status (Admin only)
@catering_bp.route("/request/<int:request_id>/status", methods=["PUT"])
@role_required("Admin")
def update_status(request_id):
    data = request.get_json()
    req = CateringRequest.query.get_or_404(request_id)
    req.status = data.get("status", req.status)
    db.session.commit()
    return jsonify({"message": f"Request {request_id} status updated to {req.status}"})

@catering_bp.route("/home")
@login_required
def catering_home():
    if not check_catering_access():
        return redirect(url_for("core.dashboard"))
    # Get confirmed bookings ordered by event date and time
    confirmed_bookings = CateringRequest.query.filter_by(status="Confirmed")\
        .order_by(CateringRequest.event_date.asc(), CateringRequest.event_time.asc()).all()
    return render_template("catering/home.html", confirmed_bookings=confirmed_bookings)


@catering_bp.route("/manage-employee")
@login_required
@department_required("Catering", "Corporate")
def manage_employee():
    """Manage employees for Catering department."""
    # Get Catering department
    catering_dept = Department.query.filter_by(name="Catering").first()
    
    if not catering_dept:
        # If Catering department doesn't exist, return empty list
        employees = []
    else:
        # Eager load the department relationship to prevent N+1 queries
        # Filter to only show employees from Catering department
        employees = Employee.query.filter_by(department_id=catering_dept.id) \
                                  .options(joinedload(Employee.department)) \
                                  .order_by(Employee.name.asc()).all()
    
    departments = Department.query.order_by(Department.name.asc()).all()

    return render_template(
        "catering/manage_employee.html",
        employees=employees,
        departments=departments
    )


@catering_bp.route("/add-employee", methods=["POST"])
@login_required
@department_required("Catering", "Corporate")
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


@catering_bp.route("/edit-employee/<int:emp_id>", methods=["POST"])
@login_required
@department_required("Catering", "Corporate")
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
    return redirect(url_for("catering.manage_employee"))


@catering_bp.route("/delete-employee/<int:emp_id>")
@login_required
@department_required("Catering", "Corporate")
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
    return redirect(url_for("catering.manage_employee"))


@catering_bp.route("/employee-names")
@login_required
@department_required("Catering", "Corporate")
def employee_names():
    """Get list of employee names for autocomplete (Catering department only)."""
    catering_dept = Department.query.filter_by(name="Catering").first()
    if not catering_dept:
        return jsonify({"names": []})
    
    names = [emp.name for emp in Employee.query.filter_by(department_id=catering_dept.id) \
                                          .order_by(Employee.name.asc()).all()]
    return jsonify({"names": names})


@catering_bp.route("/manage-menu")
@login_required
@department_required("Catering", "Corporate")
def manage_menu():
    """Manage menu items for Catering department."""
    menu_items = CateringMenu.query.order_by(CateringMenu.description.asc()).all()
    return render_template("catering/manage_menu.html", menu_items=menu_items)


@catering_bp.route("/add-menu-item", methods=["POST"])
@login_required
@department_required("Catering", "Corporate")
def add_menu_item():
    """Add a new menu item."""
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "").strip()

    if not description or not price:
        return jsonify({"success": False, "error": "Description and price are required."})

    try:
        price_value = float(price)
        if price_value < 0:
            return jsonify({"success": False, "error": "Price must be a positive number."})
    except ValueError:
        return jsonify({"success": False, "error": "Invalid price format."})

    new_item = CateringMenu(
        description=description,
        price=price_value
    )
    db.session.add(new_item)
    db.session.commit()

    return jsonify({
        "success": True,
        "menu_item": {
            "id": new_item.id,
            "description": new_item.description,
            "price": str(new_item.price)
        }
    })


@catering_bp.route("/edit-menu-item/<int:item_id>", methods=["POST"])
@login_required
@department_required("Catering", "Corporate")
def edit_menu_item(item_id):
    """Edit an existing menu item."""
    item = CateringMenu.query.get_or_404(item_id)
    
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "").strip()

    if not description or not price:
        return jsonify({"success": False, "error": "Description and price are required."})

    try:
        price_value = float(price)
        if price_value < 0:
            return jsonify({"success": False, "error": "Price must be a positive number."})
    except ValueError:
        return jsonify({"success": False, "error": "Invalid price format."})

    item.description = description
    item.price = price_value

    db.session.commit()

    # Check for AJAX request
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "success": True,
            "menu_item": {
                "id": item.id,
                "description": item.description,
                "price": str(item.price)
            }
        })

    flash("Menu item updated successfully!", "success")
    return redirect(url_for("catering.manage_menu"))


@catering_bp.route("/delete-menu-item/<int:item_id>")
@login_required
@department_required("Catering", "Corporate")
def delete_menu_item(item_id):
    """Delete a menu item."""
    item = CateringMenu.query.get_or_404(item_id)
    try:
        db.session.delete(item)
        db.session.commit()
        flash("Menu item deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Cannot delete menu item. It may be linked to other records.", "danger")
    return redirect(url_for("catering.manage_menu"))


@catering_bp.route("/manage-equipment")
@login_required
@department_required("Catering", "Corporate")
def manage_equipment():
    """Manage equipment for Catering department."""
    equipment_items = CateringEquipment.query.order_by(CateringEquipment.description.asc()).all()
    return render_template("catering/manage_equipment.html", equipment_items=equipment_items)


@catering_bp.route("/add-equipment-item", methods=["POST"])
@login_required
@department_required("Catering", "Corporate")
def add_equipment_item():
    """Add a new equipment item."""
    description = request.form.get("description", "").strip()
    rent_price = request.form.get("rent_price", "").strip()

    if not description or not rent_price:
        return jsonify({"success": False, "error": "Description and rent price are required."})

    try:
        price_value = float(rent_price)
        if price_value < 0:
            return jsonify({"success": False, "error": "Rent price must be a positive number."})
    except ValueError:
        return jsonify({"success": False, "error": "Invalid rent price format."})

    new_item = CateringEquipment(
        description=description,
        rent_price=price_value
    )
    db.session.add(new_item)
    db.session.commit()

    return jsonify({
        "success": True,
        "equipment_item": {
            "id": new_item.id,
            "description": new_item.description,
            "rent_price": str(new_item.rent_price)
        }
    })


@catering_bp.route("/edit-equipment-item/<int:item_id>", methods=["POST"])
@login_required
@department_required("Catering", "Corporate")
def edit_equipment_item(item_id):
    """Edit an existing equipment item."""
    item = CateringEquipment.query.get_or_404(item_id)
    
    description = request.form.get("description", "").strip()
    rent_price = request.form.get("rent_price", "").strip()

    if not description or not rent_price:
        return jsonify({"success": False, "error": "Description and rent price are required."})

    try:
        price_value = float(rent_price)
        if price_value < 0:
            return jsonify({"success": False, "error": "Rent price must be a positive number."})
    except ValueError:
        return jsonify({"success": False, "error": "Invalid rent price format."})

    item.description = description
    item.rent_price = price_value

    db.session.commit()

    # Check for AJAX request
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "success": True,
            "equipment_item": {
                "id": item.id,
                "description": item.description,
                "rent_price": str(item.rent_price)
            }
        })

    flash("Equipment item updated successfully!", "success")
    return redirect(url_for("catering.manage_equipment"))


@catering_bp.route("/delete-equipment-item/<int:item_id>")
@login_required
@department_required("Catering", "Corporate")
def delete_equipment_item(item_id):
    """Delete an equipment item."""
    item = CateringEquipment.query.get_or_404(item_id)
    try:
        db.session.delete(item)
        db.session.commit()
        flash("Equipment item deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Cannot delete equipment item. It may be linked to other records.", "danger")
    return redirect(url_for("catering.manage_equipment"))


@catering_bp.route("/add-transaction", methods=["POST"])
@login_required
@department_required("Catering", "Corporate")
def add_transaction():
    """Add a financial transaction for a booking."""
    booking_id = request.form.get("booking_id", "").strip()
    date_str = request.form.get("date", "").strip()
    booking_amount = request.form.get("booking_amount", "").strip()
    trans_description = request.form.get("trans_description", "").strip()
    trans_amount = request.form.get("trans_amount", "").strip()
    remarks = request.form.get("remarks", "").strip()

    if not booking_id or not date_str or not booking_amount or not trans_description or not trans_amount:
        return jsonify({"success": False, "error": "All required fields must be filled."})

    try:
        trans_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date format."})

    try:
        # Use Decimal for currency math (Numeric columns return Decimal)
        booking_amount_value = Decimal(booking_amount)
        trans_amount_value = Decimal(trans_amount)
    except (InvalidOperation, ValueError):
        return jsonify({"success": False, "error": "Invalid amount format."})

    # Verify booking exists
    booking = CateringRequest.query.get(int(booking_id))
    if not booking:
        return jsonify({"success": False, "error": "Booking not found."})

    new_transaction = CateringTransaction(
        date=trans_date,
        booking_id=int(booking_id),
        booking_amount=booking_amount_value,
        trans_description=trans_description,
        trans_amount=trans_amount_value,
        remarks=remarks if remarks else None
    )

    try:
        # Calculate total of existing transactions (before adding the new one)
        existing_total = db.session.query(func.coalesce(func.sum(CateringTransaction.trans_amount), 0))\
            .filter(CateringTransaction.booking_id == int(booking_id))\
            .scalar()
        if not isinstance(existing_total, Decimal):
            existing_total = Decimal(str(existing_total or 0))
        
        # Calculate running balance after adding this transaction
        total_after_transaction = existing_total + trans_amount_value
        running_balance = booking_amount_value - total_after_transaction
        
        # If it's a full payment and running balance is 0 (or very close to 0), update status to Completed
        booking_status_updated = False
        if trans_description == "Full Payment" and abs(running_balance) <= Decimal("0.01"):
            booking.status = "Completed"
            booking_status_updated = True
        
        # Add the transaction to the session
        db.session.add(new_transaction)
        db.session.commit()

        return jsonify({
            "success": True,
            "transaction": {
                "id": new_transaction.id,
                "date": new_transaction.date.isoformat() if new_transaction.date else None,
                "booking_id": new_transaction.booking_id,
                "booking_amount": str(new_transaction.booking_amount),
                "trans_description": new_transaction.trans_description,
                "trans_amount": str(new_transaction.trans_amount),
                "remarks": new_transaction.remarks
            },
            "booking_status_updated": booking_status_updated,
            "running_balance": float(running_balance)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@catering_bp.route("/booking-transaction-total/<int:booking_id>")
@login_required
@department_required("Catering", "Corporate")
def booking_transaction_total(booking_id):
    """Return total trans_amount for a booking."""
    total = (
        db.session.query(func.coalesce(func.sum(CateringTransaction.trans_amount), 0))
        .filter(CateringTransaction.booking_id == booking_id)
        .scalar()
    )
    return jsonify({"success": True, "total": float(total or 0)})


@catering_bp.route("/manage-bookings")
@login_required
def manage_bookings():
    """Manage catering bookings. Accessible to Admin role or Corporate department."""
    user_role = (session.get("role") or "").lower()
    user_dept = (session.get("department") or "").lower()
    
    if user_role != "admin" and user_dept != "corporate":
        flash("You do not have permission to access this page.", "danger")
        return redirect(url_for("catering.catering_home"))
    
    bookings = CateringRequest.query.order_by(CateringRequest.event_date.desc(), CateringRequest.event_time.desc()).all()
    menu_items = CateringMenu.query.order_by(CateringMenu.description.asc()).all()
    equipment_items = CateringEquipment.query.order_by(CateringEquipment.description.asc()).all()
    
    return render_template(
        "catering/manage_bookings.html",
        bookings=bookings,
        menu_items=menu_items,
        equipment_items=equipment_items
    )


@catering_bp.route("/add-booking", methods=["POST"])
@login_required
def add_booking():
    """Add a new catering booking. Accessible to Admin role or Corporate department."""
    user_role = (session.get("role") or "").lower()
    user_dept = (session.get("department") or "").lower()
    
    if user_role != "admin" and user_dept != "corporate":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    requestor_name = request.form.get("requestor_name", "").strip()
    customer_address = request.form.get("customer_address", "").strip()
    contact_number = request.form.get("contact_number", "").strip()
    email_address = request.form.get("email_address", "").strip()
    event_date_str = request.form.get("event_date", "")
    event_time_str = request.form.get("event_time", "")
    items_requested = request.form.get("items_requested", "").strip()
    status = request.form.get("status", "Pending").strip()
    
    if not requestor_name or not customer_address or not contact_number or not event_date_str or not event_time_str or not items_requested:
        return jsonify({"success": False, "error": "All required fields must be filled."})
    
    try:
        event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
        event_time = datetime.strptime(event_time_str, "%H:%M").time()
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date or time format."})
    
    new_booking = CateringRequest(
        requestor_name=requestor_name,
        customer_address=customer_address,
        contact_number=contact_number,
        email_address=email_address if email_address else None,
        event_date=event_date,
        event_time=event_time,
        items_requested=items_requested,
        status=status
    )
    
    try:
        db.session.add(new_booking)
        db.session.commit()
        
        return jsonify({
            "success": True,
                "booking": {
                    "id": new_booking.id,
                    "requestor_name": new_booking.requestor_name,
                    "customer_address": new_booking.customer_address,
                    "contact_number": new_booking.contact_number,
                    "email_address": new_booking.email_address,
                    "event_date": new_booking.event_date.isoformat() if new_booking.event_date else None,
                    "event_time": new_booking.event_time.strftime("%H:%M") if new_booking.event_time else None,
                    "items_requested": new_booking.items_requested,
                    "status": new_booking.status
                }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@catering_bp.route("/edit-booking/<int:booking_id>", methods=["POST"])
@login_required
def edit_booking(booking_id):
    """Edit an existing catering booking. Accessible to Admin role or Corporate department."""
    user_role = (session.get("role") or "").lower()
    user_dept = (session.get("department") or "").lower()
    
    if user_role != "admin" and user_dept != "corporate":
        return jsonify({"success": False, "error": "Unauthorized"}), 403
    
    booking = CateringRequest.query.get_or_404(booking_id)
    
    requestor_name = request.form.get("requestor_name", "").strip()
    customer_address = request.form.get("customer_address", "").strip()
    contact_number = request.form.get("contact_number", "").strip()
    email_address = request.form.get("email_address", "").strip()
    event_date_str = request.form.get("event_date", "")
    event_time_str = request.form.get("event_time", "")
    items_requested = request.form.get("items_requested", "").strip()
    status = request.form.get("status", "Pending").strip()
    
    if not requestor_name or not customer_address or not contact_number or not event_date_str or not event_time_str or not items_requested:
        return jsonify({"success": False, "error": "All required fields must be filled."})
    
    try:
        event_date = datetime.strptime(event_date_str, "%Y-%m-%d").date()
        event_time = datetime.strptime(event_time_str, "%H:%M").time()
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date or time format."})
    
    booking.requestor_name = requestor_name
    booking.customer_address = customer_address
    booking.contact_number = contact_number
    booking.email_address = email_address if email_address else None
    booking.event_date = event_date
    booking.event_time = event_time
    booking.items_requested = items_requested
    booking.status = status
    booking.updated_at = datetime.utcnow()
    
    try:
        db.session.commit()
        
        # Check for AJAX request
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({
                "success": True,
                "booking": {
                    "id": booking.id,
                    "requestor_name": booking.requestor_name,
                    "customer_address": booking.customer_address,
                    "contact_number": booking.contact_number,
                    "email_address": booking.email_address,
                    "event_date": booking.event_date.isoformat() if booking.event_date else None,
                    "event_time": booking.event_time.strftime("%H:%M") if booking.event_time else None,
                    "items_requested": booking.items_requested,
                    "status": booking.status
                }
            })
        
        flash("Booking updated successfully!", "success")
        return redirect(url_for("catering.manage_bookings"))
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@catering_bp.route("/delete-booking/<int:booking_id>")
@login_required
def delete_booking(booking_id):
    """Delete a catering booking. Accessible to Admin role or Corporate department."""
    user_role = (session.get("role") or "").lower()
    user_dept = (session.get("department") or "").lower()
    
    if user_role != "admin" and user_dept != "corporate":
        flash("You do not have permission to perform this action.", "danger")
        return redirect(url_for("catering.catering_home"))
    
    booking = CateringRequest.query.get_or_404(booking_id)
    
    try:
        db.session.delete(booking)
        db.session.commit()
        flash("Booking deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Cannot delete booking. It may be linked to other records.", "danger")
    
    return redirect(url_for("catering.manage_bookings"))


@catering_bp.route("/add-expense", methods=["POST"])
@login_required
@department_required("Catering", "Corporate")
def add_expense():
    """Add an expense (Wages, Expenses, or Miscellaneous) for catering."""
    date_str = request.form.get("date", "").strip()
    expense_type = request.form.get("expense_type", "").strip()
    amount = request.form.get("amount", "").strip()
    description = request.form.get("description", "").strip()
    employee_id = request.form.get("employee_id", "").strip()
    employee_name = request.form.get("employee_name", "").strip()
    remarks = request.form.get("remarks", "").strip()

    if not date_str or not expense_type or not amount:
        return jsonify({"success": False, "error": "Date, expense type, and amount are required."})

    try:
        expense_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        amount_value = Decimal(amount)
    except (ValueError, InvalidOperation):
        return jsonify({"success": False, "error": "Invalid date or amount format."})

    new_expense = CateringExpense(
        date=expense_date,
        expense_type=expense_type,
        amount=amount_value,
        description=description if description else None,
        employee_id=int(employee_id) if employee_id else None,
        employee_name=employee_name if employee_name else None,
        remarks=remarks if remarks else None
    )

    try:
        db.session.add(new_expense)
        db.session.commit()

        return jsonify({
            "success": True,
            "expense": {
                "id": new_expense.id,
                "date": new_expense.date.isoformat() if new_expense.date else None,
                "expense_type": new_expense.expense_type,
                "amount": str(new_expense.amount),
                "description": new_expense.description,
                "employee_name": new_expense.employee_name,
                "remarks": new_expense.remarks
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@catering_bp.route("/catering-employees")
@login_required
@department_required("Catering", "Corporate")
def catering_employees():
    """Get list of catering employees for wages."""
    catering_dept = Department.query.filter_by(name="Catering").first()
    if not catering_dept:
        return jsonify({"employees": []})
    
    employees = Employee.query.filter_by(department_id=catering_dept.id)\
        .order_by(Employee.name.asc()).all()
    
    return jsonify({
        "employees": [{
            "id": emp.id,
            "name": emp.name,
            "role": emp.role,
            "rate_per_day": str(emp.rate_per_day) if emp.rate_per_day else None
        } for emp in employees]
    })


@catering_bp.route("/add-wages", methods=["POST"])
@login_required
@department_required("Catering", "Corporate")
def add_wages():
    """Add wages for multiple employees. Expects JSON with array of wage entries."""
    data = request.get_json() or {}
    wages = data.get("wages", [])
    date_str = data.get("date", "").strip()
    description = data.get("description", "Wages").strip()

    if not date_str or not wages:
        return jsonify({"success": False, "error": "Date and at least one wage entry are required."})

    try:
        expense_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"success": False, "error": "Invalid date format."})

    try:
        wage_entries = []
        for wage in wages:
            employee_id = wage.get("employee_id")
            employee_name = wage.get("employee_name", "").strip()
            rate_per_day = Decimal(str(wage.get("rate_per_day", 0)))
            number_of_days = Decimal(str(wage.get("number_of_days", 0)))
            amount = Decimal(str(wage.get("amount", 0)))

            if not employee_id or not employee_name or rate_per_day <= 0 or number_of_days <= 0:
                continue

            new_wage = CateringWage(
                date=expense_date,
                employee_id=int(employee_id),
                employee_name=employee_name,
                rate_per_day=rate_per_day,
                number_of_days=number_of_days,
                amount=amount,
                description=description
            )
            wage_entries.append(new_wage)
            db.session.add(new_wage)

        if not wage_entries:
            return jsonify({"success": False, "error": "No valid wage entries provided."})

        # Calculate total wages amount
        total_wages_amount = sum(entry.amount for entry in wage_entries)
        
        # Also save to catering_expense table as a single Wages expense entry
        wages_expense = CateringExpense(
            date=expense_date,
            expense_type="Wages",
            amount=total_wages_amount,
            description=description,
            employee_id=None,  # Not specific to one employee
            employee_name=None,
            remarks=f"Wages for {len(wage_entries)} employee(s)"
        )
        db.session.add(wages_expense)
        
        db.session.commit()

        return jsonify({
            "success": True,
            "message": f"Successfully added {len(wage_entries)} wage entry/entries.",
            "wages": [{
                "id": wage.id,
                "employee_id": wage.employee_id,
                "employee_name": wage.employee_name,
                "rate_per_day": str(wage.rate_per_day),
                "number_of_days": str(wage.number_of_days),
                "amount": str(wage.amount)
            } for wage in wage_entries],
            "expense_id": wages_expense.id,
            "total_amount": str(total_wages_amount)
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@catering_bp.route("/view-wages")
@login_required
@department_required("Catering", "Corporate")
def view_wages():
    """View wages report categorized by month with per day details."""
    # Get selected month from query parameter (format: YYYY-MM)
    selected_month = request.args.get("month", "")
    
    # Get all wages ordered by date
    query = CateringWage.query
    
    # Filter by month if provided
    if selected_month:
        try:
            year, month = map(int, selected_month.split("-"))
            query = query.filter(
                extract('year', CateringWage.date) == year,
                extract('month', CateringWage.date) == month
            )
        except (ValueError, AttributeError):
            # Invalid month format, ignore filter
            pass
    
    all_wages = query.order_by(CateringWage.date.desc()).all()
    
    # Get all available months for the dropdown
    all_months_query = db.session.query(
        extract('year', CateringWage.date).label('year'),
        extract('month', CateringWage.date).label('month')
    ).distinct().order_by(
        extract('year', CateringWage.date).desc(),
        extract('month', CateringWage.date).desc()
    ).all()
    
    available_months = []
    for year, month in all_months_query:
        month_str = f"{int(year)}-{int(month):02d}"
        month_name = datetime(int(year), int(month), 1).strftime("%B %Y")
        available_months.append({
            "value": month_str,
            "label": month_name
        })
    
    # Group wages by year-month and then by date
    wages_by_month = defaultdict(lambda: defaultdict(list))
    
    for wage in all_wages:
        year_month = wage.date.strftime("%Y-%m")
        month_name = wage.date.strftime("%B %Y")
        date_key = wage.date.isoformat()
        
        wages_by_month[month_name][date_key].append({
            "id": wage.id,
            "date": wage.date,
            "employee_id": wage.employee_id,
            "employee_name": wage.employee_name,
            "rate_per_day": wage.rate_per_day,
            "number_of_days": wage.number_of_days,
            "amount": wage.amount,
            "description": wage.description
        })
    
    # Convert to sorted list format for template
    monthly_data = []
    for month_name in sorted(wages_by_month.keys(), reverse=True):
        month_wages = wages_by_month[month_name]
        daily_data = []
        month_total = Decimal("0")
        
        # Sort dates within month
        for date_key in sorted(month_wages.keys(), reverse=True):
            day_wages = month_wages[date_key]
            day_total = sum(Decimal(str(w["amount"])) for w in day_wages)
            month_total += day_total
            
            daily_data.append({
                "date": day_wages[0]["date"],
                "wages": day_wages,
                "day_total": day_total
            })
        
        monthly_data.append({
            "month_name": month_name,
            "daily_data": daily_data,
            "month_total": month_total
        })
    
    return render_template("catering/view_wages.html", 
                          monthly_data=monthly_data,
                          available_months=available_months,
                          selected_month=selected_month)


@catering_bp.route("/view-balance-sheet")
@login_required
@department_required("Catering", "Corporate")
def view_balance_sheet():
    """View balance sheet (income vs expenses) with month selection and daily details."""
    selected_month = request.args.get("month", "")

    # --- month filter ---
    year = month = None
    if selected_month:
        try:
            year, month = map(int, selected_month.split("-"))
        except (ValueError, AttributeError):
            year = month = None

    # --- available months: union of months that appear in income (booking payments) or expenses ---
    income_months = db.session.query(
        extract("year", CateringTransaction.date).label("year"),
        extract("month", CateringTransaction.date).label("month"),
    ).filter(CateringTransaction.booking_id.isnot(None)).distinct()

    expense_months = db.session.query(
        extract("year", CateringExpense.date).label("year"),
        extract("month", CateringExpense.date).label("month"),
    ).distinct()

    month_set = {(int(y), int(m)) for (y, m) in income_months.union(expense_months).all()}
    available_months = []
    for y, m in sorted(month_set, reverse=True):
        available_months.append({
            "value": f"{y}-{m:02d}",
            "label": datetime(y, m, 1).strftime("%B %Y")
        })

    # --- fetch rows ---
    income_q = CateringTransaction.query.filter(CateringTransaction.booking_id.isnot(None))
    expense_q = CateringExpense.query

    if year and month:
        income_q = income_q.filter(
            extract("year", CateringTransaction.date) == year,
            extract("month", CateringTransaction.date) == month,
        )
        expense_q = expense_q.filter(
            extract("year", CateringExpense.date) == year,
            extract("month", CateringExpense.date) == month,
        )

    incomes = income_q.order_by(CateringTransaction.date.desc(), CateringTransaction.id.desc()).all()
    expenses = expense_q.order_by(CateringExpense.date.desc(), CateringExpense.id.desc()).all()

    # --- group by day ---
    by_day = defaultdict(lambda: {"income": [], "expenses": []})
    for t in incomes:
        by_day[t.date]["income"].append(t)
    for e in expenses:
        by_day[e.date]["expenses"].append(e)

    daily_rows = []
    total_income = Decimal("0")
    total_wages = Decimal("0")
    total_expenses_other = Decimal("0")

    for day in sorted(by_day.keys(), reverse=True):
        day_incomes = by_day[day]["income"]
        day_expenses = by_day[day]["expenses"]

        day_income_total = sum((Decimal(str(x.trans_amount or 0)) for x in day_incomes), Decimal("0"))
        day_wages_total = sum((Decimal(str(x.amount or 0)) for x in day_expenses if (x.expense_type or "") == "Wages"), Decimal("0"))
        day_other_total = sum((Decimal(str(x.amount or 0)) for x in day_expenses if (x.expense_type or "") != "Wages"), Decimal("0"))
        day_expense_total = day_wages_total + day_other_total
        day_net = day_income_total - day_expense_total

        total_income += day_income_total
        total_wages += day_wages_total
        total_expenses_other += day_other_total

        daily_rows.append({
            "date": day,
            "income_total": day_income_total,
            "wages_total": day_wages_total,
            "other_expenses_total": day_other_total,
            "expense_total": day_expense_total,
            "net": day_net,
            "income_items": day_incomes,
            "expense_items": day_expenses,
        })

    summary = {
        "total_income": total_income,
        "total_wages": total_wages,
        "total_other_expenses": total_expenses_other,
        "total_expenses": total_wages + total_expenses_other,
        "net": total_income - (total_wages + total_expenses_other),
    }

    return render_template(
        "catering/view_balance_sheet.html",
        available_months=available_months,
        selected_month=selected_month,
        daily_rows=daily_rows,
        summary=summary,
    )


@catering_bp.route("/export-balance-sheet/pdf")
@login_required
@department_required("Catering", "Corporate")
def export_balance_sheet_pdf():
    """Generate a Balance Sheet PDF for selected month."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
    from reportlab.lib.units import inch
    import io
    import os
    from datetime import date, datetime
    
    month_str = request.args.get("month")
    if not month_str:
        return jsonify({"success": False, "error": "Month parameter is required."}), 400
    
    try:
        year, month = map(int, month_str.split("-"))
    except ValueError:
        return jsonify({"success": False, "error": "Invalid month format. Use YYYY-MM."}), 400
    
    # Fetch data (same logic as view_balance_sheet)
    income_q = CateringTransaction.query.filter(
        CateringTransaction.booking_id.isnot(None),
        extract("year", CateringTransaction.date) == year,
        extract("month", CateringTransaction.date) == month,
    )
    expense_q = CateringExpense.query.filter(
        extract("year", CateringExpense.date) == year,
        extract("month", CateringExpense.date) == month,
    )
    
    income_rows = income_q.order_by(CateringTransaction.date.asc()).all()
    expense_rows = expense_q.order_by(CateringExpense.date.asc()).all()
    
    # Group by date
    by_day = defaultdict(lambda: {"income": [], "expenses": []})
    for t in income_rows:
        by_day[t.date]["income"].append(t)
    for e in expense_rows:
        by_day[e.date]["expenses"].append(e)
    
    # Calculate totals
    total_income = sum(Decimal(str(t.trans_amount or 0)) for t in income_rows)
    total_wages = sum(Decimal(str(e.amount or 0)) for e in expense_rows if (e.expense_type or "") == "Wages")
    total_other_expenses = sum(Decimal(str(e.amount or 0)) for e in expense_rows if (e.expense_type or "") != "Wages")
    total_expenses = total_wages + total_other_expenses
    net = total_income - total_expenses
    
    # Build PDF
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="Balance Sheet")
    styles = getSampleStyleSheet()
    story = []
    
    # Get logo path
    logo_path = os.path.join(current_app.root_path, "static", "images", "wvc_logo.png")

    # Create custom styles (match carenderia export_trial_balance header)
    company_style = ParagraphStyle(
        "CompanyStyle",
        parent=styles["Normal"],
        fontSize=16,
        fontName="Helvetica-Bold",
        spaceAfter=0,  # No space after company name
        leading=18,  # Set line height to match font size
    )

    address_style = ParagraphStyle(
        "AddressStyle",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Helvetica",
        spaceBefore=0,  # No space before address
        spaceAfter=12,
        leading=10,  # Set line height to match font size
    )

    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontSize=18,
        fontName="Helvetica-Bold",
        spaceAfter=12,
        alignment=1,  # Center alignment
    )

    # Header with logo and company info in two columns (match export_trial_balance)
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=1.2 * inch, height=1.2 * inch)
    else:
        logo = Paragraph("", styles["Normal"])

    right_col_data = [
        [Paragraph("St. Michael Builders Corporation", company_style)],
        [Paragraph("Canjulao, Jagna, Bohol", address_style)],
        [""],  # Separator line row
    ]
    right_col_table = Table(right_col_data, colWidths=[5.5 * inch])
    right_col_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("VALIGN", (0, 0), (0, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (0, 0), 0),
                ("BOTTOMPADDING", (0, 0), (0, 0), 0),
                ("TOPPADDING", (0, 1), (0, 1), 0),
                ("BOTTOMPADDING", (0, 1), (0, 1), 0),
                ("LINEBELOW", (0, 2), (0, 2), 1, colors.black),
                ("TOPPADDING", (0, 2), (0, 2), 0),
                ("BOTTOMPADDING", (0, 2), (0, 2), 0),
                ("ROWHEIGHTS", (0, 2), (0, 2), 0.01 * inch),
            ]
        )
    )

    header_table = Table([[logo, right_col_table]], colWidths=[1.5 * inch, 5.5 * inch])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
                ("VALIGN", (1, 0), (1, 0), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story.append(header_table)
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Balance Sheet", title_style))
    story.append(Paragraph(f"Period: {datetime(year, month, 1).strftime('%B %Y')}", styles["Normal"]))
    story.append(Spacer(1, 0.25 * inch))
    
    # Summary Table
    summary_data = [
        ['Item', 'Amount'],
        ['Total Income', f"{total_income:,.2f}"],
        ['Total Wages', f"{total_wages:,.2f}"],
        ['Other Expenses', f"{total_other_expenses:,.2f}"],
        ['Total Expenses', f"{total_expenses:,.2f}"],
        ['Net', f"{net:,.2f}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[4*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(Paragraph("Summary", styles['Heading2']))
    story.append(Spacer(1, 0.1*inch))
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Daily Details (single header row table)
    story.append(Paragraph("Daily Details", styles["Heading2"]))
    story.append(Spacer(1, 0.1 * inch))

    daily_details = [["Date", "Income", "Wages", "Other Exp.", "Total Exp.", "Net"]]
    for day in sorted(by_day.keys(), reverse=False):
        day_incomes = by_day[day]["income"]
        day_expenses = by_day[day]["expenses"]

        day_income_total = sum(Decimal(str(t.trans_amount or 0)) for t in day_incomes)
        day_wages = sum(Decimal(str(e.amount or 0)) for e in day_expenses if (e.expense_type or "") == "Wages")
        day_other = sum(Decimal(str(e.amount or 0)) for e in day_expenses if (e.expense_type or "") != "Wages")
        day_total_expenses = day_wages + day_other
        day_net = day_income_total - day_total_expenses

        daily_details.append([
            day.strftime("%b %d, %Y"),
            f"{day_income_total:,.2f}",
            f"{day_wages:,.2f}",
            f"{day_other:,.2f}",
            f"{day_total_expenses:,.2f}",
            f"{day_net:,.2f}",
        ])

    daily_table = Table(
        daily_details,
        colWidths=[1.35 * inch, 1.0 * inch, 0.95 * inch, 1.1 * inch, 1.1 * inch, 1.0 * inch],
        repeatRows=1,
    )
    daily_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ]
        )
    )
    story.append(daily_table)
    
    # Build PDF
    doc.build(story)
    buf.seek(0)
    
    # Generate filename
    month_name = datetime(year, month, 1).strftime("%B_%Y")
    filename = f"balance_sheet_{month_name}.pdf"
    
    return send_file(
        buf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename
    )
