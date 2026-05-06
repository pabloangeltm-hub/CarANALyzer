"""
Session cloner — launches a visible Chrome window on Milanuncios so a human
can solve captchas, accept cookie banners, and browse naturally.

After 45 seconds the full browser state (cookies + LocalStorage + IndexedDB)
is persisted to .tmp/auth_state.json, which scrape_cars.py injects on every
fresh context to bypass Datadome without re-solving captchas each run.

Usage:
    python tools/generate_session.py
"""

import asyncio
import os
import time

from playwright.async_api import async_playwright

_UA      = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
_WAIT    = 45
_TARGET  = "https://www.milanuncios.com"
_SESSIONS_DIR = ".tmp/sessions"

_LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--lang=es-ES,es",
]


async def main() -> None:
    os.makedirs(_SESSIONS_DIR, exist_ok=True)
    out = os.path.join(_SESSIONS_DIR, f"session_{int(time.time())}.json")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, args=_LAUNCH_ARGS)
        context = await browser.new_context(
            user_agent=_UA,
            viewport={"width": 1366, "height": 768},
            locale="es-ES",
            timezone_id="Europe/Madrid",
            extra_http_headers={"Accept-Language": "es-ES,es;q=0.9"},
        )
        page = await context.new_page()
        await page.goto(_TARGET, wait_until="domcontentloaded", timeout=30_000)

        print(f"[generate_session] Browser open on {_TARGET}")
        print(f"[generate_session] → accept cookie banner, solve any captcha, browse a few pages")
        print(f"[generate_session] → saving session automatically in {_WAIT}s …")

        for remaining in range(_WAIT, 0, -5):
            await asyncio.sleep(5)
            print(f"[generate_session] {remaining - 5}s remaining …")

        await context.storage_state(path=out)
        print(f"[OK] Sesión guardada en {out}")
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
