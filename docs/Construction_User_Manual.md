# Construction Department — User Manual

This manual describes how to use the Construction module: setting up projects, recording expenses, viewing reports, and managing data. It is intended for Construction and Corporate staff and administrators.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Access and Roles](#2-access-and-roles)
3. [Setting Up](#3-setting-up)
4. [Process Flow](#4-process-flow)
5. [Daily Operations](#5-daily-operations)
6. [Reports and Viewing](#6-reports-and-viewing)
7. [Corporate-Only Tasks](#7-corporate-only-tasks)
8. [Admin-Only Features](#8-admin-only-features)
9. [Tips and Troubleshooting](#9-tips-and-troubleshooting)

---

## 1. Overview

The Construction module is used to:

- **Create and manage construction projects** (contracts) with contractor, site, dates, duration, and contract price.
- **Record expenses** per project: Materials, Labor (including overtime), Gasoline, Documents, Obligations, and Activities.
- **Track finances** with automatic invoice numbers, totals, and balance (contract price minus expenses).
- **View reports** such as project overview, balance sheet, and export to PDF.

**Main entry point:** From the main dashboard, go to **Construction**. You will see the Construction Home page with a list of projects.

---

## 2. Access and Roles

| Role / Department | What they can do |
|-------------------|-------------------|
| **Construction** or **Corporate** (Staff/Admin) | View Construction Home, open projects, add expense entries (Materials, Labor, Gasoline, Documents). View project overview and reports. |
| **Corporate** only | **New Project**, **Update Project**, **Edit Entry** (edit/delete expense line items), **View Balance Sheet**, **Manage Department**. |
| **Admin** only | All of the above, plus **Obligation** and **Activity** entry types on a project. |

- You must be in **Construction** or **Corporate** department to access the Construction module.
- **Update Project** and **Edit Entry** are restricted to **Corporate** (not Construction department).

---

## 3. Setting Up

### 3.1 Department and Users

- Ensure a **Construction** department exists (via **Manage Department** or system setup).
- Users who will record expenses or manage projects should have:
  - **Department:** Construction or Corporate.
  - **Role:** Staff or Admin (Admin needed for Obligation and Activity).

### 3.2 Manage Workers (Construction Employees)

Labor entries use employees from the **Construction** department.

1. Go to **Construction Home** → **Settings** → **Manage Workers** (or your app’s link to **Manage Employees** for Construction).
2. Add workers with:
   - Name  
   - **Rate per day** (used for labor and overtime calculation)
3. Only employees in the **Construction** department appear in the Labor entry form.

**Important:** Labor entry uses **rate per day** and **number of days**; overtime uses **rate per day ÷ 8** as hourly rate × overtime hours. Ensure rate per day is correct for each worker.

### 3.3 Creating the First Project (Corporate)

1. **Construction Home** → **Corporate** → **New Project**.
2. Fill in:
   - **Contractor Name** (required)  
   - **Contractor Address**  
   - **Project Name** (required)  
   - **Project Site**  
   - **NTP Date** (Notice to Proceed)  
   - **Completion Date**  
   - **Contract Duration** (number of days)  
   - **Contract Price**
3. Click **Save Project**. You are returned to Construction Home; the new project appears in the list.

After this, you can open the project and start adding expenses.

---

## 4. Process Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│  SETUP (once or when needed)                                            │
│  • Manage Department  • Manage Workers (Construction)  • New Project    │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  CONSTRUCTION HOME                                                       │
│  • List of projects (search by name, site, contractor, status)           │
│  • Click a row → Project Detail                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  PROJECT DETAIL (per project)                                            │
│  • Project Activities (Corporate: view/edit activities)                  │
│  • Type of Entry: Materials | Labor | Gasoline | Documents | …          │
│  • Choose type → Show entry form → Fill and Submit                       │
│  • Each submission gets an invoice number (by date)                      │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  VIEWING & REPORTS                                                       │
│  • View (Reports): list projects → click row → Project Overview         │
│  • Project Overview: Financial summary, View By Invoice, itemized list  │
│  • Corporate: Update Project, Edit Entry, Balance Sheet, PDF             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Daily Operations

### 5.1 Opening a Project

1. Go to **Construction** → **Construction Home**.
2. Use the search box to filter by project name, site, contractor, or status.
3. **Click a project row** to open **Project Detail** for that project.

### 5.2 Adding Expenses (Common Steps)

1. On **Project Detail**, select **Type of Entry** (e.g. Materials, Labor, Gasoline, Documents).
2. The corresponding **entry form** appears (e.g. Materials Entry Form).
3. Enter **Date**; the system may show **Next Invoice #** for that date.
4. Fill in the form and click **Submit**. A success message (and invoice number) appears.
5. To add another entry, choose the same or another type and repeat.

---

### 5.3 Materials Entry

- **Date:** Required.  
- **Rows:** Item, Qty, Unit, Unit Price. **Total Amount** is computed (Qty × Unit Price) per row.
- You can add multiple rows (e.g. **+ Add row** or similar). Delete rows you do not need.
- **Total** at the top is the sum of all row amounts.  
- Click **Submit** to save. All rows are saved under one invoice number for that date.

---

### 5.4 Labor Entry

- **Date:** Required.  
- **Next Invoice #** is shown for the selected date.
- **Per row:**
  - **Employee:** Select from Construction workers (autocomplete). Each employee can appear only once per submission.
  - **Rate per Day:** Filled automatically from the employee’s rate (read-only).
  - **No. of Days:** Number of days worked.
  - **Overtime Hours:** Optional.  
  - **Overtime Amount:** Read-only; computed as **(Rate per Day ÷ 8) × Overtime Hours**.
  - **Labor Total Amount:** Read-only; **Regular (Rate × Days) + Overtime Amount**.
- Add more rows for other employees. **Total Amount** at the top is the sum of all rows.
- Click **Submit** to save. All rows are saved under one invoice number.

---

### 5.5 Gasoline Entry

- **Date:** Required.  
- One or more **Amount** rows.  
- Total is the sum of amounts. Submit to save under one invoice number.

---

### 5.6 Documents Entry

- **Date:** Required.  
- Rows: **Document Description** (or reference) and **Amount**.  
- Add/delete rows as needed. Submit to save.

---

### 5.7 Obligation Entry (Admin Only)

- Same idea as Documents: reference and amount per row, with date.  
- Available only when logged in as **Admin**.

---

### 5.8 Activity Entry (Admin Only)

- **Activity Description**, **Activity Date & Time**, **Status** (e.g. Pending, In Progress, Completed, On Hold).  
- Used to log project milestones or tasks, not monetary expenses.  
- Available only when logged in as **Admin**.

---

## 6. Reports and Viewing

### 6.1 View (Reports Overview)

1. **Construction** → **View**.
2. You see a searchable list of projects (name, site, contractor, status, dates, duration, amount).
3. **Click a row** → **Project Overview** for that project.

### 6.2 Project Overview

- **Header:** Project name, site, contractor, status, NTP date, completion date, duration.
- **Financial Summary / Balance Sheet:**  
  Contract Price, breakdown of expenses (Materials, Labor, Gasoline, Documents, Obligations), Total Expenses, Balance (Profit/Loss).
- **View By Invoice:**  
  - Click to expand a table of invoices (Invoice #, Date, Total).  
  - Click an invoice row to expand **line items** (date, type, description, qty, unit, unit price, amount).
- **Itemized Project Expenses:** Full list of expenses (excluding Activity).

### 6.3 Balance Sheet (Corporate)

1. **Corporate** → **View Balance Sheet**.
2. Optionally select a **Project** to limit the report; otherwise all projects are included.
3. View **Revenue** (contract price), **Expenses** by type, and **Balance** per project and overall.
4. Use **Export PDF** (if available) to download the balance sheet.

---

## 7. Corporate-Only Tasks

### 7.1 New Project

- **Corporate** → **New Project** → Fill form → **Save Project**.  
- See [Setting Up – Creating the First Project](#33-creating-the-first-project-corporate).

### 7.2 Update Project

1. **Corporate** → **Update Project**.
2. Table lists all projects (search available). Click a **row** to open the **Edit Project** modal.
3. Change: Project Name, Contractor, Site, NTP Date, Completion Date, Duration, Contract Price, **Status** (e.g. Planning, Ongoing, Completed).
4. Click **Update** to save, or **Delete** to remove the project (and all its expenses).

### 7.3 Edit Entry (Edit Expense Line Items)

1. **Corporate** → **Update Project**.
2. In the **Action** column, click **Edit Entry** for the desired project.
3. **Edit Entries** page opens:
   - **Header:** Project name, site, contractor, status, dates, duration, contract price.
   - **Table:** Expenses grouped by **Invoice** (Date, Invoice #, Total).  
   - **Click an invoice row** to expand and show **line items**.
4. For a line item, click **Edit** → modal opens with fields for that type (Materials: item, qty, unit, unit price, amount; Labor: employee, rate, days, overtime hours, amounts; etc.).
   - **Materials:** Amount is computed as Qty × Unit Price (read-only).
   - **Labor:** Overtime Amount and Labor Total are computed (read-only).
5. Adjust values and click **Save**. You return to the Edit Entries page with updated data.

---

## 8. Admin-Only Features

- **Obligation** and **Activity** in **Type of Entry** on Project Detail (see [5.7](#57-obligation-entry-admin-only) and [5.8](#58-activity-entry-admin-only)).
- Full access to Corporate features when the user is in Corporate (or has Admin role with access to Construction).

---

## 9. Tips and Troubleshooting

### Invoice Numbers

- Invoice numbers are generated **per date** (e.g. INV-YYYYMMDD-0001).  
- Selecting a **date** in an entry form may trigger fetching the next invoice number for that date.

### Labor

- **Overtime:** Rate per hour = Rate per Day ÷ 8. Overtime Amount = Rate per hour × Overtime Hours. Labor Total = (Rate × Days) + Overtime Amount.
- Ensure Construction workers have **Rate per day** set in **Manage Workers**.

### Search

- On **Construction Home** and **Update Project**, use the search box to filter by project name, site, contractor, or status.

### Permissions

- If you do not see **Corporate** menu, **New Project**, or **Update Project**, your account may not have **Corporate** department. Contact an administrator.
- If **Obligation** or **Activity** is missing from **Type of Entry**, you must be logged in as **Admin**.

### Editing After Submit

- To change or correct an expense after submission, use **Corporate** → **Update Project** → **Edit Entry** for that project, then edit the line item (see [7.3](#73-edit-entry-edit-expense-line-items)).

### Balance Sheet PDF

- **Corporate** → **View Balance Sheet** → use the **Export PDF** (or similar) option. Filter by project first if you want a single-project report.

---

## Quick Reference

| Task | Where |
|------|--------|
| Add a project | Corporate → New Project |
| Change project details or status | Corporate → Update Project → click row → Edit |
| Delete a project | Corporate → Update Project → click row → Delete (in modal) |
| Add Materials / Labor / Gasoline / Documents | Construction Home → open project → Type of Entry → fill form → Submit |
| Edit an expense line | Corporate → Update Project → Edit Entry → expand invoice → Edit on row → Save |
| View project finances | View → click project → Project Overview (or open project and use overview link) |
| View balance sheet | Corporate → View Balance Sheet |
| Manage workers for labor | Settings → Manage Workers |

---

*End of Construction Department User Manual*
