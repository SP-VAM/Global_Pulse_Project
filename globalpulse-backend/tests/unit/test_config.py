"""Phase 1A — Configuration loading tests."""
import pytest
import os
from unittest.mock import patch


def test_default_settings_load() -> None:
    """Settings should load with defaults when no .env file overrides exist."""
    from app.core.config import Settings
    s = Settings(
        FINNHUB_API_KEY="test-key",
        _env_file=None,
    )
    assert s.APP_NAME == "GlobalPulse"
    assert s.APP_VERSION == "0.1.0"
    assert s.APP_ENV == "development"
    assert s.LOG_LEVEL == "INFO"


def test_log_level_validated_uppercase() -> None:
    """LOG_LEVEL should be normalised to uppercase."""
    from app.core.config import Settings
    s = Settings(FINNHUB_API_KEY="x", LOG_LEVEL="debug", _env_file=None)
    assert s.LOG_LEVEL == "DEBUG"


def test_invalid_log_level_raises() -> None:
    """An invalid LOG_LEVEL should raise a ValidationError at startup."""
    from pydantic import ValidationError
    from app.core.config import Settings
    with pytest.raises(ValidationError):
        Settings(FINNHUB_API_KEY="x", LOG_LEVEL="VERBOSE", _env_file=None)


def test_get_settings_is_cached() -> None:
    """get_settings() must return the same cached instance on repeated calls."""
    from app.core.config import get_settings
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2


def test_settings_accept_production_env() -> None:
    from app.core.config import Settings
    # Production mode requires all three provider API keys and a strong JWT secret
    s = Settings(
        APP_ENV="production",
        FINNHUB_API_KEY="pk_live_key",
        TRADING_ECONOMICS_API_KEY="te_live_key",
        NEWS_API_KEY="news_live_key",
        JWT_SECRET_KEY="a-strong-random-secret-for-testing-purposes-only",
        _env_file=None,
    )
    assert s.APP_ENV == "production"


def test_invalid_app_env_raises() -> None:
    from pydantic import ValidationError
    from app.core.config import Settings
    with pytest.raises(ValidationError):
        Settings(FINNHUB_API_KEY="key", APP_ENV="invalid_env", _env_file=None)
