# 🧾 Expense Splitter

A full-stack web application for splitting shared expenses among roommates. Built with Django REST Framework, React.js, and Tailwind CSS. Features AI-powered anomaly detection during CSV import.

## 🏗 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+ / Django 4.2 / Django REST Framework |
| Frontend | React 18 / Vite 5 / Tailwind CSS 3 |
| Database | SQLite (dev) / PostgreSQL (production) |
| AI/LLM | OpenAI GPT-3.5/4 (optional, rule-based fallback) |
| Deployment | Render (backend) / Vercel (frontend) |

## 📦 Project Structure

```
├── backend/                 # Django REST Framework API
│   ├── config/              # Django project settings
│   ├── expenses/            # Main app (models, views, parsers)
│   ├── ai_service/          # OpenAI LLM integration
│   ├── manage.py
│   ├── requirements.txt
│   └── Procfile
├── frontend/                # React SPA
│   ├── src/
│   │   ├── components/      # UI components
│   │   ├── api/             # API client
│   │   └── App.jsx          # Main app
│   ├── package.json
│   └── vercel.json
├── sample_data/             # Test CSV file
├── README.md
├── SCOPE.md
├── DECISIONS.md
└── AI_USAGE.md
```

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Node.js 18+
- npm 9+

### Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your settings (optional: add OPENAI_API_KEY)

# Run migrations
python manage.py makemigrations expenses
python manage.py migrate

# Create superuser (optional, for admin panel)
python manage.py createsuperuser

# Start development server
python manage.py runserver
```

The API will be available at `http://127.0.0.1:8000/api/`

### Frontend Setup

```bash
# Navigate to frontend (in a new terminal)
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`

### Using the App

1. **Upload CSV**: Go to the Upload tab and drag-drop the sample CSV from `sample_data/Expenses Export.csv`
2. **View Report**: After import, the Import Report tab shows all detected anomalies
3. **Browse Expenses**: The Dashboard tab shows all expenses with filters
4. **Check Balances**: The Balances tab shows who owes whom

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload/` | Upload CSV file |
| `GET` | `/api/import-sessions/` | List import sessions |
| `GET` | `/api/import-sessions/:id/` | Import session details + anomalies |
| `GET` | `/api/expenses/` | List expenses (filterable) |
| `GET` | `/api/expenses/:id/` | Expense detail with splits |
| `GET` | `/api/balances/` | Net balance summary |
| `GET` | `/api/settlements/` | Simplified settlement plan |
| `GET/POST` | `/api/persons/` | List/create persons |
| `GET` | `/api/anomalies/` | List anomalies |
| `GET/PATCH` | `/api/config/` | Get/update exchange rate |

### Query Parameters for `/api/expenses/`
- `?person=Aisha` — filter by payer
- `?date_from=2026-02-01&date_to=2026-03-31` — date range
- `?currency=INR` — filter by currency
- `?search=rent` — search in description/notes
- `?settlement=true` — show only settlements
- `?flagged=true` — show only flagged expenses

## 🔍 Anomaly Detection

The app detects 14+ types of data quality issues:

| # | Type | Example |
|---|------|---------|
| 1 | Duplicate entries | "Dinner at Marina Bite" ≈ "dinner - marina bites" |
| 2 | Malformed dates | "Mar-14" instead of DD-MM-YYYY |
| 3 | Missing currency | Row 28 has no currency value |
| 4 | Zero amounts | Swiggy order with amount = 0 |
| 5 | Negative amounts | Parasailing refund = -30 |
| 6 | Mixed currencies | INR and USD on same date |
| 7 | Settlement rows | "Rohan paid Aisha back" |
| 8 | Split mismatch | equal type but unequal details |
| 9 | Missing split person | Person in split_with but not split_details |
| 10 | Ambiguous dates | "is this April 5 or May?" |
| 11 | Guest/temp people | Dev, Sam, Kabir not in permanent list |
| 12 | Case inconsistency | "priya" vs "Priya" |
| 13 | Missing payer | No paid_by value |
| 14 | Departed person | Meera still in split after moving out |

## 🚢 Deployment

### Backend → Render

1. Push the `backend/` directory to a Git repo
2. Create a new Web Service on [Render](https://render.com)
3. Set build command: `pip install -r requirements.txt && python manage.py migrate`
4. Set start command: `gunicorn config.wsgi:application`
5. Add environment variables from `.env.example`

### Frontend → Vercel

1. Push the `frontend/` directory to a Git repo
2. Import to [Vercel](https://vercel.com)
3. Set build command: `npm run build`
4. Set output directory: `dist`
5. Add environment variable: `VITE_API_URL=https://your-backend.onrender.com`

## 🔐 Environment Variables

See `backend/.env.example` for all required variables.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes (prod) | dev key | Django secret key |
| `DEBUG` | No | True | Debug mode |
| `DATABASE_URL` | No | SQLite | PostgreSQL connection string |
| `OPENAI_API_KEY` | No | — | OpenAI API key for AI features |
| `USD_TO_INR_RATE` | No | 83.0 | Exchange rate |
| `CORS_ALLOWED_ORIGINS` | Yes (prod) | localhost | Frontend URL |

## 📝 License

Built for the Spreetail internship assignment.
