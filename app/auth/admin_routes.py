from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..extensions import db
from ..models.user import User
from werkzeug.security import check_password_hash
from app.decorators.auth_decorators import login_required, role_required

admin_bp = Blueprint("admin", __name__, template_folder="../../templates/admin")

# Admin User Management (mount path will be /admin because we register with url_prefix)
@admin_bp.route("/users")
@login_required
@role_required("Admin")
def manage_users():
    users = User.query.all()
    return render_template("admin/manage_users.html", users=users)


@admin_bp.route("/users/add", methods=["POST"])
@login_required
@role_required("Admin")
def add_user():
    username = request.form.get("username")
    password = request.form.get("password")
    role = request.form.get("role")
    department = request.form.get("department")

    # Validate required fields
    if not username or not password or not role:
        flash("All fields are required!", "danger")
        return redirect(url_for("admin.manage_users"))

    # Check for duplicates
    if User.query.filter_by(username=username).first():
        flash("Username already exists!", "danger")
        return redirect(url_for("admin.manage_users"))

    # Create user with department
    user = User(
        username=username,
        role=role,
        department=department
    )
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    flash("User added successfully.", "success")
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/users/update/<int:user_id>", methods=["POST"])
@login_required
@role_required("Admin")
def update_user(user_id):
    user = User.query.get_or_404(user_id)

    # Update role
    user.role = request.form.get("role")

    # Update department
    user.department = request.form.get("department")

    # Update password only if entered
    new_password = request.form.get("password")
    if new_password and new_password.strip() != "":
        user.set_password(new_password)

    db.session.commit()

    flash("User updated successfully.", "success")
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/users/delete/<int:user_id>", methods=["POST"])
@login_required
@role_required("Admin")
def delete_user(user_id):
    if user_id == session.get("user_id"):
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin.manage_users"))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash("User deleted successfully.", "success")
    return redirect(url_for("admin.manage_users"))


@admin_bp.route("/go_home")
@login_required
def go_home():
    department = session.get("department")

    if not department:
        flash("No department found for your session.", "warning")
        return redirect(url_for("admin.manage_users"))

    if department == "Construction":
        return redirect("/construction/home")
    elif department == "Carenderia":
        return redirect("/carenderia/home")
    elif department == "Catering":
        return redirect("/catering/home")

    # If none matched → fallback to dashboard
    return redirect(url_for("core.dashboard"))


