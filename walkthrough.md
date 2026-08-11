# GlobalPulse Backend — Phase 1A–1C
## Complete Technical Summary

---

## What Was Built

GlobalPulse is an India-centric global financial intelligence backend.
Phase 1A–1C delivers the foundation layer: server, market data, and timezone engine.

---

## Phase 1A — Backend Foundation

### What was built
- FastAPI application with a proper **lifespan context manager** (startup/shutdown hooks)
- `/api/v1` versioned routing — all business endpoints live under this prefix
- Single `GET /api/v1/health` endpoint returning app name + version
- Environment-based configuration loaded at startup
- Structured logging to stdout
- Centralized global exception handling with a standard JSON error envelope
- Swagger/OpenAPI UI at `/docs` and `/redoc`

### Technical concepts used

**FastAPI lifespan**
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: create shared HTTP client, wire services
    yield
    # shutdown: close HTTP client cleanly
```
The lifespan pattern replaces deprecated `@app.on_event("startup")`. It guarantees the HTTP client is created once and shared across all requests, then released properly on shutdown.

**Pydantic-settings (BaseSettings)**
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    APP_NAME: str = "GlobalPulse"
    FINNHUB_API_KEY: str = ""
    LOG_LEVEL: str = "INFO"
```
Reads from environment variables or `.env` file. Validated at startup — wrong values raise a `ValidationError` before the server accepts any traffic.

**`@lru_cache` on `get_settings()`**
Ensures the settings object is created only once. Every module calling `get_settings()` gets the same cached instance.

**Centralized exception handling**
```python
# Standard error envelope — same shape for every error
{
  "error": {
    "code": "INSTRUMENT_NOT_FOUND",
    "message": "...",
    "timestampUtc": "2024-06-11T03:00:00+00:00"
  }
}
```
FastAPI's `app.exception_handler(SomeException)` is used. Python stack traces are never exposed to API consumers.

**Typed domain exception hierarchy**
```
GlobalPulseError (base)
  ├── ProviderUnavailableError    → HTTP 503
  ├── ProviderRateLimitError      → HTTP 429
  ├── ProviderAuthenticationError → HTTP 502
  ├── InstrumentNotFoundError     → HTTP 404
  └── InvalidExchangeError        → HTTP 404
```
Each exception carries its own `error_code` and `http_status`. The global handler just reads these — no if/else chains.

**Structured logging**
```python
logger.info("Fetching quote from Finnhub | symbol=%s", symbol)
```
Uses Python's standard `logging` module. API keys and tokens are never passed to any logger call. Third-party noisy loggers (`httpx`, `httpcore`, `uvicorn.access`) are suppressed.

### Files
```
app/main.py
app/core/config.py
app/core/logging.py
app/core/exceptions.py
app/api/v1/router.py
app/api/v1/health.py
app/api/v1/dependencies.py
```

---

## Phase 1B — Global Market Data

### What was built
- Abstract `MarketDataProvider` interface (ABC)
- `FinnhubMarketProvider` — concrete implementation using `httpx.AsyncClient`
- Normalized domain models for quotes and instruments
- Currency enrichment from instrument profile (Finnhub `/quote` has no currency field)
- Exchange registry with 10 exchanges across 8 countries
- Three APIs: `/markets`, `/quotes/{symbol}`, `/instruments/{symbol}`
- `MarketService` service layer — routers never touch Finnhub directly

### Technical concepts used

**Abstract Base Class (ABC) provider pattern**
```python
class MarketDataProvider(ABC):
    @abstractmethod
    async def get_quote(self, symbol: str) -> NormalizedQuote: ...

    @abstractmethod
    async def get_instrument(self, symbol: str) -> NormalizedInstrument: ...

    @abstractmethod
    async def close(self) -> None: ...
```
All of GlobalPulse's service layer talks to `MarketDataProvider`. The actual Finnhub HTTP calls are hidden inside `FinnhubMarketProvider`. Swapping providers later = implement the ABC, change one line in `main.py`.

**Dependency injection direction**
```
API Router
    ↓
MarketService            ← business logic lives here
    ↓
MarketDataProvider       ← interface (ABC)
    ↓
FinnhubMarketProvider    ← Finnhub-specific code isolated here
    ↓
Finnhub REST API
```
This direction is enforced — routers import only services, services import only providers, providers import nothing from routes.

**FastAPI dependency injection via `app.state`**
```python
# main.py (startup)
app.state.market_service = MarketService(provider=provider)

# dependencies.py
def get_market_service(request: Request) -> MarketService:
    return request.app.state.market_service
```
Services are created once at startup and injected into routes via `Depends()`. No service is instantiated per-request.

**`httpx.AsyncClient` with connection reuse**
```python
self._client = httpx.AsyncClient(
    base_url=self._base_url,
    timeout=httpx.Timeout(timeout),
    headers={"User-Agent": "GlobalPulse/0.1.0"},
)
```
A single client instance is shared for all Finnhub requests. This reuses TCP connections. Creating a new client per request would be wasteful and slow.

**Provider error translation**
```python
if response.status_code == 401 or response.status_code == 403:
    raise ProviderAuthenticationError(...)
if response.status_code == 429:
    raise ProviderRateLimitError(...)
except httpx.TimeoutException:
    raise ProviderUnavailableError(...)
```
Raw HTTP errors are caught at the provider boundary and translated to typed domain exceptions. The service layer and routes only see `GlobalPulseError` subclasses — never raw httpx errors.

**Finnhub's zero-value convention**
When a symbol is invalid or has no data, Finnhub's `/quote` returns `{"c": 0, "d": 0, ...}` — all zeros, not null. GlobalPulse explicitly treats `0` as unknown:
```python
price=fq.c if fq.c != 0 else None
```
This prevents `price: 0` appearing in responses when the real price is simply unknown.

**Currency enrichment pattern**
Finnhub's `/quote` endpoint returns no currency. Currency is sourced separately:
```python
async def _get_currency_for(self, symbol: str) -> Optional[str]:
    # best-effort call to /stock/profile2
    # returns None silently if unavailable
    # never defaults to "USD" or any other value
```
Called on every quote. If it fails, `currency: null` is returned — never invented.

**Normalized domain models (frozen dataclasses)**
```python
@dataclass(frozen=True)
class NormalizedQuote:
    symbol: str
    price: Optional[float]
    currency: Optional[str]   # null if Finnhub can't supply it
    ...
```
`frozen=True` prevents accidental mutation. Domain models never leave the service layer — they are converted to Pydantic response schemas at the router boundary.

**Pydantic v2 response schemas**
```python
class QuoteResponse(BaseModel):
    price: Optional[float] = Field(None)
    currency: Optional[str] = Field(None, description="null if unavailable")
```
Pydantic v2 uses `model_validate()` instead of v1's `parse_obj()`. All `Optional` fields default to `None` — not `0`, not `""`.

**Exchange registry (in-memory)**
```python
_EXCHANGES: list[ExchangeMetadata] = [...]
_CODE_INDEX = {ex.exchange_code: ex for ex in _EXCHANGES}
```
Indexed by exchange code for O(1) lookup. No database needed for static exchange metadata.

### Finnhub endpoints used

| Finnhub endpoint | Used for |
|-----------------|---------|
| `GET /api/v1/quote?symbol=AAPL` | Real-time price quote |
| `GET /api/v1/stock/profile2?symbol=AAPL` | Instrument name, exchange, country, currency |

### Files
```
app/domain/instrument.py
app/domain/market.py
app/domain/exchange.py
app/schemas/market.py
app/schemas/quote.py
app/schemas/instrument.py
app/providers/base/market_provider.py
app/providers/finnhub/models.py
app/providers/finnhub/provider.py
app/services/market_service.py
app/api/v1/markets.py
app/api/v1/quotes.py
app/api/v1/instruments.py
app/utils/datetime_utils.py
```

---

## Phase 1C — Timezone & Market Session Engine

### What was built
- `TimezoneService` using Python's `zoneinfo` module (IANA-aware, DST-correct)
- `TradingSession[]` multi-session model per exchange
- TSE (Tokyo) and HKEX (Hong Kong) configured with actual morning + afternoon sessions
- `MarketStatusService` computing OPEN/CLOSED with next-open/next-close times
- All timestamps returned in both UTC and IST (Asia/Kolkata)
- `holiday_calendar_applied: false` flag in every market-status response
- Two APIs: `/market-status`, `/market-status/{exchange}`

### Technical concepts used

**`zoneinfo` (Python 3.9+ standard library)**
```python
from zoneinfo import ZoneInfo
TZ_IST = ZoneInfo("Asia/Kolkata")
TZ_ET  = ZoneInfo("America/New_York")  # handles EDT/EST automatically
```
`zoneinfo` uses the IANA timezone database (`tzdata`). It automatically knows that `America/New_York` is UTC-5 in winter (EST) and UTC-4 in summer (EDT). No hard-coded offsets anywhere.

**Canonical timestamp flow**
```
Source local time
      ↓
UTC  ← stored, processed, compared
      ↓
IST  ← presented to Indian users
```
Every datetime in the backend is stored as UTC. IST is computed only at the API response layer.

**DST-safe conversion (via `zoneinfo`)**
```python
# WRONG — hard-coded offset, breaks during DST:
ist_time = utc_time + timedelta(hours=5, minutes=30)   # ❌

# GlobalPulse — zoneinfo handles DST automatically:
ist_time = utc_time.astimezone(ZoneInfo("Asia/Kolkata"))  # ✅
```
India doesn't observe DST, but US and Europe do. The same pattern handles both correctly.

**DST-sensitive dates explicitly tested**
```python
# US spring-forward: 2024-03-10 (02:00 → 03:00, EST → EDT)
# US fall-back:      2024-11-03 (02:00 → 01:00, EDT → EST)
# UK BST begins:     2024-03-31
# UK GMT resumes:    2024-10-27
```
Tests use actual IANA-confirmed DST transition dates.

**Multi-session `TradingSession[]` model**
```python
@dataclass(frozen=True)
class TradingSession:
    open_time: time   # local exchange time
    close_time: time  # local exchange time

# TSE — morning + afternoon (lunch break in between)
sessions=[
    TradingSession(time(9, 0), time(11, 30)),    # Morning
    TradingSession(time(12, 30), time(15, 30)),  # Afternoon
]
```
A single exchange can have multiple non-contiguous session windows. `active_session_for(local_time)` checks all windows — if any matches, the market is OPEN.

**Next-open computation with intraday-break awareness**
```python
# Step 1: Is there a LATER session today? (handles intraday breaks)
for session in exchange.sessions:
    if session.open_time > local_time and is_trading_day:
        return that session's open time

# Step 2: Search forward up to 7 days for next trading day
```
If TSE is checked at 11:45 (during lunch break), the engine returns 12:30 as `next_open` — not tomorrow morning.

**Holiday transparency flag**
```json
{
  "session_status": "OPEN",
  "holiday_calendar_applied": false
}
```
Since no holiday calendar is implemented, the `false` flag tells API consumers not to trust OPEN status blindly during potential holiday dates.

**Weekday check in exchange local time**
```python
weekday = now_local.weekday()   # 0=Monday ... 6=Sunday
is_trading_day = exchange.is_trading_day(weekday)
```
Done in the **exchange's local timezone**, not UTC. Saturday in New York can still be Friday in UTC — the check must use local time.

### Files
```
app/core/timezone.py
app/domain/market.py          (TradingSession, ExchangeMetadata, MarketStatus)
app/domain/exchange.py        (10-exchange registry with session windows)
app/schemas/market_status.py
app/services/market_status_service.py
app/api/v1/market_status.py
```

---

## Test Coverage

| Test file | Phase | Tests |
|-----------|-------|-------|
| `test_health.py` | 1A | Status 200, body fields, service name, version format |
| `test_config.py` | 1A | Default values, LOG_LEVEL normalisation, invalid env raises, `get_settings()` caching |
| `test_errors.py` | 1A | Unknown route → 404, standard error format, `timestampUtc` presence |
| `test_market_service.py` | 1B | Quote success, currency null when unavailable, missing fields, invalid symbol, timeout, auth error, rate limit, malformed response, instrument nullable fields, TSE/HKEX multi-session verification |
| `test_timezone_service.py` | 1C | Singapore→IST, Tokyo→IST, Hong Kong→IST, New York→IST (EST winter + EDT summer), London→IST (GMT winter + BST summer), US DST spring-forward, US DST fall-back, UK BST, midnight rollover, naive datetime error, invalid timezone error |
| `test_market_status.py` | 1C | OPEN during session, CLOSED before open, CLOSED after close, CLOSED weekend, NYSE EDT summer, NYSE EST winter, next-open on weekend, next-close when open, holiday flag always false, invalid exchange 404, case-insensitive exchange code |

**Result: 73 tests, 0 failures, 0.52s**

### Testing patterns used
- `pytest-asyncio` with `asyncio_mode = "auto"`
- `httpx.AsyncClient(transport=ASGITransport(app=app))` — in-process HTTP tests, no real server
- `MockMarketProvider` — test double for `MarketDataProvider` with `AsyncMock` per-test
- `unittest.mock.patch("app.services.market_status_service.datetime")` — clock freezing for OPEN/CLOSED tests
- Zero live Finnhub API calls in any unit test

---

## APIs Built

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| GET | `/api/v1/markets` | All supported exchanges |
| GET | `/api/v1/markets?country=India` | Filter by country |
| GET | `/api/v1/instruments/{symbol}` | Instrument profile |
| GET | `/api/v1/quotes/{symbol}` | Real-time quote |
| GET | `/api/v1/market-status` | Status of all exchanges |
| GET | `/api/v1/market-status/{exchange}` | Status of one exchange |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc UI |
| GET | `/openapi.json` | OpenAPI schema |

---

## Corrections Applied During Review

### 1. "No intraday break sessions" — contradiction fixed
The initial limitation said "no intraday break sessions". But the `TradingSession[]` array design already supports multiple sessions per exchange. Limitation reworded: *"multi-session model supported, but complete exchange-specific break/calendar accuracy is not guaranteed in Phase 1C."* TSE and HKEX were configured with their actual morning + afternoon session windows.

### 2. Holiday transparency flag added
Without a holiday calendar, the engine can return `OPEN` during a public holiday. Added `holiday_calendar_applied: false` to every market-status response — visible in both the response body and the Swagger description.

### 3. Finnhub instrument endpoint coverage — made explicit
Empty `{}` from `/stock/profile2` → `InstrumentNotFoundError` with message: *"...may be due to provider plan coverage limitations or an invalid symbol."* Data is never invented for missing fields.

### 4. Quote currency enrichment — enforced
Finnhub `/quote` has no currency field. Currency is fetched from `/stock/profile2` as a best-effort enrichment. If unavailable, `currency: null` — never defaulted to `"USD"` or any other value.

---

## What Doesn't Work (Confirmed Limitations)

### Non-US symbols on Finnhub free tier

| Symbol | Exchange | Reason |
|--------|----------|--------|
| `RELIANCE.NS` | NSE India | NSE data licensing — Finnhub global plan required |
| `RELIANCE.BO` | BSE India | BSE data licensing — same |
| `D05.SI` | SGX Singapore | SGX data licensing |
| `7203.T` | Tokyo (TSE) | TSE data licensing |
| `SHEL.L` | LSE UK | LSE data licensing |
| `VOW3.DE` | XETRA Germany | Deutsche Börse licensing |

**Root cause:** Stock exchange data is not free. Every exchange charges data vendors (like Finnhub) licensing fees. Finnhub passes these costs to users through paid plan tiers. The free tier only unlocks US market data (NYSE, NASDAQ).

**What our code does:** Detects the empty `{}` response and raises `InstrumentNotFoundError` with a clear message. No crash, no fake data.

**Fix options:**
- Upgrade to Finnhub Global plan — same code works, no changes
- Add a second `MarketDataProvider` for Indian data (NSE India unofficial API, Alpha Vantage, Marketstack)

### Holiday calendar — not implemented
The OPEN/CLOSED engine uses weekday + session-time only. Public holidays (NSE Diwali, NYSE Christmas, TSE Golden Week, LSE Bank Holidays) are not detected. `holiday_calendar_applied: false` communicates this in every response.

### Pre-market / post-market — not implemented
NYSE/NASDAQ extended hours (04:00–09:30 and 16:00–20:00 ET) are not modeled. The `MarketStatus` enum already has `PRE_MARKET` and `POST_MARKET` reserved — they just need the logic filled in.

### No database persistence
`repositories/` directory exists as a boundary but has no implementation. All data is in-memory. No caching. PostgreSQL integration is a future phase.

### Quote timestamp defaults to "now" when `t=0`
When Finnhub returns `t: 0` (no last trade time — happens outside market hours), GlobalPulse uses current UTC as the timestamp. It doesn't represent an actual trade time.

### `asset_type` is always EQUITY or null
Finnhub `/stock/profile2` has no direct asset-type field. Only `finnhubIndustry` (sector string) is available. GlobalPulse maps non-null `finnhubIndustry` → `EQUITY`. ETFs, bonds, indices always return `null` for `asset_type`.

---

## Libraries Used

| Library | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.135.3 | Async web framework, automatic OpenAPI |
| `uvicorn` | 0.44.0 | ASGI server |
| `pydantic` | 2.12.5 | Data validation and serialization |
| `pydantic-settings` | 2.14.2 | Env-based config via `BaseSettings` |
| `httpx` | 0.28.1 | Async HTTP client (Finnhub calls) |
| `python-dotenv` | 1.2.2 | `.env` file loading |
| `tzdata` | 2026.2 | IANA timezone database (Windows needs this for `zoneinfo`) |
| `pytest` | 9.0.3 | Test runner |
| `pytest-asyncio` | 1.4.0 | Async test support |
| `pytest-mock` | 3.15.1 | `AsyncMock` and mock helpers |
| `anyio` | 4.13.0 | Async backend for tests |
| `zoneinfo` | stdlib (3.9+) | DST-safe timezone handling |

---

## What Was Explicitly Not Built (Scope Boundary)

Per the original spec, these were out of scope and were not implemented — not even as stubs:

- NewsAPI / news ingestion
- Economic calendar / Trading Economics
- Global event detection
- War / disaster / geopolitical ingestion
- Market anomaly detection
- News correlation engine
- Ripple Effect Engine
- India Impact scoring
- AI / LLM explanations
- Alert system
- WebSockets
- Portfolio features
- Kafka / message queues
- Microservices
- Kubernetes
- Docker (deferred by user request)
- Worldwide holiday calendar
