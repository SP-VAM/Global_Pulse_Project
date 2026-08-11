# Global-Pulse

An India-centric global financial intelligence and market prediction platform.

## Features
- **Global Market Intelligence**: Real-time market status, anomalies, and correlation tracking.
- **India Impact Engine**: Macro transmission models for global economic events impacting Indian markets.
- **Stock Prediction Engine**: Technical indicator computations and ML stock predictions.
- **Expense Tracker**: Real-time user expense, income, and category budget tracking with PostgreSQL persistence.
- **User Authentication**: Secure JWT auth with phone OTP verification and session management.

## Project Structure
- `Frontend/`: Vite + React UI Dashboard
- `globalpulse-backend/`: FastAPI + Async SQLAlchemy PostgreSQL backend
- `Global_Pulse-main/`: Database SQL schema & triggers

## Setup & Running
1. **Backend**:
   ```bash
   cd globalpulse-backend
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   python -m uvicorn app.main:app --reload --port 8000
   ```

2. **Frontend**:
   ```bash
   cd Frontend
   npm install
   npm run dev
   ```
