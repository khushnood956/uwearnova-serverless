"""
Isolated Configuration and Environment Security Tests
Validates strict APP_ENV requirements and production/staging security controls (F-SEC-01 & F-SEC-02).
"""

import os
import pytest
from pydantic import ValidationError

from app.core.config import Settings, VALID_ENVIRONMENTS, PROTECTED_ENVIRONMENTS


# Dummy test secrets for validation testing (safe, non-production)
DUMMY_VALID_SECRET = "dummy-testing-secure-key-at-least-32-chars-long!"
DUMMY_VALID_PASSWORD = "dummy-custom-db-password-12345"
DEV_DEFAULT_SECRET = "uninova-dev-insecure-secret-key-32-chars-minimum-needed"
DEV_DEFAULT_PASSWORD = "uninova_secure_password"


def test_app_env_missing_rejected(monkeypatch):
    """Scenario: APP_ENV missing -> Startup rejected."""
    monkeypatch.delenv("APP_ENV", raising=False)
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    errors = exc_info.value.errors()
    assert any(err["loc"] == ("APP_ENV",) and err["type"] == "missing" for err in errors)


@pytest.mark.parametrize("empty_val", ["", "   "])
def test_app_env_empty_rejected(monkeypatch, empty_val):
    """Scenario: APP_ENV empty -> Startup rejected."""
    monkeypatch.setenv("APP_ENV", empty_val)
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "APP_ENV must not be empty" in str(exc_info.value)


def test_app_env_prod_shorthand_rejected(monkeypatch):
    """Scenario: APP_ENV=prod -> Startup rejected (strict allowlist enforcement)."""
    monkeypatch.setenv("APP_ENV", "prod")
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert "Invalid APP_ENV 'prod'" in str(exc_info.value)


@pytest.mark.parametrize("unknown_env", ["unknown", "qa", "sandbox", "local", "docker"])
def test_app_env_unknown_rejected(monkeypatch, unknown_env):
    """Scenario: APP_ENV=unknown -> Startup rejected."""
    monkeypatch.setenv("APP_ENV", unknown_env)
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert f"Invalid APP_ENV '{unknown_env}'" in str(exc_info.value)


def test_app_env_development_accepted(monkeypatch):
    """Scenario: APP_ENV=development -> Accepted with development configuration."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("MYSQL_PASSWORD", raising=False)
    settings = Settings(_env_file=None)
    assert settings.APP_ENV == "development"
    # Development allows default development secrets
    assert settings.SECRET_KEY == DEV_DEFAULT_SECRET
    assert settings.MYSQL_PASSWORD == DEV_DEFAULT_PASSWORD


def test_app_env_test_accepted(monkeypatch):
    """Scenario: APP_ENV=test -> Accepted with test configuration."""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("MYSQL_PASSWORD", raising=False)
    settings = Settings(_env_file=None)
    assert settings.APP_ENV == "test"
    # Test environment allows default dev/test secrets
    assert settings.SECRET_KEY == DEV_DEFAULT_SECRET
    assert settings.MYSQL_PASSWORD == DEV_DEFAULT_PASSWORD


@pytest.mark.parametrize(
    "secret_key,mysql_password,expected_error",
    [
        (
            DEV_DEFAULT_SECRET,
            DUMMY_VALID_PASSWORD,
            "SECRET_KEY must be a cryptographically secure random string",
        ),
        (
            "too-short-secret",
            DUMMY_VALID_PASSWORD,
            "SECRET_KEY must be a cryptographically secure random string",
        ),
        (
            DUMMY_VALID_SECRET,
            DEV_DEFAULT_PASSWORD,
            "MYSQL_PASSWORD must not be the default development password",
        ),
    ],
)
def test_app_env_staging_with_weak_secrets_rejected(
    monkeypatch, secret_key, mysql_password, expected_error
):
    """Scenario: APP_ENV=staging with weak secrets -> Rejected with production-grade validation."""
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("SECRET_KEY", secret_key)
    monkeypatch.setenv("MYSQL_PASSWORD", mysql_password)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert expected_error in str(exc_info.value)


@pytest.mark.parametrize(
    "secret_key,mysql_password,expected_error",
    [
        (
            DEV_DEFAULT_SECRET,
            DUMMY_VALID_PASSWORD,
            "SECRET_KEY must be a cryptographically secure random string",
        ),
        (
            "short-secret",
            DUMMY_VALID_PASSWORD,
            "SECRET_KEY must be a cryptographically secure random string",
        ),
        (
            DUMMY_VALID_SECRET,
            DEV_DEFAULT_PASSWORD,
            "MYSQL_PASSWORD must not be the default development password",
        ),
    ],
)
def test_app_env_production_with_weak_secrets_rejected(
    monkeypatch, secret_key, mysql_password, expected_error
):
    """Scenario: APP_ENV=production with weak secrets -> Rejected."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", secret_key)
    monkeypatch.setenv("MYSQL_PASSWORD", mysql_password)

    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    assert expected_error in str(exc_info.value)


def test_app_env_production_with_valid_secrets_accepted(monkeypatch):
    """Scenario: APP_ENV=production with valid secrets -> Accepted."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", DUMMY_VALID_SECRET)
    monkeypatch.setenv("MYSQL_PASSWORD", DUMMY_VALID_PASSWORD)

    settings = Settings(_env_file=None)
    assert settings.APP_ENV == "production"
    assert settings.SECRET_KEY == DUMMY_VALID_SECRET
    assert settings.MYSQL_PASSWORD == DUMMY_VALID_PASSWORD


def test_app_env_staging_with_valid_secrets_accepted(monkeypatch):
    """Scenario: APP_ENV=staging with valid secrets -> Accepted."""
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("SECRET_KEY", DUMMY_VALID_SECRET)
    monkeypatch.setenv("MYSQL_PASSWORD", DUMMY_VALID_PASSWORD)

    settings = Settings(_env_file=None)
    assert settings.APP_ENV == "staging"
    assert settings.SECRET_KEY == DUMMY_VALID_SECRET
    assert settings.MYSQL_PASSWORD == DUMMY_VALID_PASSWORD
