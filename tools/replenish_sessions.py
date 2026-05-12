"""
Auto-replenish the Milanuncios Playwright session pool.

Creates new .tmp/sessions/session_*.json files when the active pool drops
below a configured minimum. If Milanuncios serves a DataDome challenge, the
script asks 2captcha for a DataDome cookie, injects it in the same browser
context, validates the page, then persists the full Playwright storage state.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from playwright.async_api import Page, async_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ROOT = Path(__file__).resolve().parents[1]
SESSIONS_DIR = ROOT / ".tmp" / "sessions"
BURNT_DIR = SESSIONS_DIR / "burnt"
DEFAULT_TARGET_URL = "https://www.milanuncios.com/coches-de-segunda-mano/?orden=date"
DEFAULT_MIN_SESSIONS = 5
DEFAULT_TARGET_SESSIONS = 10
WINDOWS_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
VIEWPORT = {"width": 1366, "height": 768}
LAUNCH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-infobars",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--lang=es-ES,es",
]
LISTING_SELECTORS = [
    "article[class*='ma-AdCard']",
    "a[class*='ma-AdCardV2-link']",
    "a[href*='/coches-de-segunda-mano/']",
]
COOKIE_SELECTORS = [
    "#didomi-notice-agree-button",
    "button:has-text('Aceptar y cerrar')",
    "button:has-text('Aceptar')",
]
CAPTCHA_URL_RE = re.compile(r"https://[^\"'<> ]*captcha-delivery\.com/captcha/[^\"'<> ]+")


@dataclass(frozen=True)
class ProxyConfig:
    scheme: str
    host: str
    port: int
    username: str | None = None
    password: str | None = None

    @property
    def server(self) -> str:
        return f"{self.scheme}://{self.host}:{self.port}"

    @property
    def twocaptcha_type(self) -> str:
        return "HTTPS" if self.scheme == "https" else self.scheme.upper()

    @property
    def twocaptcha_uri(self) -> str:
        auth = ""
        if self.username:
            auth = self.username
            if self.password:
                auth += f":{self.password}"
            auth += "@"
        return f"{auth}{self.host}:{self.port}"

    def as_playwright(self) -> dict[str, str]:
        payload = {"server": self.server}
        if self.username:
            payload["username"] = self.username
        if self.password:
            payload["password"] = self.password
        return payload

    def as_twocaptcha(self) -> dict[str, str]:
        return {"type": self.twocaptcha_type, "uri": self.twocaptcha_uri}


def active_sessions() -> list[Path]:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(path for path in SESSIONS_DIR.glob("*.json") if path.is_file())


def parse_proxy(raw: str | None) -> ProxyConfig | None:
    if not raw:
        return None
    parsed = urlparse(raw.strip())
    if parsed.scheme not in {"http", "https", "socks4", "socks5"}:
        raise ValueError(f"Unsupported proxy scheme: {parsed.scheme!r}")
    if not parsed.hostname or not parsed.port:
        raise ValueError("Proxy must include host and port")
    return ProxyConfig(
        scheme=parsed.scheme,
        host=parsed.hostname,
        port=parsed.port,
        username=parsed.username,
        password=parsed.password,
    )


async def dismiss_cookie_banner(page: Page) -> None:
    for selector in COOKIE_SELECTORS:
        try:
            await page.click(selector, timeout=2_000)
            print(f"[replenish] cookie banner dismissed ({selector})")
            return
        except Exception:
            continue


async def human_scroll(page: Page) -> None:
    scroll_pos = 0
    for _ in range(12):
        try:
            page_height = await page.evaluate("document.body.scrollHeight")
            scroll_pos = min(scroll_pos + 420, page_height)
            await page.evaluate(f"window.scrollTo(0, {scroll_pos});")
            await asyncio.sleep(0.25)
            if scroll_pos >= page_height:
                break
        except Exception:
            break


async def extract_captcha_url(page: Page) -> str | None:
    for selector in (
        "iframe[src*='captcha-delivery.com']",
        "iframe[src*='datadome']",
        "iframe[src*='captcha']",
    ):
        try:
            element = await page.query_selector(selector)
            if element:
                src = await element.get_attribute("src")
                if src:
                    return src
        except Exception:
            continue

    try:
        html = await page.content()
    except Exception:
        return None
    match = CAPTCHA_URL_RE.search(html)
    return match.group(0) if match else None


async def page_is_usable(page: Page) -> bool:
    title = (await page.title()).lower()
    if "pardon our interruption" in title:
        return False

    html = (await page.content()).lower()
    if "captcha-delivery.com" in html or ("datadome" in html and "ma-adcard" not in html):
        return False

    for selector in LISTING_SELECTORS:
        try:
            if await page.query_selector(selector):
                return True
        except Exception:
            continue
    return False


def parse_cookie_header(cookie_header: str, page_url: str) -> dict[str, Any]:
    first_part = cookie_header.split(";", 1)[0]
    if "=" not in first_part:
        raise ValueError(f"Unsupported 2captcha cookie payload: {cookie_header!r}")
    name, value = first_part.split("=", 1)
    host = urlparse(page_url).hostname or "www.milanuncios.com"
    domain = f".{host.removeprefix('www.')}"
    return {
        "name": name.strip(),
        "value": value.strip(),
        "domain": domain,
        "path": "/",
        "secure": True,
        "httpOnly": False,
        "sameSite": "Lax",
    }


def datadome_result_cookie(result: Any) -> str:
    if isinstance(result, str):
        return result
    if not isinstance(result, dict):
        raise ValueError(f"Unsupported 2captcha result type: {type(result).__name__}")

    for key in ("cookie", "cookies", "code"):
        value = result.get(key)
        if isinstance(value, str) and "datadome=" in value:
            return value

    solution = result.get("solution")
    if isinstance(solution, dict):
        value = solution.get("cookie")
        if isinstance(value, str) and "datadome=" in value:
            return value

    raise ValueError(f"2captcha response did not include a DataDome cookie: {result!r}")


def solve_datadome_cookie(
    *,
    api_key: str,
    captcha_url: str,
    page_url: str,
    proxy: ProxyConfig,
) -> str:
    try:
        from twocaptcha import TwoCaptcha
    except ImportError as exc:
        raise RuntimeError(
            "2captcha-python is not installed. Run `pip install -r requirements.txt`."
        ) from exc

    solver = TwoCaptcha(api_key)
    print("[replenish] sending DataDome challenge to 2captcha")
    result = solver.datadome(
        captcha_url=captcha_url,
        pageurl=page_url,
        userAgent=WINDOWS_UA,
        proxy=proxy.as_twocaptcha(),
    )
    return datadome_result_cookie(result)


async def create_session(
    *,
    target_url: str,
    api_key: str,
    proxy: ProxyConfig | None,
    timeout_ms: int,
    dry_run: bool,
) -> Path | None:
    if dry_run:
        print("[replenish] dry-run: would open browser and create one session")
        return None

    async with async_playwright() as pw:
        launch_kwargs: dict[str, Any] = {"headless": True, "args": LAUNCH_ARGS}
        if proxy:
            launch_kwargs["proxy"] = proxy.as_playwright()

        browser = await pw.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            user_agent=WINDOWS_UA,
            viewport=VIEWPORT,
            locale="es-ES",
            timezone_id="Europe/Madrid",
            extra_http_headers={"Accept-Language": "es-ES,es;q=0.9"},
        )
        try:
            page = await context.new_page()
            await page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
            await dismiss_cookie_banner(page)
            await human_scroll(page)

            if not await page_is_usable(page):
                captcha_url = await extract_captcha_url(page)
                if not captcha_url:
                    title = await page.title()
                    raise RuntimeError(f"Page is blocked but no DataDome iframe was found: {title!r}")
                if not api_key:
                    raise RuntimeError("API_KEY_SOLVER_CAPTCHA is required to solve DataDome")
                if not proxy:
                    raise RuntimeError("PROXY_URL is required by 2captcha for DataDome solving")

                cookie_header = await asyncio.to_thread(
                    solve_datadome_cookie,
                    api_key=api_key,
                    captcha_url=captcha_url,
                    page_url=target_url,
                    proxy=proxy,
                )
                await context.add_cookies([parse_cookie_header(cookie_header, target_url)])
                await page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
                await dismiss_cookie_banner(page)
                await human_scroll(page)

            if not await page_is_usable(page):
                title = await page.title()
                raise RuntimeError(f"Generated session failed validation: {title!r}")

            out = SESSIONS_DIR / f"session_{int(time.time())}.json"
            while out.exists():
                out = SESSIONS_DIR / f"session_{int(time.time() * 1000)}.json"
            await context.storage_state(path=str(out))
            print(f"[OK] session saved: {out.relative_to(ROOT)}")
            return out
        finally:
            await context.close()
            await browser.close()


async def replenish(args: argparse.Namespace) -> int:
    load_dotenv(ROOT / ".env")
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    BURNT_DIR.mkdir(parents=True, exist_ok=True)

    current = active_sessions()
    target = max(args.target, args.min)
    print(f"[replenish] active sessions: {len(current)} | min={args.min} target={target}")
    if len(current) >= args.min:
        print("[replenish] pool is healthy; nothing to do")
        return 0

    missing = target - len(current)
    if args.max_new is not None:
        missing = min(missing, args.max_new)
    print(f"[replenish] creating up to {missing} session(s)")

    proxy = parse_proxy(os.getenv("PROXY_URL"))
    api_key = os.getenv("API_KEY_SOLVER_CAPTCHA", "").strip()
    created = 0

    for attempt in range(1, missing + 1):
        print(f"[replenish] attempt {attempt}/{missing}")
        try:
            out = await create_session(
                target_url=args.url,
                api_key=api_key,
                proxy=proxy,
                timeout_ms=args.timeout_ms,
                dry_run=args.dry_run,
            )
        except Exception as exc:
            print(f"[ERROR] session creation failed: {exc}")
            if args.keep_going:
                continue
            return 1
        if out is not None:
            created += 1
        if len(active_sessions()) >= target:
            break

    if args.dry_run:
        print("[replenish] dry-run complete")
    else:
        print(f"[replenish] created={created} active={len(active_sessions())}")
    return 0 if args.dry_run or len(active_sessions()) >= args.min else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auto-replenish .tmp/sessions with validated Playwright states")
    parser.add_argument("--min", type=int, default=DEFAULT_MIN_SESSIONS, help="Minimum healthy pool size")
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET_SESSIONS, help="Fill pool up to this size")
    parser.add_argument("--max-new", type=int, default=None, help="Cap sessions created in this run")
    parser.add_argument("--url", default=DEFAULT_TARGET_URL, help="Milanuncios URL used for validation")
    parser.add_argument("--timeout-ms", type=int, default=45_000, help="Navigation timeout")
    parser.add_argument("--dry-run", action="store_true", help="Report actions without browser/API calls")
    parser.add_argument("--keep-going", action="store_true", help="Continue after a failed session attempt")
    return parser


if __name__ == "__main__":
    raise SystemExit(asyncio.run(replenish(build_parser().parse_args())))
