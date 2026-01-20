# app/auth/decorators/decorators.py
from functools import wraps
from flask import session, redirect, url_for, flash

# ----------------------------
# CORPORATE ONLY
# ----------------------------
def corporate_only(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if (session.get("department") or "").lower() != "corporate":
            flash("Access restricted to Corporate Department only.", "danger")
            return redirect(url_for("auth.unauthorized"))
        return view(*args, **kwargs)
    return wrapper


# ----------------------------
# GENERIC DEPARTMENT CHECK
# ----------------------------
def department_check(*departments):
    """
    Generic decorator to allow access based on departments (case-insensitive)
    Accepts string, multiple strings, or list/tuple
    """
    if len(departments) == 1 and isinstance(departments[0], (list, tuple)):
        departments = departments[0]
    allowed_departments = [d.lower() for d in departments]

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            user_dept = (session.get("department") or "").lower()
            if user_dept not in allowed_departments:
                flash("You are not authorized to access this page.", "warning")
                return redirect(url_for("auth.unauthorized"))
            return view(*args, **kwargs)
        return wrapper
    return decorator
