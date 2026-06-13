# Deployment Guide

This guide covers deploying the Expense Splitter to **Render** (backend) and **Vercel** (frontend), and the recommended commit structure for pushing to GitHub.

---

## Architecture Overview

```
GitHub Repo
├── backend/     → Render Web Service (Django + Gunicorn)
│                   + Render PostgreSQL database
└── frontend/    → Vercel (React SPA, static build)
```

```
Browser → Vercel (https://your-app.vercel.app)
             ↓ API calls to VITE_API_URL
          Render (https://expense-splitter-api.onrender.com/api/)
             ↓ SQL
          Render PostgreSQL
```

---

## Step 1 — Push to GitHub

### Initialise the repository

```bash
cd c:\Users\pawar\Documents\driveprj

git init
git branch -M main

# Stage files in logical commit order (see section below)
```

### Recommended Commit Order

Follow this order so each commit is independently buildable and reviewable:

```bash
# 1. Project skeleton & documentation
git add .gitignore README.md SCOPE.md DECISIONS.md AI_USAGE.md
git commit -m "chore: init repo with project docs and .gitignore"

# 2. Backend Django project structure
git add backend/manage.py backend/requirements.txt backend/Procfile backend/.env.example backend/render.yaml
git add backend/config/
git commit -m "feat(backend): Django project config, settings, urls, wsgi"

# 3. Database models
git add backend/expenses/models.py backend/expenses/migrations/
git commit -m "feat(backend): expense splitting data models and migrations"

# 4. CSV parser & anomaly detection engine
git add backend/expenses/anomaly_detector.py backend/expenses/csv_parser.py
git commit -m "feat(backend): CSV parser with 14-type rule-based anomaly detection"

# 5. Balance & settlement calculator
git add backend/expenses/balance_calculator.py
git commit -m "feat(backend): net balance calculator and greedy settlement algorithm"

# 6. REST API (serializers + views + urls)
git add backend/expenses/serializers.py backend/expenses/views.py backend/expenses/urls.py
git commit -m "feat(backend): DRF REST API — upload, expenses, balances, persons, config"

# 7. Admin registration
git add backend/expenses/admin.py backend/expenses/apps.py backend/expenses/__init__.py
git commit -m "feat(backend): Django admin registrations"

# 8. AI/LLM optional service
git add backend/ai_service/
git commit -m "feat(backend): optional OpenAI anomaly detection and expense categorisation"

# 9. Backend unit tests
git add backend/expenses/tests.py
git commit -m "test(backend): unit tests for CSV parsing, anomaly detection, settlements"

# 10. Sample data
git add sample_data/
git commit -m "chore: add sample CSV for demo and testing"

# 11. Frontend project setup
git add frontend/package.json frontend/vite.config.js frontend/postcss.config.js
git add frontend/tailwind.config.js frontend/index.html frontend/vercel.json
git commit -m "feat(frontend): Vite + React + Tailwind project setup"

# 12. Global styles & design system
git add frontend/src/index.css frontend/src/main.jsx
git commit -m "feat(frontend): global CSS design system — glassmorphism, tokens, animations"

# 13. API client
git add frontend/src/api/
git commit -m "feat(frontend): Axios API client for all backend endpoints"

# 14. UI components (one commit per component or all together)
git add frontend/src/components/Layout.jsx
git commit -m "feat(frontend): Layout component with tab navigation"

git add frontend/src/components/FileUpload.jsx
git commit -m "feat(frontend): FileUpload drag-and-drop CSV upload component"

git add frontend/src/components/ImportReport.jsx
git commit -m "feat(frontend): ImportReport anomaly table with colour-coded severity"

git add frontend/src/components/Dashboard.jsx
git commit -m "feat(frontend): Dashboard expense table with filters and pagination"

git add frontend/src/components/Balances.jsx
git commit -m "feat(frontend): Balances net view and simplified settlement arrows"

git add frontend/src/components/PersonManager.jsx
git commit -m "feat(frontend): PersonManager roommate/guest CRUD"

# 15. App root
git add frontend/src/App.jsx
git commit -m "feat(frontend): App root with tab state and upload flow"

# 16. Render Blueprint
git add render.yaml
git commit -m "chore: add Render Blueprint for one-click backend deploy"
```

### Push to GitHub

```bash
git remote add origin https://github.com/YOUR_USERNAME/expense-splitter.git
git push -u origin main
```

---

## Step 2 — Deploy Backend to Render

### Option A — Blueprint (recommended, one-click)

1. Go to [https://dashboard.render.com](https://dashboard.render.com) → **New → Blueprint**
2. Connect your GitHub repo
3. Render detects `render.yaml` and creates:
   - A **Web Service** (`expense-splitter-api`)
   - A **PostgreSQL** database (`expense-splitter-db`)
4. After creation, go to the Web Service → **Environment** tab and fill in:
   - `ALLOWED_HOSTS` → `expense-splitter-api.onrender.com,localhost`
   - `CORS_ALLOWED_ORIGINS` → *(fill after Vercel deploy)*
   - `CSRF_TRUSTED_ORIGINS` → *(fill after Vercel deploy)*
   - `OPENAI_API_KEY` → *(optional)*

### Option B — Manual

1. **New → Web Service** → connect repo → set **Root Directory** to `backend`
2. Build command: `pip install -r requirements.txt`
3. Start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120`
4. Add all env vars from `backend/.env.example`
5. **New → PostgreSQL** → create a database → copy the **Internal Database URL** into `DATABASE_URL` env var on the web service

> **Note:** The `Procfile`'s `release` phase (`python manage.py migrate`) runs automatically before each deploy — you never need to SSH in to run migrations.

---

## Step 3 — Deploy Frontend to Vercel

1. Go to [https://vercel.com](https://vercel.com) → **New Project** → import your GitHub repo
2. Set **Root Directory** to `frontend`
3. Framework preset: **Vite**
4. Build command: `npm run build` (auto-detected)
5. Output directory: `dist` (auto-detected)
6. Add environment variable:
   | Key | Value |
   |-----|-------|
   | `VITE_API_URL` | `https://expense-splitter-api.onrender.com` |
7. Deploy → copy the **Vercel deployment URL**

---

## Step 4 — Wire Render ↔ Vercel (CORS)

After both services are deployed, go back to **Render → Web Service → Environment** and update:

| Variable | Value |
|----------|-------|
| `CORS_ALLOWED_ORIGINS` | `https://your-app.vercel.app,http://localhost:5173` |
| `CSRF_TRUSTED_ORIGINS` | `https://expense-splitter-api.onrender.com,https://your-app.vercel.app` |
| `ALLOWED_HOSTS` | `expense-splitter-api.onrender.com,localhost,127.0.0.1` |

Render will redeploy automatically. Your frontend at Vercel can now call the backend API.

---

## Environment Variables Reference

### Backend (`backend/.env.example`)

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ Yes | Django secret key — Render can auto-generate |
| `DEBUG` | ✅ Yes | `False` in production |
| `DATABASE_URL` | ✅ Yes | PostgreSQL URL from Render |
| `ALLOWED_HOSTS` | ✅ Yes | Comma-separated hostnames |
| `CORS_ALLOWED_ORIGINS` | ✅ Yes | Comma-separated Vercel URLs |
| `CSRF_TRUSTED_ORIGINS` | ✅ Yes | Same as CORS + Render URL |
| `USD_TO_INR_RATE` | No | Default `83.0` |
| `OPENAI_API_KEY` | No | Enables AI features |
| `OPENAI_MODEL` | No | Default `gpt-3.5-turbo` |

### Frontend (Vercel dashboard or `frontend/.env.local` for local dev)

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | ✅ Yes (prod) | Your Render backend URL — **no trailing slash** |

> For local development, the Vite dev server proxies `/api` to `http://127.0.0.1:8000` automatically (see `vite.config.js`). You do **not** need `VITE_API_URL` locally.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `CORS error` in browser | `CORS_ALLOWED_ORIGINS` missing Vercel URL | Update env var on Render + redeploy |
| `403 CSRF error` on POST | `CSRF_TRUSTED_ORIGINS` not set | Add Render + Vercel URLs to `CSRF_TRUSTED_ORIGINS` |
| `500 Internal Server Error` | `SECRET_KEY` or `DATABASE_URL` missing | Check Render environment tab |
| Render deploy fails | Migration error | Check Render deploy logs for SQL error |
| Vercel shows blank page | `VITE_API_URL` not set | Add env var in Vercel dashboard, redeploy |
| Free Render instance slow | Cold start (spins down after 15 min) | Upgrade to Starter ($7/mo) or use UptimeRobot ping |
