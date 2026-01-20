# app/auth/decorators/auth_decorators.py
from functools import wraps
from flask import session, redirect, url_for, flash, request

# ----------------------------
# LOGIN REQUIRED
# ----------------------------
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            next_page = request.url
            return redirect(url_for("auth.login", next=next_page))
        return view(*args, **kwargs)
    return wrapper


# ----------------------------
# ROLE REQUIRED
# ----------------------------
def role_required(*roles):
    """
    Require user to have one of the allowed role(s).
    Usage:
        @role_required("Admin")
        @role_required("Admin", "Staff")
        @role_required(["Admin", "Staff"])
    """
    # Flatten if a single list/tuple is passed
    if len(roles) == 1 and isinstance(roles[0], (list, tuple)):
        roles = roles[0]

    # Normalize to lowercase
    allowed_roles = [r.lower() for r in roles]

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user_role = (session.get("role") or "").lower()
            if not user_role or user_role not in allowed_roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("auth.unauthorized"))
            return view(*args, **kwargs)
        return wrapper
    return decorator


# ----------------------------
# DEPARTMENT REQUIRED
# ----------------------------
def department_required(*departments):
    """
    Require user to belong to one of the allowed department(s).
    Usage:
        @department_required("Corporate")
        @department_required("Construction", "Corporate")
        @department_required(["Construction", "Corporate"])
    """
    # Flatten if a single list/tuple is passed
    if len(departments) == 1 and isinstance(departments[0], (list, tuple)):
        departments = departments[0]

    # Normalize to lowercase
    allowed_departments = [d.lower() for d in departments]

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user_dept = (session.get("department") or "").lower()
            if not user_dept or user_dept not in allowed_departments:
                flash("You are not authorized to access this page.", "warning")
                return redirect(url_for("auth.unauthorized"))
            return view(*args, **kwargs)
        return wrapper
    return decorator
