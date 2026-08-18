# 🌐 GlobalPulse — AI-Powered Personal Finance & Market Intelligence Platform

> A full-stack financial intelligence platform combining personal finance management, real-time Nifty 50 stock tracking, ML-powered market predictions, goal planning, and push notifications — built for the modern Indian investor.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Docker Setup](#docker-setup-optional)
- [Environment Variables](#-environment-variables)
- [API Overview](#-api-overview)
- [ML Model — Stock Predictions](#-ml-model--stock-predictions)
- [Push Notifications (FRD-048)](#-push-notifications-frd-048)
- [Database & Migrations](#-database--migrations)
- [Running Tests](#-running-tests)
- [Team Onboarding](#-team-onboarding)
- [Contributing](#-contributing)

---

## 🔍 Overview

GlobalPulse is a comprehensive personal finance and market intelligence platform designed specifically for Indian users. It integrates expense tracking, investment goal planning, Nifty 50 stock analysis with XGBoost-based ML predictions, real-time market snapshots, and an intelligent push notification system — all in a single, unified dashboard.

---

## ✨ Features

### 💰 Personal Finance
- **Expense Tracker** — Log, categorize, and analyze expenses with monthly budget controls and alerts
- **Income Management** — Track multiple income sources with historical trend analysis
- **Budget Alerts** — Real-time notifications when spending exceeds budget thresholds
- **Net Savings Calculation** — Live computation of income vs. expenses vs. savings

### 🎯 Goals & Investments
- **Goal Planning** — Create financial goals with target amounts, deadlines, and progress tracking
- **Goal Contributions** — Record savings contributions against specific goals
- **Progress Analytics** — Visual progress bars, extra-saved calculations, completion status

### 📈 Market Intelligence
- **Nifty 50 Market Snapshot** — Live price, daily change, change %, and market cap for all 50 Nifty companies
- **Stock Price Alerts** — Automatic push notifications when any stock moves ≥ ±2% in a day
- **XGBoost ML Predictions** — 1-day, 5-day, 10-day directional predictions (UP / DOWN / HOLD)
- **Technical Indicators** — RSI, MACD, Bollinger Bands, EMA, SMA, volume analysis
- **News Sentiment** — Aggregated sentiment scoring (Bullish / Neutral / Bearish) per company
- **Sparkline Charts** — Smooth cubic Bezier 30-day price history charts with hover tooltips

### 🔔 Push Notifications (FRD-048)
- Expense added / unusual activity / budget limit reached
- Income recorded / goal milestone achieved / goal completed
- Stock price surge / drop / notable movement (real-time)
- Security alerts (new device login)
- Portfolio dividend announcements
- Firebase Cloud Messaging (FCM) support for web push

### 🎓 Learning Hub
- Financial literacy modules and market education content

### 🔐 Authentication
- Email/password with JWT tokens
- Google OAuth 2.0 social login
- OTP-based mobile and email verification
- Session management with device tracking

---

## 🛠 Tech Stack

### Backend
| Layer | Technology |
|-------|-----------|
| Framework | FastAPI 0.135 (async) |
| Language | Python 3.11+ |
| Database | PostgreSQL (Railway) |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| ML Engine | XGBoost 2.1 + scikit-learn |
| Market Data | yFinance, Finnhub, Trading Economics |
| News Data | NewsAPI |
| Auth | JWT (PyJWT) + Google OAuth + Firebase FCM |
| Rate Limiting | SlowAPI |
| Testing | pytest + pytest-asyncio (665 tests) |
| Deployment | Docker / Render |

### Frontend
| Layer | Technology |
|-------|-----------|
| Framework | React 18 + Vite 4 |
| Routing | React Router DOM 6 |
| Charts | Recharts + custom Sparkline (SVG) |
| Animations | Framer Motion + GSAP |
| 3D Graphics | Three.js + React Three Fiber |
| Icons | Lucide React + React Icons |
| PDF Export | jsPDF + jspdf-autotable |
| Auth | Firebase + Google OAuth |
| HTTP Client | Axios |
| Styling | Vanilla CSS (custom design system) |

---

## 📁 Project Structure

```
Global Pulse/
├── globalpulse-backend/          # FastAPI backend
│   ├── app/
│   │   ├── api/v1/               # API route handlers
│   │   │   ├── auth.py           # Authentication endpoints
│   │   │   ├── expenses.py       # Expense & income CRUD
│   │   │   ├── goals.py          # Financial goal management
│   │   │   ├── stocks.py         # Market snapshot & ML predictions
│   │   │   ├── notifications.py  # Push notification management
│   │   │   └── ...
│   │   ├── db/
│   │   │   ├── models/           # SQLAlchemy ORM models
│   │   │   └── session.py        # DB engine & session factory
│   │   ├── services/
│   │   │   ├── stock_prediction_service.py   # XGBoost ML inference
│   │   │   ├── stock_alert_service.py        # Price move notifications
│   │   │   ├── expense_service.py            # Expense business logic
│   │   │   ├── goal_service.py               # Goal tracking logic
│   │   │   ├── notification_service.py       # FCM push + DB notifications
│   │   │   ├── auth_service.py               # JWT + OAuth logic
│   │   │   └── ...
│   │   ├── repositories/         # DB query layer (repository pattern)
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── core/                 # Config, exceptions, middleware
│   │   └── main.py               # App entrypoint + lifespan
│   ├── alembic/                  # DB migration scripts
│   ├── tests/                    # 665 unit + integration tests
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── Frontend/                     # React + Vite frontend
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard/
│   │   │   │   ├── Home/         # Main dashboard + company cards
│   │   │   │   ├── ExpenseTracker/
│   │   │   │   ├── Goals/
│   │   │   │   ├── Investments/
│   │   │   │   ├── MarketAnalysis/
│   │   │   │   ├── LearningHub/
│   │   │   │   ├── Constituents/ # Nifty 50 company list
│   │   │   │   ├── Profile/
│   │   │   │   └── Settings/
│   │   │   ├── Landing/          # Public landing page
│   │   │   └── auth/             # Login, Register, OTP pages
│   │   ├── components/common/    # Reusable UI components
│   │   │   └── Sparkline/        # Custom SVG sparkline chart
│   │   ├── api/                  # Axios API client modules
│   │   └── styles/               # Global CSS design system
│   ├── package.json
│   ├── Dockerfile
│   └── .env
│
├── docker-compose.yml            # Full-stack Docker orchestration
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

| Tool | Minimum Version |
|------|----------------|
| Python | 3.11+ |
| Node.js | 18+ |
| npm / pnpm | Latest |
| PostgreSQL | 14+ (or use Railway cloud DB) |
| Git | Any recent version |

---

### Backend Setup

```bash
# 1. Navigate to backend directory
cd globalpulse-backend

# 2. Create a virtual environment
python -m venv venv

# 3. Activate the virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. Install all dependencies
pip install -r requirements.txt

# 5. Set up environment variables
cp .env.example .env
# Then fill in the values in .env (see Environment Variables section)

# 6. Run database migrations
alembic upgrade head

# 7. Start the development server
uvicorn app.main:app --reload --port 8000
```

Backend will be live at: **http://localhost:8000**  
Interactive API docs: **http://localhost:8000/docs**

---

### Frontend Setup

```bash
# 1. Navigate to frontend directory
cd Frontend

# 2. Install dependencies
npm install
# or if using pnpm:
pnpm install

# 3. Set up environment variables
# .env file already exists — verify VITE_API_BASE_URL points to your backend

# 4. Start the development server
npm run dev
```

Frontend will be live at: **http://localhost:5173**

---

### Docker Setup (Optional)

Run the full stack with a single command:

```bash
# From the project root
docker-compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

---

## 🔑 Environment Variables

### Backend (`globalpulse-backend/.env`)

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `JWT_SECRET_KEY` | Secret key for JWT token signing | ✅ |
| `FINNHUB_API_KEY` | Finnhub market data API key | ✅ |
| `NEWS_API_KEY` | NewsAPI key for sentiment analysis | ✅ |
| `TRADING_ECONOMICS_API_KEY` | Trading Economics macro data key | Optional |
| `FIREBASE_CREDENTIALS` | Firebase service account JSON (for FCM push) | Optional |
| `APP_ENV` | `development` or `production` | ✅ |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` | Optional |

Get API keys from:
- Finnhub: https://finnhub.io/register
- NewsAPI: https://newsapi.org/register
- Trading Economics: https://tradingeconomics.com/settings/api.aspx
- Firebase: https://console.firebase.google.com

### Frontend (`Frontend/.env`)

| Variable | Description |
|----------|-------------|
| `VITE_API_BASE_URL` | Backend API URL (e.g. `http://localhost:8000`) |
| `VITE_GOOGLE_CLIENT_ID` | Google OAuth 2.0 Client ID |
| `VITE_FIREBASE_*` | Firebase web app configuration |

---

## 📡 API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | User registration |
| `POST` | `/api/v1/auth/login` | Email/password login |
| `POST` | `/api/v1/auth/google` | Google OAuth login |
| `GET` | `/api/v1/expenses/` | List expenses (paginated) |
| `POST` | `/api/v1/expenses/` | Add expense |
| `GET` | `/api/v1/expenses/summary` | Monthly summary (income, spending, savings) |
| `GET` | `/api/v1/goals/` | List financial goals |
| `POST` | `/api/v1/goals/` | Create goal |
| `POST` | `/api/v1/goals/{id}/contribute` | Add contribution to goal |
| `GET` | `/api/v1/stocks/market-snapshot` | Nifty 50 live snapshot |
| `GET` | `/api/v1/stocks/{symbol}/prediction` | XGBoost ML prediction |
| `GET` | `/api/v1/stocks/{symbol}/indicators` | Technical indicators |
| `GET` | `/api/v1/stocks/{symbol}/analysis` | Full analysis (prediction + indicators + sentiment) |
| `GET` | `/api/v1/notifications/` | Get user notifications |
| `PATCH` | `/api/v1/notifications/{id}/read` | Mark notification as read |
| `PATCH` | `/api/v1/notifications/read-all` | Mark all as read |
| `GET` | `/api/v1/health` | Server health check |

Full interactive documentation available at `/docs` (Swagger UI) and `/redoc`.

---

## 🤖 ML Model — Stock Predictions

GlobalPulse uses an **XGBoost multi-class classifier** trained on Nifty 50 historical data to predict next-day, 5-day, and 10-day price direction.

### How it works
1. **Data Source**: yFinance pulls up to 1 year of OHLCV data per ticker
2. **Feature Engineering**: 20+ technical indicators (RSI, MACD, Bollinger Bands, EMA, momentum)
3. **Prediction**: Model outputs `UP` / `DOWN` / `HOLD` with confidence percentages
4. **News Sentiment**: Optional CSV-based sentiment enrichment from aggregated financial news
5. **Output**: Confidence %, probability breakdown (up/down/hold), top influencing features

### Supported Companies
All **50 Nifty 50** companies including RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, WIPRO, BHARTIARTL, and more.

### Model Artifacts
Model `.pkl` files are stored in `globalpulse-backend/app/data/models/` and are excluded from git (>100 MB). Contact the team to obtain model files.

---

## 🔔 Push Notifications (FRD-048)

The notification system delivers real-time alerts for:

| Event | Trigger |
|-------|---------|
| 📈 Stock Surge | Any Nifty 50 stock rises ≥ +3% in a day |
| 📉 Stock Drop | Any Nifty 50 stock falls ≤ −3% in a day |
| ⚡ Notable Move | Any stock moves ≥ ±2% in a day |
| 💸 Expense Added | Every expense/income transaction |
| ⚠️ Budget Alert | Monthly spending exceeds budget limit |
| 🎯 Goal Completed | Goal savings reach target amount |
| 🏦 Dividend Alert | Company announces dividend |
| 🔒 Security Alert | Login from a new device detected |

**Architecture**: Notifications are persisted to PostgreSQL (`notifications` table) and optionally dispatched as FCM web push via Firebase.

**Deduplication**: Stock alerts fire at most **once per stock per direction per calendar day** per user — no spam.

---

## 🗄 Database & Migrations

This project uses **Alembic** for database migrations with SQLAlchemy async models.

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description of change"

# Roll back the last migration
alembic downgrade -1

# View current migration state
alembic current
```

### Core Tables
- `users` — User accounts & auth
- `expenses` — All expense & income transactions
- `budgets` — Monthly budget limits per category
- `goals` — Financial goals
- `goal_contributions` — Contribution records per goal
- `notifications` — Push notification records
- `user_device_tokens` — FCM tokens for web push

---

## 🧪 Running Tests

```bash
cd globalpulse-backend

# Activate virtual environment first
venv\Scripts\activate  # Windows

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_expense_service.py

# Run with coverage report
pytest --cov=app --cov-report=term-missing
```

> **665 tests** covering services, repositories, API routes, and ML inference.

---

## 👥 Team Onboarding

Follow these steps when cloning the repo for the first time:

### Step 1 — Clone the repository
```bash
git clone https://github.com/SP-VAM/Global_Pulse_Project.git
cd Global_Pulse_Project
```

### Step 2 — Backend setup
```bash
cd globalpulse-backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### Step 3 — Configure environment
The `.env` file is already in the repo. If it's missing, copy from example and fill values:
```bash
cp .env.example .env
# Fill in DATABASE_URL, JWT_SECRET_KEY, API keys
```

### Step 4 — Run DB migrations
```bash
alembic upgrade head
```

### Step 5 — Start backend
```bash
uvicorn app.main:app --reload --port 8000
```

### Step 6 — Frontend setup (new terminal)
```bash
cd ../Frontend
npm install
npm run dev
```

### Step 7 — Verify everything works
- Backend health: http://localhost:8000/api/v1/health
- API docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

---

## 🤝 Contributing

1. Create a feature branch from `main`
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Make your changes and ensure tests pass
   ```bash
   pytest
   ```
3. Commit with a clear message
   ```bash
   git commit -m "feat: description of what you added"
   ```
4. Push and open a Pull Request to `main`

### Commit Message Convention
| Prefix | Use for |
|--------|---------|
| `feat:` | New feature |
| `fix:` | Bug fix |
| `refactor:` | Code refactor (no behavior change) |
| `test:` | Adding/updating tests |
| `docs:` | Documentation changes |
| `chore:` | Build, config, dependency changes |

---

## 📄 License

This project is proprietary and maintained by the GlobalPulse team at ValueMomentum.

---

<div align="center">
  <strong>Built with ❤️ by the GlobalPulse Team</strong><br/>
  <sub>FastAPI · React · XGBoost · PostgreSQL · Firebase</sub>
</div>
