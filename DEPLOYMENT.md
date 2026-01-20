# Deployment Guide: Render + Supabase (Free Tier)

This guide walks you through deploying your WVC Flask app to **Render (free tier)** with **Supabase (free tier)** as the database.

---

## Prerequisites

1. **GitHub account** (your code should be pushed to GitHub)
2. **Render account** (sign up at [render.com](https://render.com))
3. **Supabase account** (sign up at [supabase.com](https://supabase.com))

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

1. Go to [render.com](https://render.com) and sign up/login
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub account if prompted
4. Select your repository (`wvc` or your repo name)
5. Fill in the service details:

   - **Name**: `wvc-app` (or your choice)
   - **Region**: Choose closest to your users
   - **Branch**: `main` (or `master`)
   - **Root Directory**: Leave empty (or `./` if needed)
   - **Runtime**: `Python 3`
   - **Build Command**: 
     ```
     pip install -r requirements.txt
     ```
   - **Start Command**: 
     ```
     gunicorn run:app
     ```
   - **Plan**: Select **Free** (⚠️ spins down after 15 min idle)

### 3.2 Configure Environment Variables

In the Render service dashboard, go to **"Environment"** tab and add:

| Key | Value | Notes |
|-----|-------|-------|
| `SECRET_KEY` | `your-secret-key-here` | Generate a random string (e.g., use `python -c "import secrets; print(secrets.token_hex(32))"`) |
| `DATABASE_URL` | `postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres` | Your Supabase connection string from Step 1.2 |
| `FLASK_ENV` | `production` | Optional, but recommended |

**Important**: 
- Replace `[PASSWORD]` with your actual Supabase password
- Do **NOT** commit `.env` files with real credentials to GitHub

### 3.3 Deploy

1. Click **"Create Web Service"**
2. Render will:
   - Clone your repo
   - Install dependencies from `requirements.txt`
   - Start your app with `gunicorn`
3. Wait 3-5 minutes for the first deploy
4. You'll get a URL like: `https://wvc-app.onrender.com`

---

## Step 4: Run Database Migrations

### 4.1 Option A: Using Render Shell (Recommended)

1. In your Render service dashboard, go to **"Shell"** tab
2. Run:
   ```bash
   flask db upgrade
   ```
3. This applies all migrations to your Supabase database

### 4.2 Option B: Using Render's Deploy Script

You can also add a **release command** in Render:

1. In your service settings, find **"Advanced"** → **"Release Command"**
2. Add:
   ```
   flask db upgrade
   ```
3. This runs migrations automatically on each deploy

---

## Step 5: Create Admin User

### 5.1 Using Render Shell

1. In Render service dashboard → **"Shell"** tab
2. Run:
   ```bash
   python create_admin.py
   ```
3. This creates the default admin user (username: `admin`, password: `123`)

**⚠️ Security Note**: Change the admin password immediately after first login!

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
