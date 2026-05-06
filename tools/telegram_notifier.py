"""
Standalone async Telegram notifier for the car arbitrage pipeline.

Sends a single structured alert per car — no class, no env magic.
All config is passed explicitly so this module can run in isolation.

Usage:
    import asyncio
    from tools.telegram_notifier import send_alert

    asyncio.run(send_alert(car_data, chat_id="123", bot_token="abc:XYZ"))

car_data keys (all optional except price / market_price):
    brand, model, year, mileage, price, market_price, roi, url,
    forensic_report  → object with .status and .summary  (or plain dict)

Test standalone:
    python tools/telegram_notifier.py
"""

import asyncio
import html
from typing import Any

import aiohttp

_API = "https://api.telegram.org/bot{token}/sendMessage"
_TIMEOUT = aiohttp.ClientTimeout(total=10)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def send_alert(car_data: dict[str, Any], chat_id: str, bot_token: str) -> bool:
    """Send one car opportunity alert to a Telegram chat.

    Args:
        car_data:   Dict with car fields (see module docstring).
        chat_id:    Telegram chat / channel ID.
        bot_token:  Bot token from @BotFather.

    Returns:
        True if Telegram confirmed delivery, False on any error.
    """
    message = _format(car_data)
    return await _post(message, chat_id=chat_id, bot_token=bot_token)


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------

def _format(car: dict[str, Any]) -> str:
    brand   = car.get("brand", "—")
    model   = car.get("model", "—")
    year    = car.get("year")
    mileage = car.get("mileage")
    price   = car.get("price")
    mkt     = car.get("market_price")
    roi     = car.get("roi")
    url     = car.get("url", "")

    # Forensic verdict — accepts Pydantic object or plain dict
    report  = car.get("forensic_report")
    verdict = _forensic_verdict(report)

    profit_str = ""
    if price is not None and mkt is not None:
        profit = mkt - price
        profit_str = f"💵 Beneficio bruto:   <b>+{profit:,.0f} €</b>\n".replace(",", ".")

    lines = [
        f"{_roi_emoji(roi)} <b>{_e(brand)} {_e(model)}</b>",
        "",
        f"🚗 Año:               {year or '—'}",
        f"🛣️  Kilómetros:        {f'{mileage:,} km'.replace(',', '.') if mileage else '—'}",
        "",
        f"💰 Precio anuncio:    <b>{price:,.0f} €</b>".replace(",", ".") if price is not None else "💰 Precio anuncio:    —",
        f"📈 Valor de mercado:  <b>{mkt:,.0f} €</b>".replace(",", ".") if mkt is not None else "📈 Valor de mercado:  —",
        profit_str.rstrip() if profit_str else "",
        f"📊 ROI bruto:         <b>{roi:.1f} %</b>" if roi is not None else "",
        "",
        verdict,
        "",
        f'🔗 <a href="{url}">Ver anuncio</a>' if url else "🔗 Sin enlace",
    ]

    return "\n".join(line for line in lines if line != "")


def _forensic_verdict(report: Any) -> str:
    if report is None:
        return "🔍 Veredicto forense: sin datos"

    # Accepts Pydantic model or plain dict
    if hasattr(report, "status"):
        status  = report.status
        summary = getattr(report, "summary", "") or ""
    elif isinstance(report, dict):
        status  = report.get("status", "unknown")
        summary = report.get("summary", "")
    else:
        return "🔍 Veredicto forense: formato desconocido"

    icons = {"clean": "✅", "damaged": "⚠️", "dudoso": "❓"}
    icon  = icons.get(status, "❓")

    label = {"clean": "Sin daños visibles", "damaged": "Daños detectados", "dudoso": "Indeterminado"}.get(status, status)
    line  = f"{icon} Veredicto forense: <b>{label}</b>"
    if summary:
        line += f"\n📋 {_e(summary)}"
    return line


def _roi_emoji(roi: float | None) -> str:
    if roi is None:
        return "📌"
    if roi >= 50:
        return "🚨"
    if roi >= 30:
        return "🔥"
    if roi >= 15:
        return "✅"
    return "📌"


def _e(text: Any) -> str:
    return html.escape(str(text))


# ---------------------------------------------------------------------------
# HTTP transport
# ---------------------------------------------------------------------------

async def _post(message: str, *, chat_id: str, bot_token: str) -> bool:
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    url = _API.format(token=bot_token)

    try:
        async with aiohttp.ClientSession(timeout=_TIMEOUT) as session:
            async with session.post(url, json=payload) as resp:
                data = await resp.json()
                if not data.get("ok"):
                    print(f"[WARN] Telegram rechazó el mensaje: {data.get('description', data)}")
                    return False
                return True

    except asyncio.TimeoutError:
        print("[WARN] Telegram API timeout — alerta omitida.")
        return False
    except aiohttp.ClientConnectionError:
        print("[WARN] Sin conexión a Telegram API — alerta omitida.")
        return False
    except Exception as exc:
        print(f"[WARN] Error inesperado Telegram: {exc!r}")
        return False


# ---------------------------------------------------------------------------
# Convenience class — loads credentials from .env automatically
# ---------------------------------------------------------------------------

class TelegramNotifier:
    """Thin wrapper around send_alert / _post that reads credentials from .env."""

    def __init__(self) -> None:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id   = os.getenv("TELEGRAM_CHAT_ID", "")

    async def send_message(self, text: str) -> bool:
        """Send a plain-text HTML message to the configured chat."""
        if not self.bot_token or not self.chat_id:
            print("[WARN] TelegramNotifier: missing TOKEN or CHAT_ID — alerta omitida.")
            return False
        return await _post(text, chat_id=self.chat_id, bot_token=self.bot_token)


# ---------------------------------------------------------------------------
# Standalone test — python tools/telegram_notifier.py
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    _MOCK_CAR = {
        "brand":        "BMW",
        "model":        "Serie 3 320d",
        "year":         2018,
        "mileage":      87_500,
        "price":        14_900,
        "market_price": 19_800,
        "roi":          32.9,
        "url":          "https://www.milanuncios.com/coches-de-segunda-mano/bmw-serie-3-320d-mock.htm",
        "forensic_report": {
            "status":  "damaged",
            "summary": "Golpe en aleta delantera derecha y arañazo en puerta trasera.",
        },
    }

    TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    if not TOKEN or not CHAT_ID:
        print("[ERROR] Añade TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en .env antes de testar.")
    else:
        print("[TEST] Enviando alerta de prueba…")
        ok = asyncio.run(send_alert(_MOCK_CAR, chat_id=CHAT_ID, bot_token=TOKEN))
        print("[TEST] Enviado correctamente." if ok else "[TEST] Falló el envío — revisa los logs.")
