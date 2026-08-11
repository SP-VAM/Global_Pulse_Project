"""
GlobalPulse Shared Rate Limiter
Provides a single Limiter instance imported by all API routers.

Rate limit tiers are read from application settings (config.py) so they
can be overridden via environment variables without code changes:

  RATE_LIMIT_LLM    — AI explanation / LLM-backed endpoints  (default: 30/minute)
  RATE_LIMIT_DATA   — Market data, single-item lookups        (default: 60/minute)
  RATE_LIMIT_LIST   — List / pagination endpoints             (default: 120/minute)
  RATE_LIMIT_HEALTH — Health check endpoint                   (default: 300/minute)

Usage in a router:
    from fastapi import Request
    from app.api.v1.limiter import limiter
    from app.core.config import get_settings

    _settings = get_settings()

    @router.get("/some-endpoint")
    @limiter.limit(_settings.RATE_LIMIT_LIST)
    async def handler(request: Request, ...):
        ...

The `request: Request` parameter is required by slowapi to extract the
client IP address used as the rate-limit key.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
