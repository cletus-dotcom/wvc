# Deployment Guide: Render + Supabase (Free Tier)

This guide walks you through deploying your WVC Flask app to **Render (free tier)** with **Supabase (free tier)** as the database.

---

## Prerequisites

1. **GitHub account** (your code should be pushed to GitHub)
2. **Render account** (sign up at [render.com](https://render.com))
3. **Supabase account** (sign up at [supabase.com](https://supabase.com))

---

## Step 0: Migrate Existing PostgreSQL Database to Supabase (Optional)

If you have an existing PostgreSQL database (local or hosted) and want to migrate it to Supabase, follow these steps:

### 0.1 Export Your Existing Database

**On Windows (PowerShell):**

1. **Install PostgreSQL client tools** (if not already installed):
   - Download from [postgresql.org/download/windows](https://www.postgresql.org/download/windows/)
   - Or use Chocolatey: `choco install postgresql` (includes `pg_dump` and `psql`)
   - **Important**: The command is **`pg_dump`** (with "pg"), not `g_dump`. During install, check "Add PostgreSQL bin to PATH" so `pg_dump` works in PowerShell. If it's not in PATH, use the full path, e.g. `"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe"`.

2. **Export the database schema and data**:
   ```powershell
   # Export everything (schema + data) — command is pg_dump (not g_dump)
   pg_dump -h localhost -U postgres -d wvc -F c -f wvc_backup.dump
   
   # Or export as SQL (easier to inspect/edit)
   pg_dump -h localhost -U postgres -d wvc -f wvc_backup.sql
   ```

   **Parameters:**
   - `-h localhost`: Database host (use your actual host if remote)
   - `-U postgres`: Database username
   - `-d wvc`: Database name
   - `-F c`: Custom format (binary, smaller file) OR `-f wvc_backup.sql` for SQL format
   - `-f filename`: Output file path

3. **If prompted for password**, enter your PostgreSQL password.

**Alternative: Export schema only (no data)**:
   ```powershell
   pg_dump -h localhost -U postgres -d wvc --schema-only -f wvc_schema_only.sql
   ```

**Export data only (no schema)**:
   ```powershell
   pg_dump -h localhost -U postgres -d wvc --data-only -f wvc_data_only.sql
   ```

### 0.2 Create Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up/login
2. Click **"New Project"**
3. Fill in:
   - **Name**: `wvc-app` (or your choice)
   - **Database Password**: Create a strong password (save it!)
   - **Region**: Choose closest to your users
   - **Pricing Plan**: Select **Free**
4. Click **"Create new project"** (takes 1-2 minutes)

### 0.3 Import Database into Supabase

**Option A: Using psql (Command Line) - Recommended**

1. **Get your Supabase connection string**:
   - In Supabase dashboard: **Settings** → **Database**
   - Copy the **"URI"** connection string (replace `[YOUR-PASSWORD]` with your actual password)
   - Example: `postgresql://postgres:YourPassword123@db.abcdefghijklmnop.supabase.co:5432/postgres`

2. **Import the SQL dump**:
   ```powershell
   # If you exported as SQL file
   psql "postgresql://postgres:YourPassword123@db.abcdefghijklmnop.supabase.co:5432/postgres" -f wvc_backup.sql
   ```

   **Or if you exported as custom format (.dump)**:
   ```powershell
   pg_restore -d "postgresql://postgres:YourPassword123@db.abcdefghijklmnop.supabase.co:5432/postgres" wvc_backup.dump
   ```

3. **If you get "could not translate host name ... Unknown host"**, try:
   - **Wake up your Supabase project**: Free tier projects pause after inactivity. Go to [Supabase Dashboard](https://supabase.com/dashboard) → your project → if it says **Paused**, click **Restore** and wait 1–2 minutes, then run `pg_restore` again.
   - **Use the Connection Pooler (Session Mode)** URL (different hostname that often resolves better): Supabase Dashboard → **Settings** → **Database** → **Connection pooling** → copy **Session mode** URI and use that with `pg_restore -d "..." wvc_backup.dump`.
   - **URL-encode special characters in your password** (e.g. `!` → `%21`) in the connection string.

4. **If you get "password authentication failed for user"** when using the pooler URL:
   - The pooler uses the **same database password** you set when creating the Supabase project (not a different "pooler" password).
   - In Supabase: **Settings** → **Database** → copy the **Session mode** URI. It will show `[YOUR-PASSWORD]` — replace only that with your real database password. If the password contains `!`, `#`, `@`, `%`, etc., URL-encode them (e.g. `!` → `%21`, `#` → `%23`, `@` → `%40`).
   - Or try the **direct** connection (URI tab, not pooler) for `pg_restore` now that the project is awake: `postgresql://postgres:YOUR_PASSWORD_ENCODED@db.PROJECT_REF.supabase.co:5432/postgres`.

**Option B: Using Supabase SQL Editor (For Small Databases)**

1. In Supabase dashboard, go to **SQL Editor**
2. Click **"New query"**
3. Open your `wvc_backup.sql` file in a text editor
4. Copy the entire contents and paste into the SQL Editor
5. Click **"Run"** (or press `Ctrl+Enter`)

   **⚠️ Note**: This method works best for small databases (< 10MB). For larger databases, use `psql` (Option A).

**Option C: Using pgAdmin (GUI Tool)**

1. Download [pgAdmin](https://www.pgadmin.org/download/)
2. Add a new server connection using your Supabase connection string
3. Right-click on the `postgres` database → **Restore**
4. Select your `.dump` file and restore

### 0.4 Verify Migration

1. **Check tables in Supabase**:
   - Go to **Table Editor** in Supabase dashboard
   - You should see all your tables listed

2. **Check row counts**:
   - Click on a table → **View data**
   - Verify data matches your source database

3. **Test connection from your app**:
   - Update your local `.env` file with Supabase `DATABASE_URL`
   - Run your Flask app locally and verify it connects

### 0.5 Common Issues and Fixes

**Issue: "Permission denied" or "Access denied"**
- **Fix**: Make sure you're using the `postgres` user (default Supabase admin user)
- Check that your connection string uses the correct password

**Issue: "Relation already exists"**
- **Fix**: Drop existing tables in Supabase first:
  ```sql
  -- In Supabase SQL Editor, run:
  DROP SCHEMA public CASCADE;
  CREATE SCHEMA public;
  GRANT ALL ON SCHEMA public TO postgres;
  GRANT ALL ON SCHEMA public TO public;
  ```
  Then re-import your database.

**Issue: "Encoding mismatch" or "Character set errors"**
- **Fix**: Export with explicit encoding:
  ```powershell
  pg_dump -h localhost -U postgres -d wvc --encoding=UTF8 -f wvc_backup.sql
  ```

**Issue: "Foreign key constraint violations"**
- **Fix**: Import in the correct order, or disable constraints temporarily:
  ```sql
  -- Before import
  SET session_replication_role = 'replica';
  -- After import
  SET session_replication_role = 'origin';
  ```

**Issue: "Large file timeout"**
- **Fix**: Use `psql` command line instead of SQL Editor, or split the dump into smaller files

### 0.6 After Migration: Update Your App

1. **Update `.env` file** (local development):
   ```env
   DATABASE_URL=postgresql://postgres:YourPassword123@db.abcdefghijklmnop.supabase.co:5432/postgres
   ```

2. **Update Render environment variables** (production):
   - Go to Render → Your Service → **Environment**
   - Update `DATABASE_URL` with your Supabase connection string

3. **Run Flask migrations** (if using Flask-Migrate):
   ```powershell
   flask db upgrade
   ```
   This ensures your migration history is synced with Supabase.

---

## Step 1: Set Up Supabase (Free Tier)

### 1.1 Create a Supabase Project

1. Go to [supabase.com](https://supabase.com) and sign up/login
2. Click **"New Project"**
3. Fill in:
   - **Name**: `wvc-app` (or your choice)
   - **Database Password**: Create a strong password (save it!)
   - **Region**: Choose closest to your users
   - **Pricing Plan**: Select **Free**
4. Click **"Create new project"** (takes 1-2 minutes)

### 1.2 Get Your Database Connection String

1. In your Supabase project dashboard, go to **Settings** → **Database**
2. Scroll to **"Connection string"** section
3. Select **"URI"** tab
4. Copy the connection string. It looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
5. **Important**: Replace `[YOUR-PASSWORD]` with the password you set during project creation
6. Save this connection string — you'll need it for Render

### 1.3 (Optional) Use Connection Pooler (Recommended)

For better connection management, use Supabase's **pooler**:

1. In **Settings** → **Database**, find **"Connection pooling"**
2. Copy the **"Session mode"** connection string (port 5432)
3. This is better for production apps with multiple workers

---

## Step 2: Prepare Your Code for Deployment

### 2.1 Verify Required Files

Make sure these files exist in your repo root:

- ✅ `Procfile` (tells Render how to run your app)
- ✅ `runtime.txt` (specifies Python version)
- ✅ `requirements.txt` (all dependencies including `gunicorn`)
- ✅ `.gitignore` (excludes `venv/`, `.env`, etc.)

### 2.2 Commit and Push to GitHub

```bash
git add Procfile runtime.txt requirements.txt
git commit -m "Add deployment files for Render"
git push origin main
```

---

## Step 3: Deploy to Render (Free Tier)

### 3.1 Create a New Web Service

1. **Go to Render Dashboard**
   - Visit [render.com](https://render.com) and sign up/login
   - You'll see your dashboard with a list of services (empty if first time)

2. **Start Creating a Web Service**
   - Click the **"New +"** button (usually top-right or in the dashboard)
   - From the dropdown menu, select **"Web Service"**
   - If this is your first time, you may see a prompt to connect GitHub

3. **Connect GitHub (Required First Step)**
   
   **If you don't see Render in GitHub's Authorized OAuth Apps, you need to connect it first:**
   
   - On the Render "New Web Service" page, look for a button that says:
     - **"Connect GitHub"** or
     - **"Connect Git Provider"** or
     - **"Authorize GitHub"**
   - Click that button
   - You'll be redirected to GitHub to authorize Render
   - GitHub will ask you to:
     - **Authorize Render** to access your account
     - Choose which repositories to grant access:
       - Select **"All repositories"** (recommended for first time), OR
       - Select **"Only select repositories"** and choose your `wvc` repo
   - Click **"Authorize"** or **"Install"** on GitHub
   - You'll be redirected back to Render
   - **After this, Render will appear in your GitHub Authorized OAuth Apps list**
   
   **If you don't see a "Connect GitHub" button:**
   - Look at the "Credentials (1)" dropdown in the search area
   - Click it and see if there's an option to "Add GitHub" or "Connect GitHub"
   - Or try clicking on the "Git Provider" tab if it's not already selected

4. **Select Your Repository**
   
   **If you see "No results" in the search:**
   - **Clear the search field**: Click the "x" icon next to the search box to clear it
   - You should now see a list of all your GitHub repositories
   - **OR** type the actual name of your repository (not "wvc-app" - that's the service name you'll use later)
   
   **To find your repository:**
   - Look for the repository where you pushed your code (e.g., `wvc`, `wvc-flask-app`, or whatever you named it on GitHub)
   - The repository name is what you see on GitHub, not the service name
   
   **If you don't see any repositories:**
   - Check the **"Credentials (1)"** dropdown - make sure the correct GitHub account is selected
   - If you have multiple GitHub accounts connected, switch to the one with your repository
   - If no repositories appear, you may need to grant Render access to your repositories:
     - Go to GitHub → Settings → Applications → Authorized OAuth Apps
     - Find "Render" and make sure it has access to your repositories
   
   **Once you find your repository:**
   - Click on the repository name in the list
   - You should see a checkmark or it will be highlighted
   - Click **"Connect"** or **"Continue"** button (usually at the bottom)

5. **Configure Service Settings**
   
   Fill in the form with these exact values:

   | Field | Value | Notes |
   |-------|-------|-------|
   | **Name** | `wvc-app` | Or any name you prefer (lowercase, no spaces) |
   | **Region** | Choose closest to your users | e.g., `Oregon (US West)` or `Frankfurt (EU)` |
   | **Branch** | `main` | Or `master` if that's your default branch |
   | **Root Directory** | Leave **empty** | Only fill if your app is in a subfolder |
   | **Runtime** | `Python 3` | Should auto-detect from your files |
   | **Build Command** | `pip install -r requirements.txt` | Installs all dependencies |
   | **Start Command** | `gunicorn run:app` | Runs your Flask app |
   | **Plan** | **Free** | ⚠️ Note: spins down after 15 min idle |

   **Visual Guide:**
   ```
   ┌─────────────────────────────────────┐
   │ Name: wvc-app                       │
   │ Region: [Dropdown: Oregon]         │
   │ Branch: main                        │
   │ Root Directory: [leave empty]       │
   │ Runtime: Python 3                   │
   │ Build Command:                      │
   │   pip install -r requirements.txt   │
   │ Start Command:                      │
   │   gunicorn run:app                  │
   │ Plan: ○ Free  ● Starter  ○ Standard│
   └─────────────────────────────────────┘
   ```

6. **Important Notes:**
   - **Build Command**: This runs during deployment to install packages
   - **Start Command**: This is what keeps your app running (uses `Procfile` if present, but you can override here)
   - **Free Plan**: Perfect for testing, but service sleeps after 15 minutes of inactivity
   - **Auto-Deploy**: By default, Render auto-deploys on every push to your selected branch

### 3.2 Configure Environment Variables

In the Render service dashboard, go to **"Environment"** tab and add:

| Key | Value | Notes |
|-----|-------|-------|
| `SECRET_KEY` | `your-secret-key-here` | Generate a random string (e.g., use `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `DATABASE_URL` | `postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres` | **For Render: Use Connection Pooler (Session Mode)** - See troubleshooting if you get "Network is unreachable" errors |
| `FLASK_APP` | `run:app` | **REQUIRED** - Tells Flask where to find your app |
| `FLASK_ENV` | `production` | Optional, but recommended |

**Important**: 
- Replace `[PASSWORD]` with your actual Supabase password
- Replace `[PROJECT-REF]` with your actual Supabase project reference (e.g., `ohkdmmnjbmfynvjrrtsw`)
- **DO NOT** include brackets `[]` in the actual values
- Do **NOT** commit `.env` files with real credentials to GitHub

**⚠️ For Render Deployment: Use Connection Pooler (Session Mode)**

If you get "Network is unreachable" errors during deployment, use Supabase's **Connection Pooler (Session Mode)** instead of the direct connection:

1. Go to **Supabase Dashboard** → Your Project → Click **"Connect"** button
2. Find **"Connection pooling"** → **"Session mode"** (port 5432)
3. Copy that connection string and use it for `DATABASE_URL` in Render

**Example direct connection** (may not work from Render):
```
postgresql://postgres:MyPassword123@db.ohkdmmnjbmfynvjrrtsw.supabase.co:5432/postgres
```

**Example pooler connection** (recommended for Render):
```
postgresql://postgres.ohkdmmnjbmfynvjrrtsw:MyPassword123@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres
```

### 3.3 Deploy

1. **Review your settings** one more time (especially environment variables)
2. Click the **"Create Web Service"** button (usually at the bottom of the form)
3. **Render will now:**
   - Clone your GitHub repository
   - Install all dependencies from `requirements.txt` (this takes 2-3 minutes)
   - Start your app with `gunicorn run:app`
   - Assign a URL to your service

4. **Watch the deployment:**
   - You'll see a live log of the build process
   - Look for messages like:
     - ✅ "Cloning repository..."
     - ✅ "Installing dependencies..."
     - ✅ "Starting service..."
   - If you see errors, check the logs (scroll down in the same page)

5. **Get your app URL:**
   - Once deployment completes, you'll see: **"Your service is live at:"**
   - URL format: `https://wvc-app.onrender.com` (or whatever name you chose)
   - Click the URL to open your app in a new tab

6. **First-time access:**
   - The first request might take 10-30 seconds (cold start on free tier)
   - If you see an error, check the **"Logs"** tab in Render dashboard

### 3.4 Verify Deployment

1. Visit your Render URL (e.g., `https://wvc-app.onrender.com`)
2. You should see your app's login page or dashboard
3. If you see an error page, check:
   - **Logs tab** in Render dashboard for error messages
   - **Environment variables** are set correctly
   - **Database connection** is working (you'll need to run migrations first - see Step 4)

---

## Step 4: Run Database Migrations

**⚠️ Important**: Render's free tier does **NOT** include Shell access. Use one of these alternatives:

### 4.1 Option A: Using Render's Release Command (RECOMMENDED - Skip Local Connection Issues)

**This is the BEST option if you're having DNS/connection issues locally!**

This runs migrations automatically before each deployment on Render's servers (which have proper network access):

**⚠️ IMPORTANT: Before setting up Release Command, make sure `DATABASE_URL` is set in Render's Environment variables!**
- Go to **"Environment"** tab → Check if `DATABASE_URL` exists
- If not, add it with your Supabase connection string
- See Step 3.2 for details

1. **First, make sure your Render service is deployed** (even if it fails to start due to missing tables)

2. In your Render service dashboard:
   - Click **"Settings"** in the left sidebar
   - In the **right sidebar** (Settings submenu), click **"Build & Deploy"**

3. Scroll down to find **"Release Command"** field

4. Enter:
   ```
   flask db upgrade
   ```
   
   **Alternative (if above fails)**: Try this more explicit version:
   ```
   export FLASK_APP=run:app && flask db upgrade
   ```

5. Click **"Save Changes"** (usually at the bottom of the page)

**⚠️ CRITICAL**: Make sure these environment variables are set BEFORE setting the Release Command:
- `DATABASE_URL` (your Supabase connection string)
- `FLASK_APP=run:app`
- `SECRET_KEY` (any random string)

6. **Trigger a new deployment**:
   - Go to **"Manual Deploy"** tab (in left sidebar)
   - Click **"Deploy latest commit"**
   - OR make a small change and push to GitHub (triggers auto-deploy)

7. **Watch the logs**:
   - Go to **"Logs"** tab (in left sidebar)
   - You'll see the deployment process:
     - "Release phase starting..."
     - Migration output: "Running upgrade ... -> ..."
     - "Release phase completed"
     - Then your app starts

**Note**: This runs migrations on EVERY deploy. That's usually fine, but if you want to run it only once, remove the Release Command after first successful deploy.

**Why this works better**: Render's servers have proper network access to Supabase, so DNS resolution works there even if it fails on your local machine.

**Visual Guide:**
```
Left Sidebar          Right Sidebar (Settings submenu)
├─ wvc                ├─ General
├─ Events             ├─ Build & Deploy  ← Click here!
├─ Settings ← Click   ├─ Custom Domains
├─ Logs               ├─ PR Previews
└─ ...                └─ ...
                       
Then scroll down to find "Release Command" field
```

### 4.2 Option B: Run Migrations from Your Local Machine

You can run migrations locally by connecting to your Supabase database:

1. **Set up your local environment** (Windows PowerShell):
   
   **Method 1: Using environment variables (Recommended)**
   ```powershell
   # Replace [YOUR-PASSWORD] and [PROJECT-REF] with your actual Supabase values
   $env:DATABASE_URL="postgresql://postgres:MyPassword123@db.abcdefghijklmnop.supabase.co:5432/postgres"
   $env:SECRET_KEY="temp-key-for-migrations"
   ```
   
   **Method 2: Create a temporary .env.local file**
   ```powershell
   # Create the file (replace values with your actual Supabase connection string)
   @"
   DATABASE_URL=postgresql://postgres:MyPassword123@db.abcdefghijklmnop.supabase.co:5432/postgres
   SECRET_KEY=temp-key-for-migrations
   "@ | Out-File -FilePath .env.local -Encoding utf8
   ```
   
   **Method 3: Manual file creation**
   - Create a new file named `.env.local` in your project root (same folder as `run.py`)
   - Add these two lines (replace with your actual values):
     ```
     DATABASE_URL=postgresql://postgres:MyPassword123@db.abcdefghijklmnop.supabase.co:5432/postgres
     SECRET_KEY=temp-key-for-migrations
     ```
   - Save the file

2. **Run migrations**:
   ```powershell
   # If you used Method 1 (environment variables), just run:
   flask db upgrade
   
   # If you used Method 2 or 3 (.env.local file), your app will auto-load it:
   flask db upgrade
   ```

3. **Verify migrations ran**:
   - You should see output like: "Running upgrade ... -> ..., <revision>"
   - Check your Supabase dashboard → Table Editor to see if tables were created

4. **Clean up** (if you created .env.local):
   ```powershell
   # Delete the temporary file
   Remove-Item .env.local
   ```
   
   **⚠️ Important**: Never commit `.env.local` to Git - it contains your database password!

### 4.3 Option C: Create a One-Time Migration Script

Create a script that runs migrations and can be executed during deployment:

1. **Create a file** `run_migrations.py` in your project root:
   ```python
   from app import create_app
   from flask_migrate import upgrade
   
   app = create_app()
   with app.app_context():
       upgrade()
       print("Migrations completed successfully!")
   ```

2. **Add it to your Release Command** in Render:
   ```
   python run_migrations.py && gunicorn run:app
   ```
   
   **OR** modify your `Procfile`:
   ```
   release: python run_migrations.py
   web: gunicorn run:app
   ```

3. **Commit and push**:
   ```bash
   git add run_migrations.py Procfile
   git commit -m "Add migration script for Render"
   git push origin main
   ```

### 4.4 Option D: Manual SQL Execution (Last Resort)

If migrations fail, you can manually run SQL in Supabase:

1. Go to your Supabase project dashboard
2. Click **"SQL Editor"** (left sidebar)
3. Open each migration file from `migrations/versions/` folder
4. Copy the SQL statements (look for `op.execute()` calls)
5. Paste and run them in Supabase SQL Editor

**⚠️ Warning**: This is error-prone and not recommended. Use only if other options fail.

---

## Troubleshooting Database Connection Issues

### Error: "could not translate host name" or "Name or service not known"

This DNS resolution error usually means:

1. **Check if Supabase project is active** (MOST COMMON ISSUE):
   - Free tier projects **pause after inactivity**
   - Go to [Supabase Dashboard](https://supabase.com/dashboard)
   - Check if your project shows as **"Paused"** or **"Inactive"**
   - If paused, click **"Restore"** or **"Resume"** to wake it up
   - **Wait 1-2 minutes** for the database to be fully ready
   - Then try the connection again

2. **Verify Supabase hostname is correct**:
   - Go to Supabase Dashboard → **Settings** → **Database**
   - Scroll to **"Connection string"** section
   - Select **"URI"** tab
   - Copy the connection string again (make sure it's the correct project)
   - Check if the hostname matches exactly: `db.ohkdmmnjbmfynvjrrtsw.supabase.co`

3. **Test network connectivity**:
   ```powershell
   # Test if you can reach Supabase
   Test-NetConnection -ComputerName db.ohkdmmnjbmfynvjrrtsw.supabase.co -Port 5432
   ```
   - If this fails, your network/firewall might be blocking port 5432
   - Try from a different network (mobile hotspot) to test

4. **Check your internet connection**:
   ```powershell
   ping google.com
   ```

5. **Try using Supabase Connection Pooler** (Different hostname):
   - Go to Supabase Dashboard → Settings → Database
   - Find **"Connection pooling"** section
   - Use the **"Session mode"** connection string (port 5432)
   - This uses a different hostname that might resolve better
   - Example format: `postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres`
   ```powershell
   # Try with pooler connection string
   $env:DATABASE_URL="postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres"
   flask db upgrade
   ```

6. **Try URL-encoding special characters in password**:
   - Your password contains `!` which might need encoding
   - `!` should be encoded as `%21`
   - Example: If password is `w1lv!nzCo26`, try `w1lv%21nzCo26` in the connection string
   ```powershell
   # Try with URL-encoded password
   $env:DATABASE_URL="postgresql://postgres:w1lv%21nzCo26@db.ohkdmmnjbmfynvjrrtsw.supabase.co:5432/postgres"
   flask db upgrade
   ```

6. **Check firewall/proxy settings**:
   - Corporate networks sometimes block database connections (port 5432)
   - Try from a different network (mobile hotspot) to test
   - Windows Firewall might be blocking - temporarily disable to test

7. **Verify connection string format**:
   - Make sure there are no extra spaces or quotes
   - The format should be: `postgresql://postgres:PASSWORD@db.PROJECT-REF.supabase.co:5432/postgres`
   - Don't wrap it in quotes when setting environment variable

### Error: "Network is unreachable" in Pre-Deploy/Release Command

**This error occurs when running `flask db upgrade` as a Release Command or Pre-Deploy script.**

The error shows:
```
connection to server at "db.ohkdmmnjbmfynvjrrtsw.supabase.co" (2406:da18:243:7401:4dde:af1f:3955:2bb1), port 5432 failed: Network is unreachable
==> Pre-deploy has failed
```

**Most common causes (in order of likelihood):**

1. **DATABASE_URL not set in Render** (MOST COMMON - 90% of cases):
   - Go to Render Dashboard → Your Service → **"Environment"** tab (left sidebar)
   - **Check if `DATABASE_URL` environment variable exists**
   - If missing or incorrect:
     - Click **"Add Environment Variable"** (or edit existing)
     - Key: `DATABASE_URL`
     - Value: `postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`
     - **Important**: Replace `[YOUR-PASSWORD]` with your actual Supabase password
     - **Important**: Replace `[PROJECT-REF]` with your actual project reference (e.g., `ohkdmmnjbmfynvjrrtsw`)
     - Click **"Save Changes"**
   - **Trigger a new deployment** (Manual Deploy → Deploy latest commit)

2. **Supabase project is paused** (Free tier auto-pauses after 1 week of inactivity):
   - Go to Supabase Dashboard → Your Project
   - If you see "Project is paused" or a "Resume project" button:
     - Click **"Resume project"**
     - Wait 1-2 minutes for database to start
     - **Then trigger a new deployment in Render**

3. **IPv6 connectivity issue** (THIS IS YOUR ISSUE - Render can't reach Supabase via IPv6):
   - The error shows an IPv6 address `2406:da18:243:7401:4dde:af1f:3955:2bb1`, which Render cannot reach
   - **SOLUTION: Use Supabase's Connection Pooler (Session Mode)** which supports IPv4:
   
   **Step-by-step fix:**
   
   1. Go to **Supabase Dashboard** → Your Project → Click **"Connect"** button (or go to Settings → Database)
   
   2. In the connection dialog, look for **"Connection pooling"** section
   
   3. Find **"Session mode"** connection string (port 5432)
   
   4. Copy the connection string - it should look like:
      ```
      postgresql://postgres.ohkdmmnjbmfynvjrrtsw:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
      ```
   
   5. **Update `DATABASE_URL` in Render**:
      - Go to Render Dashboard → Your Service → **"Environment"** tab
      - Find `DATABASE_URL` (or add it if missing)
      - Replace the value with the **Session mode pooler connection string** you copied
      - **Important**: Make sure you replace `[YOUR-PASSWORD]` with your actual password
      - Click **"Save Changes"**
   
   6. **Trigger a new deployment**:
      - Go to **"Manual Deploy"** tab
      - Click **"Deploy latest commit"**
      - Watch the logs - it should now connect successfully!
   
   **Alternative: If you can't find the pooler connection string:**
   
   - Go to Supabase Dashboard → Settings → Database
   - Scroll to **"Connection string"** section
   - Look for **"Connection pooling"** → **"Session mode"**
   - Or manually construct it:
     - Format: `postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres`
     - Your project ref: `ohkdmmnjbmfynvjrrtsw`
     - Region: Check your Supabase project region (e.g., `ap-southeast-1`, `us-east-1`, etc.)
     - Example: `postgresql://postgres.ohkdmmnjbmfynvjrrtsw:YourPassword123@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres`

4. **Special characters in password not URL-encoded**:
   - If your password contains special characters (e.g., `!`, `@`, `#`, `%`), they need to be URL-encoded
   - Common encodings:
     - `!` → `%21`
     - `@` → `%40`
     - `#` → `%23`
     - `%` → `%25`
   - Example: If password is `MyPass!123`, use `MyPass%21123` in the connection string

**Step-by-Step Fix (Do This First):**

1. **Verify ALL required environment variables in Render**:
   ```
   Render Dashboard → Your Service → Environment tab
   → Check for these variables (all are REQUIRED):
   
   ✅ DATABASE_URL = postgresql://postgres:[YOUR-PASSWORD]@db.ohkdmmnjbmfynvjrrtsw.supabase.co:5432/postgres
   ✅ FLASK_APP = run:app
   ✅ SECRET_KEY = [any-random-string]
   
   → If any are missing, click "Add Environment Variable" and add them
   → Click "Save Changes"
   ```
   
   **Common mistakes:**
   - Forgetting to set `FLASK_APP` (causes "No application found" error)
   - Using brackets `[]` in `DATABASE_URL` (should be actual values)
   - Missing password in `DATABASE_URL`
   - Extra spaces or quotes around values

2. **Double-check the connection string format**:
   - Should start with `postgresql://`
   - Format: `postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`
   - No spaces, no quotes, no extra characters
   - Make sure password is correct (copy from Supabase Dashboard → Settings → Database)

3. **Check Supabase project status**:
   ```
   Supabase Dashboard → Your Project
   → Look for "Project is paused" message
   → If paused, click "Resume project"
   → Wait 1-2 minutes for database to start
   ```

4. **Trigger a new deployment**:
   ```
   Render Dashboard → Your Service → Manual Deploy tab
   → Click "Deploy latest commit"
   → Watch the logs to see if it succeeds
   ```

**If still failing, try Connection Pooler:**

1. Get pooler connection string from Supabase:
   - Supabase Dashboard → Settings → Database → Connection pooling
   - Copy "Session mode" connection string

2. Update DATABASE_URL in Render:
   - Replace the value with the pooler connection string
   - Save changes

3. Deploy again

### Error: "Network is unreachable" in Render Shell

**This error occurs when running `flask db upgrade` in Render's Shell.**

Same troubleshooting as above - check `DATABASE_URL` is set in Environment tab first!

### Error: "Connection refused" or "Connection timeout"

- Supabase project might be paused (free tier)
- Database might be starting up (wait 1-2 minutes)
- Check Supabase dashboard for project status

### Error: "password authentication failed"

- Double-check your password in the connection string
- Make sure you're using the password you set when creating the Supabase project
- Special characters in passwords might need to be URL-encoded (e.g., `!` becomes `%21`)

### Error: "Exited with status 1" or "Pre-deploy has failed"

**This error means your Release Command (`flask db upgrade`) failed.**

**Check the deployment logs** (Render Dashboard → Logs tab) to see the exact error. Common causes:

1. **"No application found" or "Could not locate a Flask application"**:
   - **Fix**: Add `FLASK_APP=run:app` to Environment variables
   - Go to Environment tab → Add Environment Variable → Key: `FLASK_APP`, Value: `run:app`

2. **"Network is unreachable"** (see troubleshooting above):
   - **Fix**: Check `DATABASE_URL` is set correctly in Environment variables
   - Verify Supabase project is not paused

3. **"ModuleNotFoundError" or import errors**:
   - **Fix**: Make sure all dependencies are in `requirements.txt`
   - Check Build Command is: `pip install -r requirements.txt`

4. **"OperationalError" or database connection errors**:
   - **Fix**: Verify `DATABASE_URL` format is correct (no brackets, actual password)
   - Try using Supabase Connection Pooler (see troubleshooting above)

**Quick Diagnostic Checklist:**

Before deploying, verify in Render → Environment tab:
- ✅ `DATABASE_URL` exists and has correct format (no `[PASSWORD]` placeholder)
- ✅ `FLASK_APP=run:app` is set
- ✅ `SECRET_KEY` is set (any random string)
- ✅ No extra spaces or quotes around values

**To see detailed error logs:**
1. Go to Render Dashboard → Your Service → **"Logs"** tab
2. Scroll to the "Release phase" section
3. Look for the actual error message (usually in red)
4. Match it to one of the errors above

---

## Step 5: Create Admin User

**⚠️ Important**: Render's free tier doesn't have Shell access. Use one of these alternatives:

### 5.1 Option A: Run from Your Local Machine (Easiest)

1. **Set your Supabase DATABASE_URL**:
   ```powershell
   # Windows PowerShell:
   $env:DATABASE_URL="postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
   $env:SECRET_KEY="temp-key"
   python create_admin.py
   ```

2. This creates the default admin user:
   - Username: `admin`
   - Password: `123`

3. **Test login**: Go to your Render app URL and log in with these credentials

**⚠️ Security Note**: Change the admin password immediately after first login!

### 5.2 Option B: Add Admin Creation to Release Command (One-Time)

If you want to create admin during deployment:

1. **Modify `create_admin.py`** to be idempotent (won't fail if admin exists):
   ```python
   # The script already checks if admin exists, so it's safe to run multiple times
   ```

2. **Add to Release Command** in Render Settings → Advanced:
   ```
   python create_admin.py && flask db upgrade
   ```

3. **Remove it after first deploy** (to avoid running on every deploy)

### 5.3 Option C: Create Admin via Web Interface

If your app has a registration page, you can:
1. Visit your deployed app URL
2. Use the registration/signup feature (if available)
3. Create the first admin user through the web interface

---

## Step 6: Test Your Deployment

1. Visit your Render URL: `https://wvc-app.onrender.com`
2. You should see the dashboard/login page
3. Log in with the admin credentials
4. Test key features:
   - Navigation between modules
   - Database operations
   - PDF exports (if applicable)

---

## Troubleshooting

### Deployed app is not the same as local (works on localhost, errors online)

If the app runs correctly on your laptop but behaves differently or shows errors on Render, use this checklist so the online app matches your local one.

#### 1. **Sync code: push all local changes to GitHub**

Render builds from your GitHub repo. If your latest code is only on your laptop, the deployed app will be an older version.

1. On your laptop, open a terminal in the project folder and run:
   ```powershell
   git status
   ```
2. If you see modified or untracked files, add and commit them, then push:
   ```powershell
   git add .
   git commit -m "Sync local changes for deployment"
   git push origin main
   ```
   (Use `master` instead of `main` if that is your default branch.)
3. In the Render dashboard, open your service → **Manual Deploy** → **Deploy latest commit** (or wait for auto-deploy if enabled).

#### 2. **Build from the same branch**

1. In the Render dashboard, open your **Web Service** (e.g. `wvc-app`) — not the Workspace (e.g. "bobix") settings.
2. In the **left sidebar** of that service, click **Settings**.
3. In the **right-hand sub-menu**, click **Build & Deploy** (some accounts show **Build Pipeline**).
4. On that page, find the **Branch** field. It must be the branch you push to (e.g. `main` or `master`).
5. If it was wrong, set the correct branch, save, and trigger a new deploy.

#### 3. **Environment variables (must match what the app needs)**

The app uses these in production; set them in Render → **Environment**:

| Variable       | Required | Example / notes |
|----------------|----------|------------------|
| `DATABASE_URL` | Yes      | Supabase URI; use **Session mode** pooler if you had "Network is unreachable". |
| `SECRET_KEY`   | Yes      | Any long random string (e.g. `python -c "import secrets; print(secrets.token_hex(32))"`). |
| `FLASK_APP`    | Yes      | `run:app` (needed for migrations and correct app loading). |

- If `DATABASE_URL` is set by Render with `postgres://`, the app now converts it to `postgresql://` automatically.
- Do not leave placeholders like `[YOUR-PASSWORD]` in `DATABASE_URL`.

#### 4. **Database schema in sync (migrations)**

If migrations did not run or failed on Render, the database can be missing tables or columns and you’ll get errors that don’t happen locally.

1. Open your **Web Service** → **Settings** (left sidebar) → **Build & Deploy** (or **Build Pipeline**) on the right.
2. Set **Pre-Deploy Command** (or **Release Command**) to:
   ```bash
   export FLASK_APP=run:app && flask db upgrade
   ```
3. Save and redeploy. Check the **Deploy** or **Logs** tab for any `flask db upgrade` errors.
4. If you see "relation already exists" or "column already exists", the migration scripts may need to be made idempotent (see migration troubleshooting earlier in this guide).

#### 5. **Find the actual error online**

To fix the right thing, you need the exact error from production:

1. In Render: open your service → **Logs** tab.
2. Reproduce the problem in the browser (open the page or action that fails).
3. In the logs, look for Python tracebacks (e.g. `Traceback`, `Error`, `Exception`). Copy the full error.
4. Check the browser: **F12** → **Console** for JavaScript errors, **Network** for failed requests (status 500, 404, etc.).

Once you have the exact message (e.g. missing table, missing column, `postgres://` module error, file not found), you can fix that in code or config and push again.

#### 6. **Quick checklist**

- [ ] All local changes are committed and pushed to the branch Render uses.
- [ ] Render **Branch** is correct (e.g. `main`).
- [ ] `DATABASE_URL`, `SECRET_KEY`, and `FLASK_APP` are set in Render **Environment**.
- [ ] Pre-Deploy/Release runs `flask db upgrade` and succeeds (no errors in deploy logs).
- [ ] You’ve checked Render **Logs** and browser console/network for the real error.

After these steps, the deployed app should match your local app. If a specific error persists, use the exact traceback from the logs to target the fix (e.g. a missing migration or env var).

---

### App Won't Start

- **Check logs**: Render dashboard → **"Logs"** tab
- **Common issues**:
  - Missing environment variables
  - Database connection errors (check `DATABASE_URL`)
  - Import errors (check `requirements.txt`)

### Database Connection Errors

- Verify `DATABASE_URL` is correct in Render environment variables
- Check Supabase project is active (free tier pauses after inactivity)
- Try using the **pooler** connection string instead

### Migrations Fail

- Make sure `FLASK_APP` is set (or use `flask db upgrade` explicitly)
- Check database permissions in Supabase
- Verify migrations folder is committed to Git

### App Spins Down (Free Tier)

- Free tier services sleep after **15 minutes** of inactivity
- First request after sleep takes ~30 seconds (cold start)
- Upgrade to paid plan for always-on service

---

## Free Tier Limitations

### Render Free Tier:
- ✅ 750 free instance hours/month
- ⚠️ Services spin down after 15 min idle
- ⚠️ Slower cold starts
- ✅ Free SSL/HTTPS

### Supabase Free Tier:
- ✅ 500 MB database
- ✅ 1 GB file storage
- ✅ Basic auth features
- ⚠️ Limited bandwidth
- ✅ No 30-day expiry (unlike Render's free Postgres)

---

## Next Steps (When Ready for Production)

1. **Upgrade Render**: Paid plan (~$7-25/mo) for always-on service
2. **Upgrade Supabase**: Pro plan ($25/mo) for more storage/features
3. **Custom Domain**: Add your domain in Render settings
4. **Monitoring**: Set up error tracking (e.g., Sentry)
5. **Backups**: Configure Supabase backups (Pro plan)

---

## Support

- **Render Docs**: [render.com/docs](https://render.com/docs)
- **Supabase Docs**: [supabase.com/docs](https://supabase.com/docs)
- **Flask Deployment**: [flask.palletsprojects.com/en/latest/deploying/](https://flask.palletsprojects.com/en/latest/deploying/)

---

**Good luck with your deployment! 🚀**
