from flask import Blueprint, render_template, request, redirect, url_for, session, flash, session
from ..extensions import db
from ..models.user import User
from werkzeug.security import check_password_hash

auth_bp = Blueprint("auth", __name__, template_folder="../../templates/auth")


# Login
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        # Use the correct field for hashed password
        if user and check_password_hash(user.password, password):
            # Save session
            session["user_id"] = user.id
            session["username"] = user.username
            session["role"] = user.role
            session["department"] = user.department

            flash(f"Welcome {user.username}!", "success")

            # Check if there's a next parameter
            next_url = request.form.get("next") or request.args.get("next")
            if next_url and next_url != "None" and next_url.strip():
                # Validate that next_url is a safe redirect (same host)
                from urllib.parse import urlparse
                parsed = urlparse(next_url)
                if parsed.netloc == '' or parsed.netloc == request.host:
                    return redirect(next_url)

            # Redirect based on role
            if user.role == "Admin":
                return redirect(url_for("admin.manage_users"))
            else:
                return redirect(url_for("core.dashboard"))

        else:
            flash("Invalid username or password.", "danger")
            return redirect(url_for("auth.login"))

    # GET request
    next_url = request.args.get("next")
    return render_template("auth/login.html", next=next_url)



@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("core.dashboard"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("role") != "Admin":
        return redirect(url_for("auth.unauthorized"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")

        if User.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return redirect(url_for("auth.register"))

        user = User(username=username, role=role)
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash("User registered successfully!", "success")
        return redirect(url_for("core.dashboard"))

    return render_template("auth/register.html")


@auth_bp.route("/unauthorized")
def unauthorized():
    return render_template("auth/unauthorized.html")
