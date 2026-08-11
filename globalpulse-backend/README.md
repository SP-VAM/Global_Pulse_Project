# GlobalPulse Backend — Phase 1A–1C

> **India-centric global financial intelligence and market-awareness platform.**
> Current scope: Backend foundation · Finnhub market data integration · International timezone/market-session engine.

---

## Overview

GlobalPulse is designed to detect important global market and real-world events, understand their financial ripple effects, determine their relevance to India, and explain them clearly to Indian users.

The complete future flow is:

```
Global Data → Event Detection → News Correlation → Ripple Effect
           → India Impact → Prioritization → Alert → Financial Awareness
```

This release implements **Phase 1A–1E and Dashboard Backend**.

---

## Implemented Phases

### Phase 1A — Backend Foundation

- FastAPI application with lifespan-managed startup/shutdown
- `/api/v1` API versioning
- Environment-based configuration via `pydantic-settings`
- Structured logging (secrets never logged)
- Centralized exception handling with standard JSON error format
- Swagger / OpenAPI documentation at `/docs`
- Health endpoint: `GET /api/v1/health`

### Phase 1B — Global Market Data

- Abstract `MarketDataProvider` interface — Finnhub is swappable
- `FinnhubMarketProvider` with shared `httpx.AsyncClient` (connection reuse, timeout, DST-aware)
- Normalized `NormalizedQuote` and `NormalizedInstrument` domain models
- Raw Finnhub JSON is never exposed via GlobalPulse APIs
- Currency for quotes is enriched from Finnhub's `/stock/profile2` (the `/quote` endpoint has no currency field); `null` if unavailable
- Provider errors mapped to typed domain exceptions
- Exchange registry covering 10 exchanges across 8 countries
- APIs: `/api/v1/markets`, `/api/v1/instruments/{symbol}`, `/api/v1/quotes/{symbol}`

### Phase 1C — Timezone & Market Session Engine

- `TimezoneService` using Python `zoneinfo` — DST handled automatically
- No hard-coded UTC offsets anywhere
- Multi-session `TradingSession[]` model (TSE and HKEX configured with actual morning + afternoon windows)
- `MarketStatusService` computing `OPEN`/`CLOSED` with next-open/next-close in both UTC and IST
- All timestamps returned in UTC and IST
- `holiday_calendar_applied: false` flag in all market-status responses for consumer transparency
- APIs: `/api/v1/market-status`, `/api/v1/market-status/{exchange}`

### Dashboard — Dashboard Feed & Search Engine

- `DashboardService` orchestrating news, global events, classification, deduplication, filtering, sorting, pagination, and optional quote enrichment
- Single-pass article retrieval with single-pass classification (no double-fetching)
- Single API contract powering the Dashboard UI
- Filters: `category`, `country`, `company`, `sector`, `type` (`NEWS` | `GLOBAL_EVENT`), date range (`from`, `to`), pagination (`page`, `pageSize`), and sorting (`sort=latest` | `sort=oldest`)
- Free-text search endpoint over normalized headlines, summaries, and tags: `GET /api/v1/dashboard/search?q={query}`
- Optional real-time market context quote enrichment for recognized company tags (isolated so quote failures do not fail the dashboard)
- Explicit presentation impact level handling (`HIGH`, `MEDIUM`, `LOW`, `UNKNOWN` — defaults to `UNKNOWN`)
- APIs: `/api/v1/dashboard`, `/api/v1/dashboard/search`


---

## Architecture

```
API Router (v1)
      ↓
Service Layer (MarketService, MarketStatusService)
      ↓
Provider / Domain (FinnhubMarketProvider, ExchangeRegistry)
      ↓
External API (Finnhub) / In-memory Exchange Config
```

Business logic never lives in routers. Finnhub is never called directly from routers.

---

## Project Structure

```
globalpulse-backend/
│
├── app/
│   ├── main.py                        # FastAPI app factory, lifespan, middleware
│   │
│   ├── api/v1/
│   │   ├── router.py                  # Aggregates all v1 routes
│   │   ├── health.py                  # GET /api/v1/health
│   │   ├── markets.py                 # GET /api/v1/markets
│   │   ├── quotes.py                  # GET /api/v1/quotes/{symbol}
│   │   ├── instruments.py             # GET /api/v1/instruments/{symbol}
│   │   ├── market_status.py           # GET /api/v1/market-status[/{exchange}]
│   │   └── dependencies.py            # FastAPI DI resolvers
│   │
│   ├── core/
│   │   ├── config.py                  # Pydantic-settings, env-based config
│   │   ├── logging.py                 # Structured logging setup
│   │   ├── exceptions.py              # Domain exceptions + global handlers
│   │   └── timezone.py                # TimezoneService (zoneinfo)
│   │
│   ├── domain/
│   │   ├── market.py                  # ExchangeMetadata, TradingSession, MarketStatus
│   │   ├── instrument.py              # NormalizedInstrument, NormalizedQuote
│   │   └── exchange.py                # Exchange registry (10 exchanges)
│   │
│   ├── schemas/
│   │   ├── market.py                  # Market listing Pydantic response schemas
│   │   ├── quote.py                   # Quote response schema
│   │   ├── instrument.py              # Instrument response schema
│   │   └── market_status.py           # Market status response schema
│   │
│   ├── services/
│   │   ├── market_service.py          # MarketService (quotes, instruments, markets)
│   │   └── market_status_service.py   # MarketStatusService (OPEN/CLOSED engine)
│   │
│   ├── providers/
│   │   ├── base/market_provider.py    # ABC: MarketDataProvider
│   │   └── finnhub/
│   │       ├── provider.py            # FinnhubMarketProvider
│   │       └── models.py              # Finnhub raw response models (internal only)
│   │
│   ├── repositories/                  # DB boundary placeholder (no impl yet)
│   └── utils/datetime_utils.py        # Datetime helpers
│
├── tests/
│   ├── conftest.py                    # Fixtures: app client, mock provider
│   ├── unit/
│   │   ├── test_health.py             # Phase 1A
│   │   ├── test_config.py             # Phase 1A
│   │   ├── test_errors.py             # Phase 1A
│   │   ├── test_market_service.py     # Phase 1B
│   │   ├── test_timezone_service.py   # Phase 1C
│   │   └── test_market_status.py      # Phase 1C
│   └── integration/                   # Placeholder for future live tests
│
├── .env.example
├── .gitignore
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## Supported Exchanges

| Code | Exchange | Country | Timezone |
|------|----------|---------|----------|
| NSE | National Stock Exchange of India | India | Asia/Kolkata |
| BSE | BSE Limited | India | Asia/Kolkata |
| SGX | Singapore Exchange | Singapore | Asia/Singapore |
| TSE | Tokyo Stock Exchange | Japan | Asia/Tokyo |
| HKEX | Hong Kong Exchanges | Hong Kong | Asia/Hong_Kong |
| NYSE | New York Stock Exchange | United States | America/New_York |
| NASDAQ | Nasdaq Stock Market | United States | America/New_York |
| LSE | London Stock Exchange | United Kingdom | Europe/London |
| XETRA | Deutsche Börse Xetra | Germany | Europe/Berlin |
| EURONEXT_PARIS | Euronext Paris | France | Europe/Paris |

---

## Setup

### Prerequisites

- Python 3.11+
- A [Finnhub](https://finnhub.io/) API key (free tier works for basic symbols)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd globalpulse-backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env and set FINNHUB_API_KEY=<your-key>
```

### Finnhub API Configuration

1. Register at [https://finnhub.io/](https://finnhub.io/)
2. Copy your API key from the dashboard
3. Add it to `.env`:
   ```
   FINNHUB_API_KEY=your_key_here
   ```

> **Note:** The free Finnhub tier supports US stocks (AAPL, MSFT, etc.) and some global symbols. Coverage for NSE/BSE/SGX may require a paid plan. The application will return a clear `INSTRUMENT_NOT_FOUND` error with a provider-limitation message — it will never invent fake data.

---

## Running Locally

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Running Tests

```bash
pytest
```

Or with verbose output:

```bash
pytest -v
```

Run a specific phase:

```bash
pytest tests/unit/test_health.py tests/unit/test_config.py tests/unit/test_errors.py   # Phase 1A
pytest tests/unit/test_market_service.py                                                # Phase 1B
pytest tests/unit/test_timezone_service.py tests/unit/test_market_status.py            # Phase 1C
```

> All unit tests use mocked providers — no live Finnhub API calls required.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/dashboard` | Main Dashboard feed with filters, sorting, and pagination |
| GET | `/api/v1/dashboard/search?q={query}` | Free-text search over Dashboard content |
| GET | `/api/v1/markets` | List all supported exchanges |
| GET | `/api/v1/markets?country=India` | Filter exchanges by country |
| GET | `/api/v1/instruments/{symbol}` | Normalized instrument profile |
| GET | `/api/v1/quotes/{symbol}` | Real-time market quote |
| GET | `/api/v1/market-status` | Status for all exchanges |
| GET | `/api/v1/market-status/{exchange}` | Status for one exchange (e.g. `SGX`) |

### Example Requests

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Dashboard feed
curl "http://localhost:8000/api/v1/dashboard?category=GEOPOLITICS&country=Singapore&page=1&pageSize=20"

# Dashboard search
curl "http://localhost:8000/api/v1/dashboard/search?q=oil"

# Get all markets
curl http://localhost:8000/api/v1/markets
```


# Filter by country
curl "http://localhost:8000/api/v1/markets?country=Japan"

# Get Apple quote
curl http://localhost:8000/api/v1/quotes/AAPL

# Get Apple instrument profile
curl http://localhost:8000/api/v1/instruments/AAPL

# All exchange statuses
curl http://localhost:8000/api/v1/market-status

# SGX status
curl http://localhost:8000/api/v1/market-status/SGX
```

### Example Quote Response

```json
{
  "symbol": "AAPL",
  "price": 210.42,
  "open": 208.00,
  "high": 212.00,
  "low": 207.50,
  "previous_close": 212.60,
  "change": -2.18,
  "change_percent": -1.03,
  "currency": "USD",
  "timestamp_utc": "2024-01-15T14:30:00+00:00",
  "timestamp_ist": "2024-01-15T20:00:00+05:30",
  "source": "FINNHUB"
}
```

### Example Market Status Response

```json
{
  "exchange": "SGX",
  "country": "Singapore",
  "session_status": "OPEN",
  "holiday_calendar_applied": false,
  "exchange_local_time": "2024-06-11T11:00:00+08:00",
  "current_time_utc": "2024-06-11T03:00:00+00:00",
  "current_time_ist": "2024-06-11T08:30:00+05:30",
  "next_open_utc": null,
  "next_open_ist": null,
  "next_close_utc": "2024-06-11T09:00:00+00:00",
  "next_close_ist": "2024-06-11T14:30:00+05:30"
}
```

### Standard Error Response

```json
{
  "error": {
    "code": "INSTRUMENT_NOT_FOUND",
    "message": "Instrument profile not found for symbol 'BADINSTR'. This may be due to provider plan coverage limitations or an invalid symbol.",
    "timestampUtc": "2024-06-11T03:00:00.123456+00:00"
  }
}
```

---

## Current Limitations (Phase 1C)

1. **No holiday calendar** — Market status does not account for exchange-specific public holidays (NSE Diwali muhurat, NYSE Christmas, TSE Golden Week, etc.). The API response includes `holiday_calendar_applied: false` so consumers are aware of this limitation. A dedicated holiday engine is planned for a future phase.

2. **No pre-market / post-market** — The status engine only detects `OPEN` / `CLOSED` for regular trading sessions. Extended-hours status is not implemented.

3. **Multi-session model supported; break accuracy not complete** — The `TradingSession[]` design allows TSE (lunch break) and HKEX (lunch break) to be configured with actual session windows. However, complete intraday break accuracy across all exchanges requires a full calendar engine.

4. **Finnhub instrument endpoint coverage varies** — `GET /api/v1/instruments/{symbol}` calls Finnhub's `/stock/profile2`. Coverage depends on your Finnhub subscription and the exchange. If the provider returns an empty response, a clear `INSTRUMENT_NOT_FOUND` error with a provider-limitation message is returned. Data is never invented.

5. **Quote currency is null if unavailable** — Finnhub's `/quote` endpoint does not return currency. Currency is enriched from the instrument profile endpoint (best-effort). If unavailable, `currency` is `null` — never defaulted.

6. **No database persistence** — The `repositories/` layer boundary exists but has no database implementation yet. PostgreSQL integration is planned for a future phase.

---

## Error Codes

| Code | HTTP | Meaning |
|------|------|---------|
| `INSTRUMENT_NOT_FOUND` | 404 | Symbol not found or provider plan limitation |
| `INVALID_EXCHANGE` | 404 | Unknown exchange code |
| `PROVIDER_UNAVAILABLE` | 503 | Finnhub timeout or malformed response |
| `PROVIDER_RATE_LIMIT` | 429 | Finnhub rate limit hit |
| `PROVIDER_AUTHENTICATION_ERROR` | 502 | Invalid API key |
| `NOT_FOUND` | 404 | Unknown API path |
| `INTERNAL_ERROR` | 500 | Unexpected backend error |

---

## Next Planned Phases

| Phase | Scope |
|-------|-------|
| 2A | NewsAPI integration — global news ingestion |
| 2B | Economic calendar (Trading Economics) |
| 2C | Global event detection and categorization |
| 3A | Ripple Effect Engine — market chain analysis |
| 3B | India Impact Engine — relevance scoring |
| 4A | Prioritization and alert system |
| 4B | AI/LLM-powered beginner explanations |
| 5A | WebSocket real-time event feed |
| 5B | Portfolio awareness layer |

---

*GlobalPulse Backend — Phase 1A–1C | Built with FastAPI + Pydantic v2 + zoneinfo*
