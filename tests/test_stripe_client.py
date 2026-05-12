import stripe
import pytest

from tools.api.services.stripe_client import (
    StripeConfigurationError,
    StripeSettings,
    configure_stripe,
    load_stripe_settings,
)


def test_load_stripe_settings_requires_secret(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    with pytest.raises(StripeConfigurationError, match="STRIPE_SECRET_KEY"):
        load_stripe_settings()


def test_load_stripe_settings_reads_optional_env(monkeypatch):
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_123")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_123")
    monkeypatch.setenv("STRIPE_PRICE_STARTER", "price_starter")
    monkeypatch.setenv("STRIPE_PRICE_PRO", "price_pro")
    monkeypatch.setenv("STRIPE_PRICE_ELITE", "price_elite")
    monkeypatch.setenv("AGARTHA_PUBLIC_URL", "https://app.example.com")
    monkeypatch.setenv("STRIPE_MAX_NETWORK_RETRIES", "4")

    settings = load_stripe_settings()

    assert settings.secret_key == "sk_test_123"
    assert settings.webhook_secret == "whsec_123"
    assert settings.starter_price_id == "price_starter"
    assert settings.pro_price_id == "price_pro"
    assert settings.elite_price_id == "price_elite"
    assert settings.public_url == "https://app.example.com"
    assert settings.max_network_retries == 4


def test_load_stripe_settings_can_be_optional(monkeypatch):
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)

    settings = load_stripe_settings(require_secret=False)

    assert settings.secret_key == ""


def test_configure_stripe_sets_sdk_globals():
    settings = StripeSettings(secret_key="sk_test_configured", max_network_retries=3)

    configured = configure_stripe(settings)

    assert configured is stripe
    assert stripe.api_key == "sk_test_configured"
    assert stripe.max_network_retries == 3
