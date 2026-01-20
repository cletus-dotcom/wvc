from flask import request, jsonify, render_template, redirect, url_for, flash, session, send_file, current_app
from .models import ConstructionContract
from ...extensions import db
from app.decorators.auth_decorators import login_required, role_required, department_required
from . import construction_bp  # existing blueprint
from app.decorators.decorators import corporate_only
from datetime import datetime
from .models import ProjectExpense, DailyInvoiceCounter
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import distinct
from decimal import Decimal
from collections import defaultdict



# --- NEW: redirect /construction to /construction/home ---
@construction_bp.route("")
@login_required
@department_required("Construction", "Corporate")
def construction_root():
    return redirect(url_for("construction.construction_home"))


@construction_bp.route("/home")
@login_required
@department_required("Construction", "Corporate")
def construction_home():
    # Fetch all projects ordered by creation date descending
    projects = ConstructionContract.query.order_by(ConstructionContract.created_at.desc()).all()
    return render_template("construction/home.html", projects=projects)


@construction_bp.route("/reports")
@login_required
@department_required("Construction", "Corporate")
def reports():
    # Fetch all projects ordered by creation date descending
    projects = ConstructionContract.query.order_by(ConstructionContract.created_at.desc()).all()
    return render_template("construction/reports.html", projects=projects)


@construction_bp.route("/project/<int:project_id>/overview")
@login_required
@department_required("Construction", "Corporate")
def project_overview(project_id):
    """Display financial summary/balance sheet for a project."""
    project = ConstructionContract.query.get_or_404(project_id)
    
    # Calculate expense totals by type
    from app.models.core import Employee
    expenses = ProjectExpense.query.filter_by(contract_id=project_id).order_by(ProjectExpense.expense_date.desc(), ProjectExpense.created_at.desc()).all()
    
    # Add employee names to labor expenses
    for expense in expenses:
        if expense.expense_type == "Labor" and expense.labor_id:
            employee = Employee.query.get(expense.labor_id)
            expense.employee_name = employee.name if employee else "Unknown"
        else:
            expense.employee_name = None
    
    # Initialize totals
    total_materials = 0
    total_labor = 0
    total_gasoline = 0
    total_documents = 0
    total_obligations = 0
    
    # Sum up expenses by type
    for expense in expenses:
        if expense.expense_type == "Materials" and expense.material_amount:
            total_materials += float(expense.material_amount)
        elif expense.expense_type == "Labor" and expense.labor_charge:
            total_labor += float(expense.labor_charge)
        elif expense.expense_type == "Gasoline" and expense.gasoline_amount:
            total_gasoline += float(expense.gasoline_amount)
        elif expense.expense_type == "Documents" and expense.document_amount:
            total_documents += float(expense.document_amount)
        elif expense.expense_type == "Obligation" and expense.obligation_amount:
            total_obligations += float(expense.obligation_amount)
    
    # Calculate total expenses
    total_expenses = total_materials + total_labor + total_gasoline + total_documents + total_obligations
    
    # Get contract price
    contract_price = float(project.contract_price) if project.contract_price else 0
    
    # Calculate balance (profit/loss)
    balance = contract_price - total_expenses
    
    # Prepare summary data
    summary = {
        'total_materials': total_materials,
        'total_labor': total_labor,
        'total_gasoline': total_gasoline,
        'total_documents': total_documents,
        'total_obligations': total_obligations,
        'total_expenses': total_expenses,
        'contract_price': contract_price,
        'balance': balance
    }
    
    return render_template("construction/project_overview.html", project=project, summary=summary, expenses=expenses)


@construction_bp.route("/balance-sheet")
@login_required
@department_required("Construction", "Corporate")
def view_balance_sheet():
    """Construction balance sheet with per-project option and overall summary."""
    project_id = request.args.get("project_id", "").strip()

    projects = ConstructionContract.query.order_by(ConstructionContract.project_name.asc()).all()

    selected_project = None
    if project_id:
        try:
            pid = int(project_id)
            selected_project = ConstructionContract.query.get(pid)
        except ValueError:
            selected_project = None

    # Choose which projects to include
    included_projects = [selected_project] if selected_project else projects
    included_projects = [p for p in included_projects if p is not None]

    per_project_rows = []
    overall_contract_total = Decimal("0")
    overall_expense_total = Decimal("0")

    for p in included_projects:
        contract_price = Decimal(str(p.contract_price or 0))
        overall_contract_total += contract_price

        # Sum expense amounts by type using ProjectExpense fields
        expenses = ProjectExpense.query.filter_by(contract_id=p.id).all()
        totals = {
            "Materials": Decimal("0"),
            "Labor": Decimal("0"),
            "Gasoline": Decimal("0"),
            "Documents": Decimal("0"),
            "Obligation": Decimal("0"),
        }
        for e in expenses:
            if (e.expense_type or "") == "Materials" and e.material_amount is not None:
                totals["Materials"] += Decimal(str(e.material_amount))
            elif (e.expense_type or "") == "Labor" and e.labor_charge is not None:
                totals["Labor"] += Decimal(str(e.labor_charge))
            elif (e.expense_type or "") == "Gasoline" and e.gasoline_amount is not None:
                totals["Gasoline"] += Decimal(str(e.gasoline_amount))
            elif (e.expense_type or "") == "Documents" and e.document_amount is not None:
                totals["Documents"] += Decimal(str(e.document_amount))
            elif (e.expense_type or "") == "Obligation" and e.obligation_amount is not None:
                totals["Obligation"] += Decimal(str(e.obligation_amount))

        total_expenses = sum(totals.values(), Decimal("0"))
        overall_expense_total += total_expenses
        balance = contract_price - total_expenses

        per_project_rows.append({
            "project": p,
            "contract_price": contract_price,
            "totals": totals,
            "total_expenses": total_expenses,
            "balance": balance,
        })

    summary = {
        "overall_contract_total": overall_contract_total,
        "overall_expense_total": overall_expense_total,
        "overall_balance": overall_contract_total - overall_expense_total,
    }

    return render_template(
        "construction/balance_sheet.html",
        projects=projects,
        selected_project=selected_project,
        per_project_rows=per_project_rows,
        summary=summary,
    )


@construction_bp.route("/balance-sheet/pdf")
@login_required
@department_required("Construction", "Corporate")
def export_balance_sheet_pdf():
    """Export Construction balance sheet as PDF (header matches catering balance sheet export)."""
    # Local import to avoid hard dependency at app import-time
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.units import inch
    import io
    import os

    project_id = request.args.get("project_id", "").strip()

    projects = ConstructionContract.query.order_by(ConstructionContract.project_name.asc()).all()
    selected_project = None
    if project_id:
        try:
            pid = int(project_id)
            selected_project = ConstructionContract.query.get(pid)
        except ValueError:
            selected_project = None

    included_projects = [selected_project] if selected_project else projects
    included_projects = [p for p in included_projects if p is not None]

    per_project_rows = []
    overall_contract_total = Decimal("0")
    overall_expense_total = Decimal("0")

    for p in included_projects:
        contract_price = Decimal(str(p.contract_price or 0))
        overall_contract_total += contract_price

        expenses = ProjectExpense.query.filter_by(contract_id=p.id).all()
        totals = {
            "Materials": Decimal("0"),
            "Labor": Decimal("0"),
            "Gasoline": Decimal("0"),
            "Documents": Decimal("0"),
            "Obligation": Decimal("0"),
        }
        for e in expenses:
            if (e.expense_type or "") == "Materials" and e.material_amount is not None:
                totals["Materials"] += Decimal(str(e.material_amount))
            elif (e.expense_type or "") == "Labor" and e.labor_charge is not None:
                totals["Labor"] += Decimal(str(e.labor_charge))
            elif (e.expense_type or "") == "Gasoline" and e.gasoline_amount is not None:
                totals["Gasoline"] += Decimal(str(e.gasoline_amount))
            elif (e.expense_type or "") == "Documents" and e.document_amount is not None:
                totals["Documents"] += Decimal(str(e.document_amount))
            elif (e.expense_type or "") == "Obligation" and e.obligation_amount is not None:
                totals["Obligation"] += Decimal(str(e.obligation_amount))

        total_expenses = sum(totals.values(), Decimal("0"))
        overall_expense_total += total_expenses
        balance = contract_price - total_expenses

        per_project_rows.append((p, contract_price, totals, total_expenses, balance))

    overall_balance = overall_contract_total - overall_expense_total

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, title="Construction Balance Sheet", topMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    story = []

    # --- Header (copy the same heading settings from catering balance sheet export) ---
    logo_path = os.path.join(current_app.root_path, "static", "images", "wvc_logo.png")

    company_style = ParagraphStyle(
        "CompanyStyle",
        parent=styles["Normal"],
        fontSize=16,
        fontName="Helvetica-Bold",
        spaceAfter=0,
        leading=18,
    )
    address_style = ParagraphStyle(
        "AddressStyle",
        parent=styles["Normal"],
        fontSize=9,
        fontName="Helvetica",
        spaceBefore=0,
        spaceAfter=12,
        leading=10,
    )
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        fontSize=18,
        fontName="Helvetica-Bold",
        spaceAfter=12,
        alignment=1,
    )

    if os.path.exists(logo_path):
        # Logo size per requirement
        logo = Image(logo_path, width=0.65 * inch, height=0.75 * inch)
    else:
        logo = Paragraph("", styles["Normal"])

    right_col_table = Table(
        [
            [Paragraph("St. Michael Builders Corporation", company_style)],
            [Paragraph("Canjulao, Jagna, Bohol", address_style)],
            [""],
        ],
        colWidths=[5.5 * inch],
    )
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

    # Heading first column width set to 1"
    header_table = Table([[logo, right_col_table]], colWidths=[1.0 * inch, 6.0 * inch])
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
    story.append(Paragraph("Construction Balance Sheet", title_style))
    story.append(Paragraph(f"Project: {selected_project.project_name if selected_project else 'All Projects'}", styles["Normal"]))
    story.append(Spacer(1, 0.25 * inch))

    # Summary
    summary_data = [
        ["Item", "Amount"],
        ["Total Contract Amount", f"{overall_contract_total:,.2f}"],
        ["Total Expenses", f"{overall_expense_total:,.2f}"],
        ["Balance", f"{overall_balance:,.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[4 * inch, 2 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )
    )
    story.append(Paragraph("Summary", styles["Heading2"]))
    story.append(Spacer(1, 0.1 * inch))
    story.append(summary_table)
    story.append(Spacer(1, 0.25 * inch))

    # Per project details
    details = [["Project", "Contract", "Expenses", "Balance"]]
    for (p, contract_price, _totals, total_expenses, balance) in per_project_rows:
        details.append([
            p.project_name or f"Project #{p.id}",
            f"{contract_price:,.2f}",
            f"{total_expenses:,.2f}",
            f"{balance:,.2f}",
        ])
    details_table = Table(details, colWidths=[3.3 * inch, 1.2 * inch, 1.2 * inch, 1.3 * inch], repeatRows=1)
    details_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
            ]
        )
    )
    story.append(Paragraph("Per Project Details", styles["Heading2"]))
    story.append(Spacer(1, 0.1 * inch))
    story.append(details_table)

    doc.build(story)
    buf.seek(0)

    filename = "construction_balance_sheet.pdf" if not selected_project else f"construction_balance_sheet_project_{selected_project.id}.pdf"
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=filename)


@construction_bp.route("/admin/manage-users")
@login_required
@role_required("Admin")
def manage_users():
    # Example: fetch all users (replace with your actual user model)
    from ...models.user import User
    users = User.query.all()
    return render_template("admin/manage_users.html", users=users)


@construction_bp.route("/new-project", methods=["GET", "POST"])
@login_required
@department_required("Construction", "Corporate")
def new_project():
    if request.method == "POST":
        # Collect data
        contractor_name = request.form.get("contractor_name")
        contractor_address = request.form.get("contractor_address")
        project_name = request.form.get("project_name")
        project_site = request.form.get("project_site")
        ntp_date = request.form.get("ntp_date")
        completion_date = request.form.get("completion_date")
        contract_duration = request.form.get("contract_duration")
        contract_price = request.form.get("contract_price")

        # Create record
        from .models import ConstructionContract
        new_contract = ConstructionContract(
            contractor_name=contractor_name,
            contractor_address=contractor_address,
            project_name=project_name,
            project_site=project_site,
            ntp_date=ntp_date,
            completion_date=completion_date,
            contract_duration=contract_duration,
            contract_price=contract_price
        )

        db.session.add(new_contract)
        db.session.commit()

        flash("New project added successfully!", "success")
        return redirect(url_for("construction.construction_home"))

    return render_template("construction/new_project.html")

@construction_bp.route("/update-project")
@login_required
@corporate_only
def update_project():
    projects = ConstructionContract.query.order_by(ConstructionContract.id.desc()).all()
    return render_template("construction/update_project.html", projects=projects)


@construction_bp.post("/update-project/<int:project_id>")
@login_required
@corporate_only
def update_project_submit(project_id):
    p = ConstructionContract.query.get_or_404(project_id)

    p.project_name = request.form["project_name"]
    p.contractor_name = request.form["contractor_name"]
    p.project_site = request.form["project_site"]
    p.ntp_date = request.form.get("ntp_date")
    p.completion_date = request.form.get("completion_date")
    p.contract_duration = request.form.get("contract_duration")
    p.contract_price = request.form.get("contract_price")
    p.status = request.form["status"]

    db.session.commit()
    flash("Project updated successfully!", "success")
    return redirect(url_for("construction.update_project"))


@construction_bp.post("/delete-project/<int:project_id>")
@login_required
@corporate_only
def delete_project(project_id):
    p = ConstructionContract.query.get_or_404(project_id)
    db.session.delete(p)
    db.session.commit()

    flash("Project deleted successfully!", "danger")
    return redirect(url_for("construction.update_project"))

@construction_bp.route("/project/<int:project_id>")
@login_required
@department_required("Construction", "Corporate")
def project_detail(project_id):
    project = ConstructionContract.query.get_or_404(project_id)
    return render_template("construction/project_detail.html", project=project)

@construction_bp.get("/next-invoice-number")
@login_required
@department_required("Construction", "Corporate")
def next_invoice_number():
    """
    Returns the next invoice number for a given date.
    Optional query param: date=YYYY-MM-DD
    """
    date_str = request.args.get("date")
    try:
        today = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.today().date()
    except ValueError:
        return jsonify({"message": "Invalid date format. Use YYYY-MM-DD."}), 400

    try:
        # Ensure atomic operation for getting next invoice number
        with db.session.begin_nested():
            counter = DailyInvoiceCounter.query.get(today)
            next_seq = counter.last_seq + 1 if counter else 1

        invoice_number = f"INV-{today.strftime('%Y%m%d')}-{next_seq:04d}"
        return jsonify({"invoice_number": invoice_number})
    except Exception as e:
        return jsonify({"message": "Error generating invoice number.", "error": str(e)}), 500


@construction_bp.post("/project/<int:project_id>/add-materials")
@login_required
@department_required("Construction", "Corporate")
def add_materials(project_id):
    data = request.get_json()
    expense_date = data.get("expense_date")
    expense_type = data.get("expense_type")
    materials = data.get("materials", [])

    if not expense_date or not materials:
        return jsonify({"message": "Missing required fields."}), 400

    # --- Clean and validate materials ---
    valid_rows = []
    for m in materials:
        item = (m.get("item") or "").strip()
        qty = m.get("qty") or 0
        unit = (m.get("unit") or "").strip()
        unit_price = m.get("unit_price") or 0
        material_amount = m.get("material_amount") or qty * unit_price

        try: qty = float(qty)
        except: qty = 0
        try: unit_price = float(unit_price)
        except: unit_price = 0
        try: material_amount = float(material_amount)
        except: material_amount = qty * unit_price

        if item and qty > 0:
            valid_rows.append({
                "item": item,
                "qty": qty,
                "unit": unit,
                "unit_price": unit_price,
                "material_amount": material_amount
            })

    if not valid_rows:
        return jsonify({"message": "No valid materials to save."}), 400

    session_user = session.get("user_id")
    today = datetime.today().date()

    try:
        with db.session.begin():  # atomic transaction
            # --- UPSERT DailyInvoiceCounter ---
            insert_stmt = pg_insert(DailyInvoiceCounter).values(
                invoice_date=today, last_seq=1
            ).on_conflict_do_update(
                index_elements=[DailyInvoiceCounter.invoice_date],
                set_=dict(last_seq=DailyInvoiceCounter.last_seq + 1)
            ).returning(DailyInvoiceCounter.last_seq)

            result = db.session.execute(insert_stmt)
            last_seq = result.scalar()  # safely get sequence

            invoice_number = f"INV-{today.strftime('%Y%m%d')}-{last_seq:04d}"

            # --- Save all materials with the same invoice number ---
            expenses = [
                ProjectExpense(
                    contract_id=project_id,
                    expense_type=expense_type,
                    expense_date=expense_date,
                    item=m["item"],
                    qty=m["qty"],
                    unit=m["unit"],
                    unit_price=m["unit_price"],
                    material_amount=m["material_amount"],
                    invoice_number=invoice_number,
                    created_by=session_user,
                )
                for m in valid_rows
            ]
            db.session.add_all(expenses)

        db.session.commit()
        return jsonify({"message": "Materials saved successfully!", "invoice_number": invoice_number})

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error saving materials.", "error": str(e)}), 500
    

@construction_bp.route("/get-employees")
@login_required
@department_required("Construction", "Corporate")
def get_employees():
    from app.models.core import Employee  # adjust import as needed

    employees = Employee.query.order_by(Employee.name.asc()).all()

    return jsonify({
        "employees": [
            {
                "id": e.id,
                "name": e.name,
                "rate_per_day": float(e.rate_per_day) if e.rate_per_day else None,
                "department": e.department.name if e.department else None
            }
            for e in employees
        ]
    })

@construction_bp.post("/project/<int:project_id>/add-labor")
@login_required
@department_required("Construction", "Corporate")
def add_labor(project_id):
    from decimal import Decimal

    data = request.get_json()
    expense_date = data.get("expense_date")
    expense_type = data.get("expense_type")
    labor_entries = data.get("labor_entries", [])

    if not expense_date or not labor_entries:
        return jsonify({"message": "Missing required fields."}), 400

    # --- Clean and validate labor entries ---
    valid_rows = []
    for entry in labor_entries:
        labor_id = entry.get("labor_id")
        rate_per_day = entry.get("rate_per_day") or 0
        days = entry.get("days") or 0
        labor_charge = entry.get("labor_charge") or (rate_per_day * days)

        try:
            rate_per_day = Decimal(rate_per_day)
            days = Decimal(days)
            labor_charge = Decimal(labor_charge)
        except:
            continue

        if labor_id and days > 0:
            valid_rows.append({
                "labor_id": labor_id,
                "rate_per_day": rate_per_day,
                "days": days,
                "labor_charge": labor_charge
            })

    if not valid_rows:
        return jsonify({"message": "No valid labor entries to save."}), 400

    session_user = session.get("user_id")
    today = datetime.today().date()

    try:
        with db.session.begin():  # atomic transaction
            # --- UPSERT DailyInvoiceCounter ---
            insert_stmt = pg_insert(DailyInvoiceCounter).values(
                invoice_date=today, last_seq=1
            ).on_conflict_do_update(
                index_elements=[DailyInvoiceCounter.invoice_date],
                set_=dict(last_seq=DailyInvoiceCounter.last_seq + 1)
            ).returning(DailyInvoiceCounter.last_seq)

            result = db.session.execute(insert_stmt)
            last_seq = result.scalar()  # safely get sequence

            invoice_number = f"INV-{today.strftime('%Y%m%d')}-{last_seq:04d}"

            # --- Save all labor entries with the same invoice number ---
            expenses = [
                ProjectExpense(
                    contract_id=project_id,
                    expense_type=expense_type,
                    expense_date=expense_date,
                    labor_id=entry["labor_id"],
                    rate_per_day=entry["rate_per_day"],
                    days=entry["days"],
                    labor_charge=entry["labor_charge"],
                    invoice_number=invoice_number,
                    created_by=session_user,
                )
                for entry in valid_rows
            ]
            db.session.add_all(expenses)

        db.session.commit()
        return jsonify({"message": "Labor expenses saved successfully!", "invoice_number": invoice_number})

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error saving labor expenses.", "error": str(e)}), 500

@construction_bp.post("/project/<int:project_id>/add-gasoline")
@login_required
@department_required("Construction", "Corporate")
def add_gasoline(project_id):
    data = request.get_json()
    expense_date = data.get("expense_date")
    expense_type = data.get("expense_type")
    gasoline_entries = data.get("gasoline_entries", [])

    if not expense_date or not gasoline_entries:
        return jsonify({"message": "Missing required fields."}), 400

    # --- Clean and validate gasoline entries ---
    valid_rows = []
    for entry in gasoline_entries:
        gasoline_amount = entry.get("gasoline_amount") or 0

        try:
            gasoline_amount = float(gasoline_amount)
        except:
            continue

        if gasoline_amount > 0:
            valid_rows.append({
                "gasoline_amount": gasoline_amount
            })

    if not valid_rows:
        return jsonify({"message": "No valid gasoline entries to save."}), 400

    session_user = session.get("user_id")
    today = datetime.today().date()

    try:
        with db.session.begin():  # atomic transaction
            # --- UPSERT DailyInvoiceCounter ---
            insert_stmt = pg_insert(DailyInvoiceCounter).values(
                invoice_date=today, last_seq=1
            ).on_conflict_do_update(
                index_elements=[DailyInvoiceCounter.invoice_date],
                set_=dict(last_seq=DailyInvoiceCounter.last_seq + 1)
            ).returning(DailyInvoiceCounter.last_seq)

            result = db.session.execute(insert_stmt)
            last_seq = result.scalar()  # safely get sequence

            invoice_number = f"INV-{today.strftime('%Y%m%d')}-{last_seq:04d}"

            # --- Save all gasoline entries with the same invoice number ---
            expenses = [
                ProjectExpense(
                    contract_id=project_id,
                    expense_type=expense_type,
                    expense_date=expense_date,
                    gasoline_amount=entry["gasoline_amount"],
                    invoice_number=invoice_number,
                    created_by=session_user,
                )
                for entry in valid_rows
            ]
            db.session.add_all(expenses)

        db.session.commit()
        return jsonify({"message": "Gasoline expenses saved successfully!", "invoice_number": invoice_number})

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error saving gasoline expenses.", "error": str(e)}), 500

@construction_bp.post("/project/<int:project_id>/add-documents")
@login_required
@department_required("Construction", "Corporate")
def add_documents(project_id):
    data = request.get_json()
    expense_date = data.get("expense_date")
    expense_type = data.get("expense_type")
    document_entries = data.get("document_entries", [])

    if not expense_date or not document_entries:
        return jsonify({"message": "Missing required fields."}), 400

    # --- Clean and validate document entries ---
    valid_rows = []
    for entry in document_entries:
        document_ref = (entry.get("document_ref") or "").strip()
        document_amount = entry.get("document_amount") or 0

        try:
            document_amount = float(document_amount)
        except:
            continue

        if document_ref and document_amount > 0:
            valid_rows.append({
                "document_ref": document_ref,
                "document_amount": document_amount
            })

    if not valid_rows:
        return jsonify({"message": "No valid document entries to save."}), 400

    session_user = session.get("user_id")
    today = datetime.today().date()

    try:
        with db.session.begin():  # atomic transaction
            # --- UPSERT DailyInvoiceCounter ---
            insert_stmt = pg_insert(DailyInvoiceCounter).values(
                invoice_date=today, last_seq=1
            ).on_conflict_do_update(
                index_elements=[DailyInvoiceCounter.invoice_date],
                set_=dict(last_seq=DailyInvoiceCounter.last_seq + 1)
            ).returning(DailyInvoiceCounter.last_seq)

            result = db.session.execute(insert_stmt)
            last_seq = result.scalar()  # safely get sequence

            invoice_number = f"INV-{today.strftime('%Y%m%d')}-{last_seq:04d}"

            # --- Save all document entries with the same invoice number ---
            expenses = [
                ProjectExpense(
                    contract_id=project_id,
                    expense_type=expense_type,
                    expense_date=expense_date,
                    document_ref=entry["document_ref"],
                    document_amount=entry["document_amount"],
                    invoice_number=invoice_number,
                    created_by=session_user,
                )
                for entry in valid_rows
            ]
            db.session.add_all(expenses)

        db.session.commit()
        return jsonify({"message": "Document expenses saved successfully!", "invoice_number": invoice_number})

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error saving document expenses.", "error": str(e)}), 500

@construction_bp.post("/project/<int:project_id>/add-obligation")
@login_required
@department_required("Construction", "Corporate")
def add_obligation(project_id):
    data = request.get_json()
    expense_date = data.get("expense_date")
    expense_type = data.get("expense_type")
    obligation_entries = data.get("obligation_entries", [])

    if not expense_date or not obligation_entries:
        return jsonify({"message": "Missing required fields."}), 400

    # --- Clean and validate obligation entries ---
    valid_rows = []
    for entry in obligation_entries:
        obligation_ref = (entry.get("obligation_ref") or "").strip()
        obligation_amount = entry.get("obligation_amount") or 0

        try:
            obligation_amount = float(obligation_amount)
        except:
            continue

        if obligation_ref and obligation_amount > 0:
            valid_rows.append({
                "obligation_ref": obligation_ref,
                "obligation_amount": obligation_amount
            })

    if not valid_rows:
        return jsonify({"message": "No valid obligation entries to save."}), 400

    session_user = session.get("user_id")
    today = datetime.today().date()

    try:
        with db.session.begin():  # atomic transaction
            # --- UPSERT DailyInvoiceCounter ---
            insert_stmt = pg_insert(DailyInvoiceCounter).values(
                invoice_date=today, last_seq=1
            ).on_conflict_do_update(
                index_elements=[DailyInvoiceCounter.invoice_date],
                set_=dict(last_seq=DailyInvoiceCounter.last_seq + 1)
            ).returning(DailyInvoiceCounter.last_seq)

            result = db.session.execute(insert_stmt)
            last_seq = result.scalar()  # safely get sequence

            invoice_number = f"INV-{today.strftime('%Y%m%d')}-{last_seq:04d}"

            # --- Save all obligation entries with the same invoice number ---
            expenses = [
                ProjectExpense(
                    contract_id=project_id,
                    expense_type=expense_type,
                    expense_date=expense_date,
                    obligation_ref=entry["obligation_ref"],
                    obligation_amount=entry["obligation_amount"],
                    invoice_number=invoice_number,
                    created_by=session_user,
                )
                for entry in valid_rows
            ]
            db.session.add_all(expenses)

        db.session.commit()
        return jsonify({"message": "Obligation expenses saved successfully!", "invoice_number": invoice_number})

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error saving obligation expenses.", "error": str(e)}), 500

@construction_bp.post("/project/<int:project_id>/add-activity")
@login_required
@department_required("Construction", "Corporate")
def add_activity(project_id):
    data = request.get_json()
    expense_date = data.get("expense_date")
    expense_type = data.get("expense_type")
    activity_entries = data.get("activity_entries", [])

    if not expense_date or not activity_entries:
        return jsonify({"message": "Missing required fields."}), 400

    # --- Clean and validate activity entries ---
    valid_rows = []
    for entry in activity_entries:
        activity = (entry.get("activity") or "").strip()
        activity_date_str = entry.get("activity_date") or expense_date
        activity_status = entry.get("activity_status") or "Pending"

        # Parse datetime-local string (YYYY-MM-DDTHH:mm or YYYY-MM-DDTHH:mm:ss) to datetime
        activity_date = None
        if activity_date_str and str(activity_date_str).strip():
            try:
                # Parse the full datetime string
                activity_date_str_clean = str(activity_date_str).strip()
                
                if "T" in activity_date_str_clean:
                    # Try parsing with seconds first, then without
                    try:
                        # Parse as datetime with seconds (YYYY-MM-DDTHH:mm:ss)
                        activity_date = datetime.strptime(activity_date_str_clean, "%Y-%m-%dT%H:%M:%S")
                    except ValueError:
                        try:
                            # Parse as datetime without seconds (YYYY-MM-DDTHH:mm) - this is the datetime-local format
                            activity_date = datetime.strptime(activity_date_str_clean, "%Y-%m-%dT%H:%M")
                        except ValueError:
                            # Try with just date part (shouldn't happen but handle it)
                            date_part = activity_date_str_clean.split("T")[0]
                            activity_date = datetime.strptime(date_part, "%Y-%m-%d")
                else:
                    # Just date, use midnight
                    activity_date = datetime.strptime(activity_date_str_clean, "%Y-%m-%d")
            except Exception as e:
                # Fallback to expense_date if parsing fails
                try:
                    activity_date = datetime.strptime(str(expense_date), "%Y-%m-%d")
                except:
                    activity_date = datetime.now()

        if activity:
            # Ensure we have a valid datetime
            if not activity_date:
                # If no datetime provided, use expense_date at midnight, or current datetime
                if expense_date:
                    try:
                        activity_date = datetime.strptime(str(expense_date), "%Y-%m-%d")
                    except:
                        activity_date = datetime.now()
                else:
                    activity_date = datetime.now()
            
            valid_rows.append({
                "activity": activity,
                "activity_date": activity_date,
                "activity_status": activity_status
            })

    if not valid_rows:
        return jsonify({"message": "No valid activity entries to save."}), 400

    session_user = session.get("user_id")

    try:
        # --- Save all activity entries without invoice number ---
        expenses = [
            ProjectExpense(
                contract_id=project_id,
                expense_type=expense_type,
                expense_date=expense_date,
                activity_date=entry["activity_date"],
                activity=entry["activity"],
                activity_status=entry["activity_status"],
                invoice_number=None,
                created_by=session_user,
            )
            for entry in valid_rows
        ]
        db.session.add_all(expenses)
        db.session.commit()
        return jsonify({"message": "Activity entries saved successfully!"})

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error saving activity expenses.", "error": str(e)}), 500

@construction_bp.route("/project/<int:project_id>/get-activities")
@login_required
@department_required("Construction", "Corporate")
def get_activities(project_id):
    """Return all activities for a project."""
    try:
        activities = db.session.query(ProjectExpense).filter(
            ProjectExpense.contract_id == project_id,
            ProjectExpense.expense_type == "Activity",
            ProjectExpense.activity.isnot(None)
        ).order_by(ProjectExpense.activity_date.desc(), ProjectExpense.created_at.desc()).all()
        
        activities_list = []
        for act in activities:
            # Format activity_date - reconstruct datetime string from date
            # Since we store only date, we'll use the date and created_at time as fallback
            activity_date_str = ""
            activity_time_str = ""
            if act.activity_date:
                if isinstance(act.activity_date, str):
                    # If it's already a datetime string, use it
                    if "T" in act.activity_date:
                        activity_date_str = act.activity_date.split("T")[0]
                        activity_time_str = act.activity_date.split("T")[1]
                    else:
                        activity_date_str = act.activity_date
                else:
                    # It's a datetime object, extract date and time
                    activity_date_str = act.activity_date.strftime("%Y-%m-%d")
                    activity_time_str = act.activity_date.strftime("%H:%M")
            
            activities_list.append({
                "id": act.id,
                "activity": act.activity,
                "activity_date": activity_date_str,
                "activity_time": activity_time_str,
                "activity_status": act.activity_status or "Pending",
                "expense_date": act.expense_date.strftime("%Y-%m-%d") if act.expense_date else "",
                "created_at": act.created_at.strftime("%Y-%m-%d %H:%M:%S") if act.created_at else ""
            })
        
        return jsonify({"activities": activities_list})
    except Exception as e:
        return jsonify({"activities": [], "error": str(e)})

@construction_bp.put("/project/<int:project_id>/update-activity/<int:activity_id>")
@login_required
@department_required("Construction", "Corporate")
def update_activity(project_id, activity_id):
    """Update an activity entry."""
    data = request.get_json()
    activity = data.get("activity")
    activity_date_str = data.get("activity_date")
    activity_status = data.get("activity_status")

    if not activity or not activity_date_str:
        return jsonify({"message": "Missing required fields."}), 400

    try:
        activity_obj = db.session.query(ProjectExpense).filter(
            ProjectExpense.id == activity_id,
            ProjectExpense.contract_id == project_id,
            ProjectExpense.expense_type == "Activity"
        ).first()
        
        if not activity_obj:
            return jsonify({"message": "Activity not found."}), 404

        # Parse datetime string
        activity_date = None
        if activity_date_str:
            try:
                if "T" in str(activity_date_str):
                    activity_date = datetime.strptime(activity_date_str, "%Y-%m-%dT%H:%M")
                else:
                    activity_date = datetime.strptime(str(activity_date_str), "%Y-%m-%d")
            except:
                return jsonify({"message": "Invalid date format."}), 400

        activity_obj.activity = activity
        activity_obj.activity_date = activity_date
        activity_obj.activity_status = activity_status or "Pending"

        db.session.commit()
        return jsonify({"message": "Activity updated successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error updating activity.", "error": str(e)}), 500

@construction_bp.delete("/project/<int:project_id>/delete-activity/<int:activity_id>")
@login_required
@department_required("Construction", "Corporate")
def delete_activity(project_id, activity_id):
    """Delete an activity entry."""
    try:
        activity = db.session.query(ProjectExpense).filter(
            ProjectExpense.id == activity_id,
            ProjectExpense.contract_id == project_id,
            ProjectExpense.expense_type == "Activity"
        ).first()
        
        if not activity:
            return jsonify({"message": "Activity not found."}), 404
        
        db.session.delete(activity)
        db.session.commit()
        return jsonify({"message": "Activity deleted successfully!"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Error deleting activity.", "error": str(e)}), 500

@construction_bp.route("/project/get-items-units")
@login_required
@department_required("Construction", "Corporate")
def get_items_units():
    """Return distinct items and units for autocomplete."""
    try:
        items_raw = [row[0] for row in db.session.query(distinct(ProjectExpense.item)).order_by(ProjectExpense.item.asc()).all()]
        units_raw = [row[0] for row in db.session.query(distinct(ProjectExpense.unit)).order_by(ProjectExpense.unit.asc()).all()]
        # Filter out None and empty strings
        items = [item for item in items_raw if item is not None and str(item).strip()]
        units = [unit for unit in units_raw if unit is not None and str(unit).strip()]
        return jsonify({"items": items, "units": units})
    except Exception as e:
        return jsonify({"items": [], "units": [], "error": str(e)})


