"""
GlobalPulse Backend Configuration
Environment-based settings via pydantic-settings.
"""
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "GlobalPulse"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    APP_VERSION: str = "0.1.0"

    # Provider — Finnhub (market data)
    FINNHUB_API_KEY: str = ""
    FINNHUB_BASE_URL: str = "https://finnhub.io/api/v1"
    FINNHUB_TIMEOUT_SECONDS: float = 10.0

    # Provider — Trading Economics (economic & macro data)
    TRADING_ECONOMICS_API_KEY: str = ""
    TRADING_ECONOMICS_BASE_URL: str = "https://api.tradingeconomics.com"
    TRADING_ECONOMICS_TIMEOUT_SECONDS: float = 10.0

    # Provider — NewsAPI (news & global events)
    NEWS_API_KEY: str = ""
    NEWS_API_BASE_URL: str = "https://newsapi.org/v2"
    NEWS_API_TIMEOUT_SECONDS: float = 10.0

    # Provider — Stock Prediction Engine
    STOCK_PROVIDER: Literal["yfinance", "finnhub"] = "yfinance"
    STOCK_MODEL_DIR: str = "app/data/stocks/models"
    STOCK_DATA_DIR: str = "app/data/stocks/merged_data"

    # SMTP Email Provider Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = ""
    EMAILS_FROM_NAME: str = "GlobalPulse"

    # Database — PostgreSQL railway database configuration
    DATABASE_URL: str = ""

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        v_clean = (v or "").strip()
        if not v_clean:
            raise ValueError(
                "DATABASE_URL environment variable is required. Production must use Railway PostgreSQL database 'railway'."
            )
        if "sqlite" in v_clean.lower():
            raise ValueError(
                "DATABASE_URL must point to PostgreSQL database 'railway'. SQLite is strictly not permitted for application persistence."
            )
        return v_clean

    # Security & Auth
    # JWT_SECRET_KEY MUST be set via environment variable / .env file.
    # The empty default forces an explicit value to be provided.
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Logging
    LOG_LEVEL: str = "INFO"

    # ── Security: CORS ──────────────────────────────────────────────────
    # In development, all origins are permitted automatically.
    # In staging/production, explicitly list allowed origins via this env var.
    # Example: ALLOWED_ORIGINS=["https://app.globalpulse.io","https://www.globalpulse.io"]
    ALLOWED_ORIGINS: list[str] = []

    # ── Security: Trusted Hosts ─────────────────────────────────────────
    # Used by TrustedHostMiddleware in staging/production.
    # In development, all hosts are allowed (["*"]).
    # Default allowed hosts include local development hosts and the Render
    # deployment hostname so TrustedHostMiddleware accepts requests from Render.
    ALLOWED_HOSTS: list[str] = ["*", "*.onrender.com", "localhost", "127.0.0.1"]

    # ── Security: Rate Limiting (slowapi-compatible limit strings) ──────
    # AI explanation / LLM-backed endpoints (expensive per-request cost)
    RATE_LIMIT_LLM: str = "30/minute"
    # Market data, quotes, India impact single-item lookups
    RATE_LIMIT_DATA: str = "60/minute"
    # List / pagination endpoints (anomalies, correlations, historical, dashboard)
    RATE_LIMIT_LIST: str = "120/minute"
    # Health check endpoint
    RATE_LIMIT_HEALTH: str = "300/minute"
    # Auth endpoints — login, signup, OTP (brute-force / spam protection)
    RATE_LIMIT_AUTH: str = "10/minute"

    # ── Security: Request Body Size ─────────────────────────────────────
    # Maximum allowed Content-Length in bytes before returning HTTP 413.
    # Default: 1 MB (1_048_576 bytes).
    MAX_BODY_SIZE_BYTES: int = 1_048_576

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of {allowed}, got '{v}'")
        return upper

    @field_validator("FINNHUB_BASE_URL", "TRADING_ECONOMICS_BASE_URL", "NEWS_API_BASE_URL")
    @classmethod
    def validate_provider_url_uses_https(cls, v: str) -> str:
        """
        Enforce HTTPS for all external provider base URLs.
        Exceptions: http://localhost and http://127.0.0.1 are allowed for local
        development and unit-test mocking (httpx ASGI transport, mock servers).
        """
        _local_prefixes = ("http://localhost", "http://127.0.0.1", "http://testserver")
        if not v.startswith("https://") and not any(v.startswith(p) for p in _local_prefixes):
            raise ValueError(
                f"Provider base URL must use HTTPS to protect API keys in transit, got: '{v}'. "
                "Only http://localhost and http://127.0.0.1 are permitted for local development."
            )
        return v

    @model_validator(mode="after")
    def validate_runtime_security(self) -> "Settings":
        """
        Combined runtime security validator:
        1. Warn on missing API keys in development/staging.
        2. Raise on missing API keys or insecure JWT secret in production.
        """
        import warnings

        _INSECURE_JWT_DEFAULT = "globalpulse-super-secret-key-change-in-production"

        # JWT_SECRET_KEY validation
        if not self.JWT_SECRET_KEY or self.JWT_SECRET_KEY == _INSECURE_JWT_DEFAULT:
            if self.APP_ENV == "production":
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a strong random secret in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            else:
                warnings.warn(
                    "JWT_SECRET_KEY is not set or uses the insecure default. "
                    "Set a strong secret in your .env file before deploying.",
                    UserWarning,
                    stacklevel=2,
                )
                # Provide a stable fallback for local development only
                if not self.JWT_SECRET_KEY:
                    object.__setattr__(self, "JWT_SECRET_KEY", _INSECURE_JWT_DEFAULT)

        required_keys = {
            "FINNHUB_API_KEY": "Market-data endpoints will return provider errors.",
            "TRADING_ECONOMICS_API_KEY": "Economic/macro endpoints will return provider errors.",
            "NEWS_API_KEY": "News/global-events endpoints will return provider errors.",
        }

        missing_in_prod: list[str] = []
        for attr, warn_msg in required_keys.items():
            if not getattr(self, attr):
                if self.APP_ENV == "production":
                    missing_in_prod.append(attr)
                else:
                    warnings.warn(
                        f"{attr} is not set. {warn_msg}",
                        UserWarning,
                        stacklevel=2,
                    )

        if missing_in_prod:
            raise ValueError(
                f"Required API keys are missing in production environment: {missing_in_prod}. "
                "All provider API keys must be set before deploying to production."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
