"""Transactional email service backed by Resend."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import resend

from tools.api.models.plan import PlanName, normalize_plan


class EmailConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class EmailSettings:
    api_key: str
    from_email: str
    public_url: str


def load_email_settings(*, require_api_key: bool = True) -> EmailSettings:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if require_api_key and not api_key:
        raise EmailConfigurationError("RESEND_API_KEY is required")
    return EmailSettings(
        api_key=api_key,
        from_email=os.getenv("AGARTHA_EMAIL_FROM", "Agartha <onboarding@resend.dev>").strip(),
        public_url=os.getenv("AGARTHA_PUBLIC_URL", "http://localhost:5173").rstrip("/"),
    )


async def send_email(
    *,
    to: str | list[str],
    subject: str,
    html: str,
    text: str | None = None,
    tags: list[dict[str, str]] | None = None,
    settings: EmailSettings | None = None,
) -> dict[str, Any]:
    settings = settings or load_email_settings()
    resend.api_key = settings.api_key
    recipients = [to] if isinstance(to, str) else to
    params: dict[str, Any] = {
        "from": settings.from_email,
        "to": recipients,
        "subject": subject,
        "html": html,
    }
    if text:
        params["text"] = text
    if tags:
        params["tags"] = tags
    return await resend.Emails.send_async(params)


async def send_welcome_email(
    *,
    to: str,
    dealer_name: str,
    settings: EmailSettings | None = None,
) -> dict[str, Any]:
    settings = settings or load_email_settings()
    dashboard_url = f"{settings.public_url}/"
    return await send_email(
        to=to,
        subject="Bienvenido a Agartha",
        html=(
            f"<p>Hola {dealer_name},</p>"
            "<p>Tu cuenta de Agartha ya esta lista para analizar oportunidades de alto ROI.</p>"
            f"<p><a href=\"{dashboard_url}\">Entrar al dashboard</a></p>"
        ),
        text=f"Hola {dealer_name}, tu cuenta de Agartha ya esta lista: {dashboard_url}",
        tags=[{"name": "event", "value": "welcome"}],
        settings=settings,
    )


async def send_payment_failed_email(
    *,
    to: str,
    dealer_name: str,
    settings: EmailSettings | None = None,
) -> dict[str, Any]:
    settings = settings or load_email_settings()
    billing_url = f"{settings.public_url}/billing"
    return await send_email(
        to=to,
        subject="Accion requerida: pago fallido en Agartha",
        html=(
            f"<p>Hola {dealer_name},</p>"
            "<p>No hemos podido procesar el ultimo pago de tu suscripcion.</p>"
            f"<p><a href=\"{billing_url}\">Actualizar metodo de pago</a></p>"
        ),
        text=f"Hola {dealer_name}, actualiza tu metodo de pago: {billing_url}",
        tags=[{"name": "event", "value": "payment_failed"}],
        settings=settings,
    )


async def send_plan_upgrade_email(
    *,
    to: str,
    dealer_name: str,
    plan: PlanName | str,
    settings: EmailSettings | None = None,
) -> dict[str, Any]:
    settings = settings or load_email_settings()
    plan_name = normalize_plan(plan)
    return await send_email(
        to=to,
        subject=f"Plan {plan_name.value} activado en Agartha",
        html=(
            f"<p>Hola {dealer_name},</p>"
            f"<p>Tu plan <strong>{plan_name.value}</strong> ya esta activo.</p>"
        ),
        text=f"Hola {dealer_name}, tu plan {plan_name.value} ya esta activo.",
        tags=[{"name": "event", "value": "plan_upgrade"}],
        settings=settings,
    )
