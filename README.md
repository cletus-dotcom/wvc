# WVC (St. Michael Builders Corporation) – Flask App

This repository contains a Flask web application used by **St. Michael Builders Corporation (WVC)** to manage multiple business modules:

- **Construction**
- **Carenderia**
- **Catering**

It uses **Flask + SQLAlchemy + Flask-Migrate (Alembic)** with a **PostgreSQL** database and Bootstrap-based HTML templates.

---

## Quick Start (Windows / PowerShell)

### Prerequisites
- Python (the project currently runs with a local `venv/`)
- PostgreSQL (a database you can connect to)

### 1) Create a virtual environment (if you don’t already have one)

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2) Install dependencies

This repo currently does **not** include a pinned `requirements.txt`. Install from your environment or add one if you want reproducible installs.

At minimum, the app uses:
- `Flask`
- `Flask-SQLAlchemy`
- `Flask-Migrate`
- `python-dotenv`
- `psycopg2-binary` (or another Postgres driver)
- `reportlab` (PDF exports)

### 3) Configure environment variables

Create a `.env` file in the project root:

```env
SECRET_KEY=change-me
DATABASE_URL=postgresql://postgres:password@localhost:5432/wvc
```

The values are loaded in `app/config.py` using `python-dotenv`.

### 4) Run migrations

```bash
flask db upgrade
```

### 5) Start the app

```bash
python run.py
```

Open the app and use the dashboard as the entry point.

---

## Architecture Overview

### App factory
- **Entry**: `run.py`
- **Factory**: `app/__init__.py` → `create_app()`
- **Config**: `app/config.py`
- **DB/Migrations**: `app/extensions.py` (SQLAlchemy + Flask-Migrate)

### Blueprints (modules)
The app is split into blueprints registered in `app/__init__.py`:

- **Core** (root): `app/models/core.py`
- **Construction**: `app/models/construction/` with prefix `/construction`
- **Carenderia**: `app/models/carenderia/` with prefix `/carenderia`
- **Catering**: `app/models/catering/` with prefix `/catering`
- **Auth**: `app/auth/routes.py` with prefix `/auth`
- **Admin**: `app/auth/admin_routes.py` with prefix `/admin`

---

## Authentication & Authorization

This codebase uses **session-based** authorization checks via decorators:

- `login_required`
- `role_required`
- `department_required`

See `app/decorators/auth_decorators.py`.

The user’s department/role is stored in session keys like:
- `session["user_id"]`
- `session["department"]`
- `session["role"]`

---

## Modules

### Core
- **Dashboard**: `app/templates/core/dashboard.html`
  - Acts as the main landing page (SMBC dashboard) for navigating modules.
- **Manage Employees**: `app/templates/core/manage_employees.html`
  - The `core.manage_employees` route now filters to **Construction** employees only (by department).
- **Manage Departments**: `app/templates/core/manage_department.html`

---

### Catering
Key database tables/models live in `app/models/catering/models.py`:

- `catering_requests` (bookings)
- `catering_menu`
- `catering_equipment`
- `catering_transaction` (booking payments)
- `catering_expense` (expenses such as Wages / Expenses / Miscellaneous)
- `catering_wages` (detailed wages entries per employee/day)

Key routes live in `app/models/catering/routes.py`:

- **Home dashboard**: confirmed bookings list and financial transaction modal
- **Manage Bookings**: booking CRUD + items requested (menu/equipment)
- **Manage Menu / Equipment**: CRUD pages
- **Expenses**:
  - Wages modal supports multiple employees with rate/day × days, totals, and list management
  - Saves detailed wages to `catering_wages` and a summarized entry to `catering_expense`
- **Reports**:
  - View Wages (month filter)
  - View Balance Sheet (month filter + daily details)
  - Balance Sheet PDF export (ReportLab)

Templates:
- `app/templates/catering/home.html`
- `app/templates/catering/manage_bookings.html`
- `app/templates/catering/manage_menu.html`
- `app/templates/catering/manage_equipment.html`
- `app/templates/catering/view_wages.html`
- `app/templates/catering/view_balance_sheet.html`

---

### Carenderia
Key routes/models:
- `app/models/carenderia/models.py`
- `app/models/carenderia/routes.py`

Notable reporting:
- Trial Balance export PDF (ReportLab) routes:
  - `/carenderia/export-trial-balance/pdf`

---

### Construction
Key models:
- `app/models/construction/models.py`
  - `ConstructionContract`
  - `ProjectExpense` (materials/labor/gas/documents/obligations etc.)

Key routes:
- `app/models/construction/routes.py`
  - Project overview (`/project/<id>/overview`)
  - Construction balance sheet:
    - `/construction/balance-sheet` (project selector + overall + per-project details)
    - `/construction/balance-sheet/pdf` (PDF export using the same heading layout as Catering balance sheet export)

Templates:
- `app/templates/construction/home.html`
- `app/templates/construction/balance_sheet.html`
- `app/templates/construction/project_overview.html`

---

## PDF Exports (ReportLab)

PDF generation uses **ReportLab** and is implemented in blueprint route files. Notable endpoints:

- Catering Balance Sheet export:
  - `GET /catering/export-balance-sheet/pdf?month=YYYY-MM`
- Carenderia Trial Balance export:
  - `GET /carenderia/export-trial-balance/pdf?month=YYYY-MM`
- Construction Balance Sheet export:
  - `GET /construction/balance-sheet/pdf?project_id=<id|empty>`

All exports use a consistent WVC header block (logo + company name/address + separator line).

---

## Database & Migrations

Migrations are stored in `migrations/` (Alembic / Flask-Migrate).

Common commands:

```bash
flask db migrate -m "your message"
flask db upgrade
flask db downgrade
```

---

## Admin Bootstrap User

There is a helper script to create a default admin:

- `create_admin.py`

Run it from an activated environment:

```bash
python create_admin.py
```

**Important**: Update the default password before using in production.

---

## Deployment

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for a step-by-step guide to deploy this app to **Render + Supabase** (free tier for testing, or paid for production).

Quick summary:
- **Render** hosts the Flask web service
- **Supabase** provides the PostgreSQL database
- Estimated cost for small usage: **~$400-500/year** (paid plans) or **$0** (free tier with limitations)

---

## Notes / Known Gaps

- The repository currently includes a `venv/` folder; typically you would exclude this from version control and rebuild it locally.

