"""Test configuration loading from environment and defaults."""

import pytest

from shared.config import Settings, get_settings


def test_settings_load_defaults():
    settings = get_settings()
    assert settings.jwt_secret is not None
    assert settings.channel_accumulator_cap == 40.0
    assert settings.risk_half_life_seconds == 240.0
    assert settings.demo_student1_username == "student1"
    assert settings.demo_faculty1_username == "faculty1"


def test_production_mode_rejects_insecure_jwt_secret():
    """Verify Section 10 rule: no hardcoded default secrets in production."""
    with pytest.raises(Exception) as exc_info:
        Settings(
            APP_ENV="production",
            JWT_SECRET="dev-insecure-custodian-ai-secret-key-change-in-production",
        )
    assert "Security Violation" in str(exc_info.value)


def test_production_mode_accepts_strong_jwt_secret():
    """Verify production mode accepts custom high-entropy secrets."""
    prod_settings = Settings(
        APP_ENV="production",
        JWT_SECRET="super-strong-production-cryptographic-secret-key-32chars",
    )
    assert prod_settings.app_env == "production"
    assert (
        prod_settings.jwt_secret
        == "super-strong-production-cryptographic-secret-key-32chars"
    )

