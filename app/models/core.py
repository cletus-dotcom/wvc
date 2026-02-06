# app/models/core.py
from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from ..extensions import db
from sqlalchemy.orm import joinedload

from app.decorators.auth_decorators import (
    login_required,
    role_required,
    department_required
)

core_bp = Blueprint(
    "core",
    __name__,
    template_folder="templates/core"
)

class Department(db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)

class Employee(db.Model):
    __tablename__ = "employees"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(100))
    rate_per_day = db.Column(db.Float, nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    department = db.relationship("Department", backref="employees", lazy=True)

@core_bp.route("/")
def dashboard():
    ventures = [
        {
            "name": "Construction",
            "url": "/construction",
            "icon": "bi-building",
            "color": "bg-primary",
            "description": "Manage all construction projects and site operations."
        },
        {
            "name": "Carenderia",
            "url": "/carenderia",
            "icon": "bi-basket",
            "color": "bg-danger",
            "description": "Track daily carenderia operations and sales."
        },
        {
            "name": "Catering",
            "url": "/catering",
            "icon": "bi-egg-fried",
            "color": "bg-warning text-dark",
            "description": "Handle catering events, orders, and logistics."
        },
    ]

    return render_template("core/dashboard.html", ventures=ventures)

@core_bp.route("/venture/construction")
@login_required
def go_construction():
    department = session.get("department", "").lower()
    if department in ["construction", "corporate"]:
        return redirect(url_for("construction.construction_home"))
    else:
        flash("You must be in Construction or Corporate to access this module.", "warning")
        return redirect(url_for("auth.login"))

@core_bp.route("/manage-department")
@login_required
@department_required("Corporate")   # Only Corporate can access
def manage_department():
    from .core import Department
    depts = Department.query.order_by(Department.name.asc()).all()
    return render_template("core/manage_department.html", departments=depts)

@core_bp.route("/add-department", methods=["POST"])
@login_required
@department_required("Corporate")
def add_department():
    name = request.form.get("name", "").strip()

    if not name:
        flash("Department name cannot be empty.", "danger")
        return redirect(url_for("core.manage_department"))

    # Check if department already exists
    existing = Department.query.filter_by(name=name).first()
    if existing:
        flash("Department already exists.", "warning")
        return redirect(url_for("core.manage_department"))

    # Create new department
    new_dept = Department(name=name)
    db.session.add(new_dept)
    db.session.commit()

    flash("Department added successfully!", "success")
    return redirect(url_for("core.manage_department"))

@core_bp.route("/edit-department/<int:dept_id>", methods=["POST", "GET"])
@login_required
@department_required("Corporate")
def edit_department(dept_id):
    dept = Department.query.get_or_404(dept_id)

    if request.method == "POST":
        new_name = request.form.get("name", "").strip()

        if not new_name:
            flash("Department name cannot be empty.", "danger")
            return redirect(url_for("core.manage_department"))

        # Check for duplicates (excluding itself)
        exists = Department.query.filter(
            Department.name == new_name,
            Department.id != dept_id
        ).first()

        if exists:
            flash("Another department with this name already exists.", "warning")
            return redirect(url_for("core.manage_department"))

        dept.name = new_name
        db.session.commit()

        flash("Department updated successfully!", "success")
        return redirect(url_for("core.manage_department"))

    # GET request → show the edit modal/page
    return render_template("core/edit_department.html", dept=dept)

@core_bp.route("/delete-department/<int:dept_id>")
@login_required
@department_required("Corporate")
def delete_department(dept_id):
    dept = Department.query.get_or_404(dept_id)

    try:
        db.session.delete(dept)
        db.session.commit()
        flash("Department deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Cannot delete department. It may be linked to employees or other records.", "danger")

    return redirect(url_for("core.manage_department"))



@core_bp.route("/manage-employees")
@login_required
@role_required(["Admin", "Staff"])
@department_required(["Construction", "Corporate"])
def manage_employees():
    # Eager load the department relationship to prevent N+1 queries
    # Filter to only show employees from Construction department
    construction_dept = Department.query.filter_by(name="Construction").first()
    if not construction_dept:
        employees = []
    else:
        employees = (
            Employee.query.filter_by(department_id=construction_dept.id)
            .options(joinedload(Employee.department))
            .order_by(Employee.name.asc())
            .all()
        )
    
    departments = Department.query.order_by(Department.name.asc()).all()

    breadcrumbs = [
        ("Home", url_for("construction.construction_home")),
        ("Manage Employees", url_for("core.manage_employees"))
    ]

    action_button = {
        "label": "+ Add Employee",
        "toggle": "modal",
        "target": "#addEmployeeModal"
    }

    return render_template(
        "core/manage_employees.html",
        page_title="Manage Employees",
        breadcrumbs=breadcrumbs,
        back_url=url_for("construction.construction_home"),
        action_button=action_button,
        employees=employees,
        departments=departments
    )


@core_bp.route("/add-employee", methods=["POST"])
@login_required
@role_required(["Admin", "Staff"])
@department_required(["Construction", "Corporate"])
def add_employee():
    name = request.form.get("name", "").strip()
    role = request.form.get("role", "").strip()
    rate = request.form.get("rate_per_day", 0)
    dept_id = request.form.get("department_id")

    if not name or not dept_id:
        return {"success": False, "error": "Name and Department are required."}

    dept = Department.query.get(int(dept_id))
    if not dept:
        return {"success": False, "error": "Invalid department."}

    new_emp = Employee(
        name=name,
        role=role,
        rate_per_day=float(rate) if rate else None,
        department_id=int(dept_id)
    )
    db.session.add(new_emp)
    db.session.commit()

    return {
        "success": True,
        "employee": {
            "id": new_emp.id,
            "name": new_emp.name,
            "role": new_emp.role,
            "rate_per_day": new_emp.rate_per_day,
            "department_id": new_emp.department_id,
            "department_name": dept.name
        }
    }



@core_bp.route("/edit-employee/<int:emp_id>", methods=["POST", "GET"])
@login_required
@role_required(["Admin", "Staff"])
@department_required(["Construction", "Corporate"])
def edit_employee(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    departments = Department.query.order_by(Department.name.asc()).all()

    if request.method == "POST":
        emp.name = request.form.get("name", emp.name).strip()
        emp.role = request.form.get("role", emp.role).strip()
        emp.rate_per_day = float(request.form.get("rate_per_day", emp.rate_per_day) or 0)
        emp.department_id = int(request.form.get("department_id", emp.department_id))

        dept = Department.query.get(emp.department_id)

        db.session.commit()

        # Check for AJAX request using modern Flask
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

        flash("Worker updated successfully!", "success")
        return redirect(url_for("core.manage_employees"))

    # GET → fallback
    return render_template("core/edit_employee.html", emp=emp, departments=departments)


@core_bp.route("/delete-employee/<int:emp_id>")
@login_required
@role_required(["Admin", "Staff"])
@department_required(["Construction", "Corporate"])
def delete_employee(emp_id):
    emp = Employee.query.get_or_404(emp_id)
    try:
        db.session.delete(emp)
        db.session.commit()
        flash("Worker deleted successfully!", "success")
    except:
        db.session.rollback()
        flash("Cannot delete worker. It may be linked to projects or records.", "danger")
    return redirect(url_for("core.manage_employees"))

@core_bp.route("/employee-names")
@login_required
@role_required(["Admin", "Staff"])
def employee_names():
    names = [e.name for e in Employee.query.order_by(Employee.name.asc()).all()]
    return jsonify({"names": names})
