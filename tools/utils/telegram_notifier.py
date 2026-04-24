"""
Telegram alert notifier for the car arbitrage pipeline.

Usage:
    from tools.utils.telegram_notifier import TelegramNotifier

    notifier = TelegramNotifier()
    notifier.send_opportunity(
        brand="Toyota Supra MK4",
        list_price=18_500,
        market_price=27_000,
        roi=46.0,
        url="https://coches.net/anuncio/...",
        location="Madrid",
        year=1995,
        mileage=120_000,
    )

    # Or send a free-form alert
    notifier.send_text("Pipeline completed — 3 new opportunities found.")

Environment variables required in .env:
    TELEGRAM_BOT_TOKEN   Token from @BotFather
    TELEGRAM_CHAT_ID     Your personal chat ID (get it from @userinfobot)
"""

import os
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"
_SEND_TIMEOUT = 10  # seconds — fast fail so Sheets write is never blocked


class TelegramNotifier:
    """Sends HTML-formatted car opportunity alerts to a Telegram chat.

    All public methods are fire-and-forget: they catch every exception and
    return False on failure so the calling pipeline can continue without crashing.
    """

    def __init__(self):
        self._token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self._chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self._ready = bool(self._token and self._chat_id)

        if not self._ready:
            print(
                "[WARN] TelegramNotifier: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID "
                "missing from .env — alerts will be skipped silently."
            )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def send_opportunity(
        self,
        brand: str,
        list_price: float,
        market_price: float,
        roi: float,
        url: str,
        location: str = "—",
        year: Optional[int] = None,
        mileage: Optional[int] = None,
        extra: Optional[str] = None,
    ) -> bool:
        """Send a structured car opportunity alert.

        Args:
            brand:        Full car name (e.g. "Toyota Supra MK4").
            list_price:   Asking price on the listing site (EUR).
            market_price: Estimated resale / market value (EUR).
            roi:          Return on investment in percent (e.g. 46.0 → "46.0 %").
            url:          Direct link to the listing.
            location:     City or region (optional).
            year:         Manufacturing year (optional).
            mileage:      Odometer in km (optional).
            extra:        Any additional free-form note (optional).

        Returns:
            True if Telegram confirmed delivery, False otherwise.
        """
        profit = market_price - list_price
        roi_emoji = self._roi_emoji(roi)

        year_str = str(year) if year else "—"
        mileage_str = f"{mileage:,} km".replace(",", ".") if mileage else "—"

        lines = [
            f"{roi_emoji} <b>{self._esc(brand)}</b>",
            "",
            f"💰 Precio lista:    <b>{list_price:,.0f} €</b>".replace(",", "."),
            f"📈 Valor mercado:  <b>{market_price:,.0f} €</b>".replace(",", "."),
            f"💵 Beneficio:       <b>+{profit:,.0f} €</b>".replace(",", "."),
            f"📊 ROI:             <b>{roi:.1f} %</b>",
            "",
            f"📅 Año:      {year_str}",
            f"🛣️ Km:       {mileage_str}",
            f"📍 Lugar:   {self._esc(location)}",
        ]

        if extra:
            lines += ["", f"📝 {self._esc(extra)}"]

        lines += ["", f'🔗 <a href="{url}">Ver anuncio</a>']

        return self.send_text("\n".join(lines))

    def send_text(self, message: str, disable_preview: bool = True) -> bool:
        """Send any HTML-formatted text message.

        Args:
            message:         HTML string (Telegram subset: bold, italic, links…).
            disable_preview: Suppress link previews (default True).

        Returns:
            True if delivered, False on any error (network, auth, rate limit).
        """
        if not self._ready:
            return False

        payload = {
            "chat_id": self._chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_preview,
        }

        try:
            resp = requests.post(
                _TELEGRAM_API.format(token=self._token, method="sendMessage"),
                json=payload,
                timeout=_SEND_TIMEOUT,
            )
            data = resp.json()

            if not data.get("ok"):
                print(
                    f"[WARN] Telegram rejected message: {data.get('description', data)}"
                )
                return False

            return True

        except requests.exceptions.Timeout:
            print("[WARN] Telegram API timed out — alert skipped, pipeline continues.")
            return False
        except requests.exceptions.ConnectionError:
            print("[WARN] No connection to Telegram API — alert skipped.")
            return False
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] Unexpected Telegram error: {exc!r} — alert skipped.")
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _esc(text: str) -> str:
        """Escape the five HTML chars that break Telegram's HTML parse mode."""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    @staticmethod
    def _roi_emoji(roi: float) -> str:
        if roi >= 50:
            return "🚨"
        if roi >= 30:
            return "🔥"
        if roi >= 15:
            return "✅"
        return "📌"
