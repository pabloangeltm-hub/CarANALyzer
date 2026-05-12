import asyncio

import pytest
import resend

from tools.api.services.email_service import (
    EmailConfigurationError,
    EmailSettings,
    load_email_settings,
    send_email,
    send_payment_failed_email,
    send_plan_upgrade_email,
    send_welcome_email,
)


def test_load_email_settings_requires_api_key(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)

    with pytest.raises(EmailConfigurationError, match="RESEND_API_KEY"):
        load_email_settings()


def test_load_email_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_123")
    monkeypatch.setenv("AGARTHA_EMAIL_FROM", "Agartha <hello@example.com>")
    monkeypatch.setenv("AGARTHA_PUBLIC_URL", "https://app.example.com/")

    settings = load_email_settings()

    assert settings.api_key == "re_123"
    assert settings.from_email == "Agartha <hello@example.com>"
    assert settings.public_url == "https://app.example.com"


def test_send_email_uses_resend_async(monkeypatch):
    calls = []

    async def fake_send_async(params):
        calls.append(params)
        return {"id": "email_123"}

    monkeypatch.setattr(resend.Emails, "send_async", fake_send_async)
    settings = EmailSettings(
        api_key="re_test",
        from_email="Agartha <hello@example.com>",
        public_url="https://app.example.com",
    )

    result = asyncio.run(
        send_email(
            to="dealer@example.com",
            subject="Subject",
            html="<p>Hello</p>",
            tags=[{"name": "event", "value": "test"}],
            settings=settings,
        )
    )

    assert result == {"id": "email_123"}
    assert resend.api_key == "re_test"
    assert calls == [
        {
            "from": "Agartha <hello@example.com>",
            "to": ["dealer@example.com"],
            "subject": "Subject",
            "html": "<p>Hello</p>",
            "tags": [{"name": "event", "value": "test"}],
        }
    ]


def test_transactional_email_templates(monkeypatch):
    calls = []

    async def fake_send_async(params):
        calls.append(params)
        return {"id": f"email_{len(calls)}"}

    monkeypatch.setattr(resend.Emails, "send_async", fake_send_async)
    settings = EmailSettings(
        api_key="re_test",
        from_email="Agartha <hello@example.com>",
        public_url="https://app.example.com",
    )

    asyncio.run(send_welcome_email(to="a@example.com", dealer_name="Dealer A", settings=settings))
    asyncio.run(send_payment_failed_email(to="b@example.com", dealer_name="Dealer B", settings=settings))
    asyncio.run(
        send_plan_upgrade_email(
            to="c@example.com",
            dealer_name="Dealer C",
            plan="premium",
            settings=settings,
        )
    )

    assert calls[0]["subject"] == "Bienvenido a Agartha"
    assert calls[0]["tags"] == [{"name": "event", "value": "welcome"}]
    assert "billing" in calls[1]["html"]
    assert calls[1]["tags"] == [{"name": "event", "value": "payment_failed"}]
    assert "elite" in calls[2]["subject"]
    assert calls[2]["tags"] == [{"name": "event", "value": "plan_upgrade"}]
