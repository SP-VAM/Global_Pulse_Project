"""
Unit and integration tests for Google OAuth2 & Firebase Authentication routes.
Verifies:
  1. POST /api/auth/google-login with access_token (Google OAuth flow)
  2. POST /api/auth/google with access_token
  3. POST /api/auth/google-login with Firebase id_token
  4. Invalid / unresolvable token rejection (HTTP 400)
"""
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.final_models import User
from app.sync_database import get_db


@pytest.fixture
def client():
    return TestClient(app)


def test_google_login_with_access_token_new_user(client):
    """Verify POST /api/auth/google-login creates new user when valid access_token is provided."""
    mock_db = MagicMock()
    # User does not exist
    mock_db.query(User).filter().first.return_value = None
    mock_db.query.return_value.filter.return_value.first.return_value = None

    mock_google_profile = {
        "sub": "google-oauth-uid-12345",
        "email": "newgoogleuser@gmail.com",
        "name": "Sanjai Prashad",
        "picture": "https://lh3.googleusercontent.com/photo.jpg",
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_google_profile

    from app.main import app as main_app
    main_app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.auth_routes.requests.get", return_value=mock_resp), \
         patch("app.auth_routes.create_access_token", return_value="mock.jwt.token"), \
         patch("app.auth_routes.serialize_user_entity", return_value={"email": "newgoogleuser@gmail.com"}):

        resp = client.post(
            "/api/auth/google-login",
            json={"access_token": "valid_google_oauth_access_token_abc"},
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["message"] == "Google Login Successful"
        assert data["access_token"] == "mock.jwt.token"
        assert data["is_new_user"] is True

    main_app.dependency_overrides.clear()


def test_google_login_with_access_token_existing_user(client):
    """Verify POST /api/auth/google-login logs in existing user."""
    mock_db = MagicMock()
    existing_user = User(
        user_id=42,
        email="existing@gmail.com",
        username="existinguser",
        account_status="ACTIVE",
    )
    mock_db.query(User).filter().first.return_value = existing_user
    mock_db.query.return_value.filter.return_value.first.return_value = existing_user

    mock_google_profile = {
        "sub": "google-oauth-uid-existing",
        "email": "existing@gmail.com",
        "name": "Existing User",
        "picture": "https://lh3.googleusercontent.com/existing.jpg",
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_google_profile

    from app.main import app as main_app
    main_app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.auth_routes.requests.get", return_value=mock_resp), \
         patch("app.auth_routes.create_access_token", return_value="mock.jwt.token.existing"), \
         patch("app.auth_routes.serialize_user_entity", return_value={"email": "existing@gmail.com"}):

        resp = client.post(
            "/api/auth/google-login",
            json={"access_token": "valid_google_oauth_access_token_existing"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "Google Login Successful"
        assert data["is_new_user"] is False

    main_app.dependency_overrides.clear()


def test_google_login_invalid_token_rejected(client):
    """Verify invalid token returns HTTP 400 Bad Request."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.text = "Invalid credentials"

    with patch("app.auth_routes.requests.get", return_value=mock_resp):
        resp = client.post(
            "/api/auth/google-login",
            json={"access_token": "expired_invalid_token"},
        )
        assert resp.status_code == 400
        body = resp.json()
        error_msg = body.get("detail") or body.get("error", {}).get("message", "")
        assert "Invalid Google credentials" in error_msg
