"""
Car listing scraper — Playwright async + stealth.
Bypasses basic bot detection (Cloudflare, Datadome) on Spanish car portals.

Architecture:
    CarScraper (abstract base)
    └── MilanunciosScraper  ← V1 implementation (proof of concept)

Output format per listing (compatible with valuation_engine.py):
    {
        "portal":      "milanuncios",
        "brand":       "BMW",
        "model":       "320d",
        "year":        2019,
        "mileage":     145000,   # int | None
        "price":       14500.0,  # float | None
        "title":       "BMW 320d 2019 Diesel",
        "description": "Motor averiado, turbo roto…",  # str | None
        "url":         "https://www.milanuncios.com/..."
    }

Usage:
    python tools/scrape_cars.py
    python tools/scrape_cars.py --portal milanuncios --pages 5
    python tools/scrape_cars.py --url "https://www.milanuncios.com/coches-de-segunda-mano/?marca=BMW" --pages 3

As a module:
    from tools.scrape_cars import run
    import asyncio
    path = asyncio.run(run("milanuncios", url="https://...", max_pages=3))
"""

import asyncio
import argparse
import glob
import json
import os
import random
import re
import shutil
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

try:
    from tools.telegram_notifier import TelegramNotifier
except ImportError:
    from telegram_notifier import TelegramNotifier

import uuid
import httpx
from playwright.async_api import async_playwright, Browser, Page
from playwright_stealth import Stealth


# ---------------------------------------------------------------------------
# Anti-detection configuration
# ---------------------------------------------------------------------------

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# Windows/Chrome UA used when auth state is loaded (must match the session generator)
_WINDOWS_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

# Full-state session file written by tools/generate_session.py
_AUTH_STATE_PATH = ".tmp/auth_state.json"

# Directory with rotating session pool (*.json files)
_SESSIONS_DIR = ".tmp/sessions"

_CHROME_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--disable-dev-shm-usage",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-infobars",
    "--disable-gpu",
    "--window-position=0,0",
    "--ignore-certificate-errors",
    "--ignore-certificate-errors-spki-list",
    "--lang=es-ES,es",
]

_VIEWPORT = {"width": 1366, "height": 768}

# Human-like delay ranges (seconds)
_DELAY_BETWEEN_PAGES = (6.0, 10.0)
_DELAY_AFTER_LOAD   = (1.0, 2.5)

# Listing minimum price — anything below is treated as an anuncio trampa
MIN_VALID_PRICE = 500.0


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class CarScraper(ABC):
    """
    Base class for all car portal scrapers.

    Subclasses must implement:
        _extract_listings(page) → list[dict]
        _paginate_url(base_url, page_num) → str
        PORTAL_NAME: str

    Subclasses may override:
        _get_next_page_url(page) → Optional[str]
            Return the next-page URL extracted from the live DOM.
            Returning None falls back to _paginate_url(base_url, page_num + 1).
    """

    PORTAL_NAME: str = "base"

    async def scrape(
        self,
        url: str,
        max_pages: int = 3,
        seen_ids: Optional[set[str]] = None,
        start_page: int = 1,
        disable_brake: bool = False,
    ) -> list[dict]:
        """
        Launch a stealth browser, iterate through pages, and collect listings.
        Returns a flat list of raw car dicts.

        Hit & Run + Auto-heal architecture: each page gets a fresh context.
        On Datadome block (title match or 0 cards), the current session is
        burned (.json → .json.banned) and the next session in the pool is used
        to retry the exact same page. Stops only when no sessions remain.

        Args:
            start_page:    First page number to scrape (for historical mode).
            disable_brake: When True, ignores seen_ids and never stops early —
                           enables full historical dumps without deduplication gaps.
        """
        results: list[dict] = []
        next_url: Optional[str] = self._paginate_url(url, start_page)

        # ── Session pool ────────────────────────────────────────────────────
        pool: list[str] = sorted(glob.glob(f"{_SESSIONS_DIR}/*.json"))
        random.shuffle(pool)
        if not pool and os.path.exists(_AUTH_STATE_PATH):
            pool = [_AUTH_STATE_PATH]
        if pool:
            print(f"[{self.PORTAL_NAME}] session pool: {len(pool)} file(s)")

        def _pick() -> Optional[str]:
            return pool[0] if pool else None

        async def _burn(path: str) -> None:
            if not path or path not in pool:
                return
            pool.remove(path)
            burnt_dir = ".tmp/sessions/burnt"
            os.makedirs(burnt_dir, exist_ok=True)
            dest = os.path.join(burnt_dir, os.path.basename(path))
            try:
                shutil.move(path, dest)
                print(f"[{self.PORTAL_NAME}] session burned → {dest} | {len(pool)} remaining")
            except OSError as exc:
                print(f"[{self.PORTAL_NAME}] could not move session ({exc})")
            remaining = len(glob.glob(f"{_SESSIONS_DIR}/*.json"))
            if remaining < 10:
                try:
                    notifier = TelegramNotifier()
                    await notifier.send_message(
                        f"⚠️ Alerta Agartha: Quedan solo {remaining} sesiones disponibles."
                    )
                except Exception as tg_exc:
                    print(f"[{self.PORTAL_NAME}] Telegram alert failed: {tg_exc}")

        # ── Paging loop ─────────────────────────────────────────────────────
        async with async_playwright() as pw:
            browser = await self._launch_browser(pw)
            try:
                page_num = start_page
                consecutive_burns = 0
                cooldowns_triggered = 0
                while page_num < start_page + max_pages:
                    os.makedirs(".tmp", exist_ok=True)
                    with open(".tmp/last_page.txt", "w") as _lp:
                        _lp.write(str(page_num))

                    if next_url is None:
                        print(f"[{self.PORTAL_NAME}] no next page found — stopping.")
                        break

                    auth_state = _pick()
                    ctx_kwargs: dict = dict(
                        viewport=_VIEWPORT,
                        user_agent=_WINDOWS_UA if auth_state else random.choice(_USER_AGENTS),
                        locale="es-ES",
                        timezone_id="Europe/Madrid",
                        extra_http_headers={"Accept-Language": "es-ES,es;q=0.9"},
                    )
                    if auth_state:
                        ctx_kwargs["storage_state"] = auth_state

                    context = await browser.new_context(**ctx_kwargs)
                    page    = await context.new_page()
                    await Stealth().apply_stealth_async(page)

                    current_url = next_url
                    rel_page    = page_num - start_page + 1
                    blocked     = False
                    page_listings: list[dict] = []

                    try:
                        print(f"[{self.PORTAL_NAME}] page {rel_page}/{max_pages} → {current_url}")

                        ok = await self._navigate(page, current_url)
                        if not ok:
                            print(f"[{self.PORTAL_NAME}] navigation failed — stopping early")
                            break

                        page_title = await page.title()
                        if "Pardon Our Interruption" in page_title:
                            print(f"[{self.PORTAL_NAME}] BLOCKED (title: {page_title!r})")
                            blocked = True
                        else:
                            page_listings = await self._extract_listings(page)
                            if not page_listings:
                                print(f"[{self.PORTAL_NAME}] 0 cards — treating as block")
                                blocked = True

                        if not blocked:
                            dom_next = await self._get_next_page_url(page)
                            next_url = dom_next if dom_next else self._paginate_url(url, page_num + 1)
                    finally:
                        await context.close()

                    # ── Block recovery ──────────────────────────────────────
                    if blocked:
                        await _burn(auth_state)
                        consecutive_burns += 1
                        if consecutive_burns >= 3:
                            cooldowns_triggered += 1
                            if cooldowns_triggered >= 2:
                                print(
                                    "[CRITICAL] IP bloqueada permanentemente. "
                                    "Deteniendo el bot para salvar las sesiones restantes."
                                )
                                sys.exit(1)
                            print(
                                "[WARNING] IP HOT: 3 sesiones quemadas. "
                                "Iniciando enfriamiento de 15 minutos..."
                            )
                            await asyncio.sleep(900)
                            consecutive_burns = 0
                        print(f"[{self.PORTAL_NAME}] retrying page {rel_page} with next session…")
                        next_url = current_url  # retry same page
                        continue               # page_num stays the same

                    consecutive_burns = 0
                    cooldowns_triggered = 0

                    # ── Success: process results ────────────────────────────
                    if disable_brake:
                        new = page_listings
                        print(
                            f"[{self.PORTAL_NAME}] page {rel_page}: "
                            f"{len(page_listings)} extracted (brake disabled)"
                        )
                    else:
                        new = [
                            l for l in page_listings
                            if l.get("ad_id") not in (seen_ids or set())
                        ]
                        hit_overlap = len(new) < len(page_listings)
                        print(
                            f"[{self.PORTAL_NAME}] page {rel_page}: "
                            f"{len(page_listings)} extracted, {len(new)} new"
                        )
                        if hit_overlap:
                            print(
                                f"[{self.PORTAL_NAME}] known ID detected — "
                                "incremental brake engaged"
                            )
                            results.extend(new)
                            page_num += 1
                            break

                    results.extend(new)
                    page_num += 1

                    if rel_page < max_pages:
                        delay = random.uniform(*_DELAY_BETWEEN_PAGES)
                        print(f"[{self.PORTAL_NAME}] sleeping {delay:.1f}s before next page…")
                        await asyncio.sleep(delay)
            finally:
                await browser.close()

        return results

    # ------------------------------------------------------------------
    # Internal helpers (shared across all portal subclasses)
    # ------------------------------------------------------------------

    async def _launch_browser(self, pw) -> Browser:
        return await pw.chromium.launch(headless=True, args=_CHROME_ARGS)

    async def _navigate(self, page: Page, url: str) -> bool:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            await asyncio.sleep(random.uniform(*_DELAY_AFTER_LOAD))
            return True
        except Exception as exc:
            print(f"[{self.PORTAL_NAME}] navigation error: {exc}")
            return False

    async def _get_next_page_url(self, page: Page) -> Optional[str]:
        """
        Override to extract the next-page URL directly from the live DOM.
        Returning None causes scrape() to fall back to _paginate_url().
        """
        return None

    # ------------------------------------------------------------------
    # Shared text parsers (reusable by all subclasses)
    # ------------------------------------------------------------------

    @staticmethod
    def parse_price(raw: str) -> Optional[float]:
        """
        '14.500 €'            →  14500.0
        '16.500 € / 189 €/mes' →  16500.0  (lowest numeric price wins)
        None on failure.
        """
        if not raw:
            return None
        # Extract all candidate prices: sequences of digits with . or , separators
        candidates = re.findall(r"\d[\d.,]*\d|\d", raw)
        values: list[float] = []
        for c in candidates:
            try:
                # Normalise European thousands separators: "14.500" → 14500
                normalised = c.replace(".", "").replace(",", "")
                values.append(float(normalised))
            except ValueError:
                continue
        if not values:
            return None
        # Return the smallest value — rebajado / financiado price is always lower
        return min(values)

    @staticmethod
    def parse_mileage(raw: str) -> Optional[int]:
        """'145.000 km'  →  145000   |  None on failure"""
        if not raw:
            return None
        digits = re.sub(r"[^\d]", "", raw)
        return int(digits) if digits else None

    @staticmethod
    def parse_year(raw: str) -> Optional[int]:
        """Extract the first 4-digit year (1900–2099) from any string."""
        match = re.search(r"\b(19|20)\d{2}\b", raw or "")
        return int(match.group()) if match else None

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    async def _extract_listings(self, page: Page) -> list[dict]:
        """Parse all listing cards from the current page DOM."""
        ...

    @abstractmethod
    def _paginate_url(self, base_url: str, page_num: int) -> str:
        """Return the URL for page N of a given base search URL."""
        ...


# ---------------------------------------------------------------------------
# Milanuncios implementation (V1 — proof of concept)
# ---------------------------------------------------------------------------

class MilanunciosScraper(CarScraper):
    """
    Scraper for Milanuncios car listings.

    Default search URL (sorted by date — required for seen_ids brake to work):
        https://www.milanuncios.com/coches-de-segunda-mano/?orden=date

    Pagination:
        Uses the "Siguiente" DOM button href (contains nextToken) rather than
        manually constructing pagina=N URLs, which can drift from the real token.

    Selector notes:
        Milanuncios uses React with server-side rendering. Class names are
        stable semantic BEM names (ma-AdCard*, ma-AdPrice, ma-AdTag) as of
        April 2026. The broad `article[class*='ma-AdCard']` pattern captures
        both organic (ma-AdCardV2) and highlighted/professional (ma-AdCardV2--highlighted)
        variants without explicit enumeration.
        Mark any selector with # VERIFY if it stops matching after a portal update.
    """

    PORTAL_NAME = "milanuncios"
    # ?orden=date is mandatory — relevance order breaks the seen_ids brake
    BASE_URL    = "https://www.milanuncios.com/coches-de-segunda-mano/?orden=date"

    # VERIFY these selectors after any Milanuncios frontend update
    # Broad match captures organic + Destacado + Profesional card variants
    _SEL_CARD        = "article[class*='ma-AdCard']"
    _SEL_TITLE       = "[class*='ma-AdCardListingV2-TitleRow'], [class*='ma-AdCardV2-title'], [class*='ma-AdCard-title']"
    _SEL_LINK        = "a[class*='ma-AdCardV2-link'], a[class*='ma-AdCard-link']"
    _SEL_PRICE       = "[class*='ma-AdCardV2-price'], [class*='ma-AdCard-price'], [class*='ma-AdPrice']"
    _SEL_TAG_LABELS  = "[class*='ma-AdCardV2-tag'], [class*='ma-AdCard-tag'], [class*='ma-AdTag-label']"
    _SEL_DESCRIPTION = ".ma-AdDetail-description"

    # Next-page button — Milanuncios pagination bar
    _SEL_NEXT_BTN = [
        "a[class*='ma-Pagination-item--next']",
        "a[aria-label='Siguiente']",
        "a[title='Siguiente']",
        "[class*='pagination'] a[rel='next']",
        "a[rel='next']",
    ]

    # GDPR cookie popup selectors — Didomi provider used by Milanuncios
    _COOKIE_SELECTORS = [
        "#didomi-notice-agree-button",
        "button:has-text('Aceptar y cerrar')",
        "button:has-text('Aceptar')",
    ]

    async def _handle_cookies(self, page: Page) -> None:
        for sel in self._COOKIE_SELECTORS:
            try:
                await page.click(sel, timeout=4_000)
                print(f"[{self.PORTAL_NAME}] cookie banner dismissed ({sel})")
                return
            except Exception:
                continue

    def _paginate_url(self, base_url: str, page_num: int) -> str:
        if page_num <= 1:
            return base_url
        sep = "&" if "?" in base_url else "?"
        return f"{base_url}{sep}pagina={page_num}"

    async def _get_next_page_url(self, page: Page) -> Optional[str]:
        """Extract the href of the 'Siguiente' button from the live DOM."""
        for sel in self._SEL_NEXT_BTN:
            try:
                el = await page.query_selector(sel)
                if el:
                    href = await el.get_attribute("href")
                    if href:
                        if href.startswith("/"):
                            return f"https://www.milanuncios.com{href}"
                        return href
            except Exception:
                continue
        return None

    async def _human_scroll(self, page: Page) -> None:
        """
        Scroll gradually to the bottom so the browser fires lazy-load events
        for all listing cards in the grid (~30-40 per page).
        Recalculates page height after each step to handle dynamic content expansion.
        """
        scroll_pos: int = 0
        max_steps: int = 80  # safety cap against infinite growth

        for _ in range(max_steps):
            page_height: int = await page.evaluate("document.body.scrollHeight")
            if scroll_pos >= page_height:
                break
            step = random.randint(260, 420)
            scroll_pos = min(scroll_pos + step, page_height)
            await page.evaluate(f"window.scrollTo(0, {scroll_pos});")
            await asyncio.sleep(random.uniform(0.25, 0.55))

        # Final pause to let the last batch of images / card data settle
        await asyncio.sleep(random.uniform(0.8, 1.4))

    async def _extract_listings(self, page: Page) -> list[dict]:
        await self._handle_cookies(page)

        # Wait for at least one listing card to appear
        try:
            await page.wait_for_selector(self._SEL_CARD, timeout=12_000)
        except Exception:
            page_title = await page.title()
            print(
                f"[{self.PORTAL_NAME}] listing selector not found — "
                "possible bot block, empty search, or DOM change. "
                f"Check selector: {self._SEL_CARD!r}"
            )
            print(f"[{self.PORTAL_NAME}] page <title>: {page_title!r}")
            os.makedirs(".tmp", exist_ok=True)
            screenshot_path = ".tmp/debug_milanuncios.png"
            await page.screenshot(path=screenshot_path)
            print(f"[{self.PORTAL_NAME}] screenshot saved → {screenshot_path}")
            return []

        # Gradual human-like scroll to trigger full lazy loading
        await self._human_scroll(page)

        cards = await page.query_selector_all(self._SEL_CARD)
        print(f"[{self.PORTAL_NAME}] cards in DOM after scroll: {len(cards)}")

        results: list[dict] = []
        seen: set[str] = set()
        for card in cards:
            try:
                item = await self._parse_card(card)
                if item is not None:
                    ad_id = item["ad_id"]
                    if ad_id in seen:
                        continue
                    seen.add(ad_id)
                    results.append(item)
            except Exception as exc:
                print(f"[{self.PORTAL_NAME}] card parse error (skipping): {exc}")
                continue

        return results

    async def _parse_card(self, card) -> Optional[dict]:
        # ── Title ────────────────────────────────────────────────────
        title_el = await card.query_selector(self._SEL_TITLE)
        if title_el is None:
            return None
        title = (await title_el.inner_text()).strip()

        # ── URL ──────────────────────────────────────────────────────
        href = ""
        for link_sel in (self._SEL_LINK, "a[href^='/']", "a[href]", "a"):
            link_el = await card.query_selector(link_sel)
            if link_el:
                href = await link_el.get_attribute("href") or ""
            if href:
                break

        if not href:
            return None

        url = f"https://www.milanuncios.com{href}" if href.startswith("/") else href
        ad_id_match = re.search(r"(\d{6,})", url)
        ad_id = ad_id_match.group(1) if ad_id_match else href.strip("/").replace("/", "-")

        # ── Price ────────────────────────────────────────────────────
        price_el  = await card.query_selector(self._SEL_PRICE)
        price_raw = (await price_el.inner_text()).strip() if price_el else ""
        price     = self.parse_price(price_raw)

        # Discard anuncios trampa immediately
        if price is not None and price < MIN_VALID_PRICE:
            return None

        # ── Detail badges (year, mileage, fuel) ─────────────────────
        tag_els   = await card.query_selector_all(self._SEL_TAG_LABELS)
        tag_texts = [(await el.inner_text()).strip() for el in tag_els]

        year    = None
        mileage = None

        for tag in tag_texts:
            if year is None:
                year = self.parse_year(tag)
            if mileage is None and "km" in tag.lower():
                mileage = self.parse_mileage(tag)

        # Fallback: parse year from title string
        if year is None:
            year = self.parse_year(title)

        # ── Description snippet ──────────────────────────────────────
        desc_el = await card.query_selector(self._SEL_DESCRIPTION)
        description = (await desc_el.inner_text()).strip() if desc_el else None

        # ── Brand / model (best-effort from title) ───────────────────
        brand, model = self._split_brand_model(title)

        return {
            "portal":      self.PORTAL_NAME,
            "ad_id":       ad_id,
            "brand":       brand,
            "model":       model,
            "year":        year,
            "mileage":     mileage,
            "price":       price,
            "title":       title,
            "description": description,
            "url":         url,
        }

    @staticmethod
    def _split_brand_model(title: str) -> tuple[Optional[str], Optional[str]]:
        """
        'BMW 320d 2019 Diesel'         → ('BMW', '320d')
        'BMW - 320d 2019'              → ('BMW', '320d')
        'MERCEDES-BENZ CLASE A 2018'   → ('MERCEDES-BENZ', 'CLASE A')
        'VOLKSWAGEN GOLF GTI 2019'     → ('VOLKSWAGEN', 'GOLF GTI')
        Collects all words after brand up to (but not including) the first year token.
        """
        cleaned = re.sub(r"\s+[-–—]\s+", " ", title.strip())
        parts = [p for p in cleaned.split() if p not in ("-", "–", "—")]
        if not parts:
            return None, None
        brand = parts[0].upper()
        model_parts: list[str] = []
        for word in parts[1:]:
            if re.fullmatch(r"(19|20)\d{2}", word):
                break
            model_parts.append(word)
        model = " ".join(model_parts) if model_parts else None
        return brand, model


# ---------------------------------------------------------------------------
# Wallapop implementation (V2 — REST API, no Playwright)
# ---------------------------------------------------------------------------
#
# Real flow (reverse-engineered from browser XHR, 2026-05):
#   1. GET /api/v3/search/components  →  returns query_params containing search_id
#   2. GET /api/v3/search/section     →  data.section.items + meta.next_page (JWT cursor)
#
# Required headers: x-appversion, x-deviceos, x-deviceid (random UUID per session)
# ---------------------------------------------------------------------------

class WallapopScraper:
    """
    REST API scraper for Wallapop car listings.
    Uses httpx directly — no Playwright, no session pool.
    """

    PORTAL_NAME = "wallapop"

    _COMPONENTS_URL = "https://api.wallapop.com/api/v3/search/components"
    _SECTION_URL    = "https://api.wallapop.com/api/v3/search/section"

    _SEARCH_PARAMS: dict = {
        "source":     "deep_link",
        "order_by":   "newest",
        "latitude":   "40.4168",
        "longitude":  "-3.7038",
        "category_id": "100",
    }
    _MAX_RETRY = 3

    def _build_headers(self) -> dict:
        return {
            "user-agent":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "accept":           "application/json, text/plain, */*",
            "accept-language":  "es,es-ES;q=0.9",
            "referer":          "https://es.wallapop.com/",
            "origin":           "https://es.wallapop.com",
            "x-appversion":     "820140",
            "x-deviceos":       "0",
            "x-deviceid":       str(uuid.uuid4()),
            "deviceos":         "0",
            "sec-fetch-dest":   "empty",
            "sec-fetch-mode":   "cors",
            "sec-fetch-site":   "same-site",
        }

    async def scrape(
        self,
        url: str = None,          # ignored — uses fixed API endpoint
        max_pages: int = 3,
        seen_ids: Optional[set[str]] = None,
        start_page: int = 1,
        disable_brake: bool = False,
    ) -> list[dict]:
        results: list[dict] = []
        seen = set(seen_ids or set())

        async with httpx.AsyncClient(headers=self._build_headers(), timeout=30.0) as client:
            # Step 1: get search_id + query_params from components endpoint
            query_params = await self._get_query_params(client)
            if query_params is None:
                print(f"[{self.PORTAL_NAME}] could not initialise search session — aborting")
                return []

            next_cursor: Optional[str] = None
            # skip (start_page - 1) pages before collecting results
            pages_to_skip = start_page - 1

            for page_num in range(pages_to_skip + max_pages):
                params = {**query_params, "section_type": "category_feed_results"}
                if next_cursor:
                    params["next_page"] = next_cursor

                data = await self._fetch(client, self._SECTION_URL, params)
                if data is None:
                    print(f"[{self.PORTAL_NAME}] fetch failed — stopping early")
                    break

                section = (data.get("data") or {}).get("section") or {}
                raw_items = section.get("items") or []
                next_cursor = (data.get("meta") or {}).get("next_page") or None

                if not raw_items:
                    print(f"[{self.PORTAL_NAME}] page {page_num + 1}: no items — stopping")
                    break

                # Skip pages before start_page (cursor advances via next_page token)
                if page_num < pages_to_skip:
                    if not next_cursor:
                        break
                    continue

                rel_page = page_num - pages_to_skip + 1
                page_listings: list[dict] = []
                for item in raw_items:
                    listing = self._parse_item(item)
                    if listing is not None:
                        page_listings.append(listing)

                if disable_brake:
                    new = page_listings
                    print(
                        f"[{self.PORTAL_NAME}] page {rel_page}/{max_pages}: "
                        f"{len(page_listings)} extracted (brake disabled)"
                    )
                else:
                    new = [l for l in page_listings if l["ad_id"] not in seen]
                    hit_overlap = len(new) < len(page_listings)
                    print(
                        f"[{self.PORTAL_NAME}] page {rel_page}/{max_pages}: "
                        f"{len(page_listings)} extracted, {len(new)} new"
                    )
                    if hit_overlap:
                        print(f"[{self.PORTAL_NAME}] known ID detected — incremental brake engaged")
                        results.extend(new)
                        break
                    for listing in new:
                        seen.add(listing["ad_id"])

                results.extend(new)

                if not next_cursor:
                    print(f"[{self.PORTAL_NAME}] no next_page cursor — end of results")
                    break

                if rel_page < max_pages:
                    delay = random.uniform(2.0, 5.0)
                    print(f"[{self.PORTAL_NAME}] sleeping {delay:.1f}s…")
                    await asyncio.sleep(delay)

        return results

    async def _get_query_params(self, client: "httpx.AsyncClient") -> Optional[dict]:
        """Call /search/components to obtain query_params (includes the search_id)."""
        data = await self._fetch(
            client,
            self._COMPONENTS_URL,
            self._SEARCH_PARAMS,
            accept="application/json; sequence=v2",
        )
        if data is None:
            return None
        for comp in data.get("components", []):
            if comp.get("type") == "search_section":
                qp = (comp.get("type_data") or {}).get("query_params")
                if qp:
                    return qp
        return None

    async def _fetch(
        self,
        client: "httpx.AsyncClient",
        url: str,
        params: dict,
        accept: Optional[str] = None,
    ) -> Optional[dict]:
        headers = {"accept": accept} if accept else {}
        for attempt in range(self._MAX_RETRY):
            try:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 429:
                    wait = 5 * (2 ** attempt)  # 5s → 10s → 20s
                    print(
                        f"[{self.PORTAL_NAME}] rate limited (429) — "
                        f"sleeping {wait}s (attempt {attempt + 1}/{self._MAX_RETRY})"
                    )
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                print(f"[{self.PORTAL_NAME}] HTTP {exc.response.status_code}: {exc}")
            except Exception as exc:
                print(f"[{self.PORTAL_NAME}] request error: {exc}")
            if attempt < self._MAX_RETRY - 1:
                await asyncio.sleep(2 ** attempt)
        return None

    def _parse_item(self, item: dict) -> Optional[dict]:
        try:
            ad_id = str(item.get("id") or "").strip()
            if not ad_id:
                return None

            title       = (item.get("title") or "").strip()
            description = (item.get("description") or "").strip() or None

            # Price is always {"amount": float, "currency": "EUR"}
            price_raw = item.get("price") or {}
            try:
                price = float(price_raw.get("amount") or 0) or None
            except (ValueError, TypeError):
                price = None
            if price is not None and price < MIN_VALID_PRICE:
                return None

            # URL built from web_slug
            web_slug    = item.get("web_slug") or ad_id
            listing_url = f"https://es.wallapop.com/item/{web_slug}"

            # Car-specific attributes are in type_attributes
            attrs = item.get("type_attributes") or {}

            brand = (attrs.get("brand") or "").strip() or None
            model = (attrs.get("model") or "").strip() or None

            year_raw = attrs.get("year")
            year = int(year_raw) if year_raw is not None else CarScraper.parse_year(title)

            km_raw  = attrs.get("km")
            mileage = int(km_raw) if km_raw is not None else None

            # Fallback brand/model from title when type_attributes is sparse
            if not brand or not model:
                brand_fb, model_fb = MilanunciosScraper._split_brand_model(title)
                brand = brand or brand_fb
                model = model or model_fb

            return {
                "portal":      self.PORTAL_NAME,
                "ad_id":       ad_id,
                "brand":       brand,
                "model":       model,
                "year":        year,
                "mileage":     mileage,
                "price":       price,
                "title":       title,
                "description": description,
                "url":         listing_url,
            }
        except Exception as exc:
            print(f"[{self.PORTAL_NAME}] item parse error (skipping): {exc}")
            return None


# ---------------------------------------------------------------------------
# Portal registry — add new scrapers here
# ---------------------------------------------------------------------------

SCRAPERS: dict[str, type] = {
    "milanuncios": MilanunciosScraper,
    "wallapop":    WallapopScraper,
    # "cochesnet":   CochesNetScraper,    # V3
    # "autoscout24": AutoScout24Scraper,  # V3
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def run(
    portal: str,
    url: str,
    max_pages: int,
    start_page: int = 1,
    disable_brake: bool = False,
) -> str:
    """
    Execute the scraper and persist results to .tmp/.
    Returns the path to the written JSON file.
    """
    scraper_cls = SCRAPERS.get(portal)
    if scraper_cls is None:
        raise ValueError(
            f"Unknown portal: {portal!r}. Available: {list(SCRAPERS.keys())}"
        )

    scraper = scraper_cls()
    results = await scraper.scrape(
        url,
        max_pages=max_pages,
        start_page=start_page,
        disable_brake=disable_brake,
    )

    os.makedirs(".tmp", exist_ok=True)
    timestamp   = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    output_path = f".tmp/{portal}_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)

    print(f"\n[OK] {len(results)} listing(s) → {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Scrape car listings using Playwright + stealth"
    )
    parser.add_argument(
        "--portal",
        default="milanuncios",
        choices=list(SCRAPERS.keys()),
        help="Target portal (default: milanuncios)",
    )
    parser.add_argument(
        "--url",
        default=MilanunciosScraper.BASE_URL,
        help="Search URL to scrape (default: Milanuncios base URL with orden=date)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=3,
        help="Number of pages to scrape (default: 3)",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        default=1,
        dest="start_page",
        help="First page to start from (default: 1)",
    )
    parser.add_argument(
        "--disable-brake",
        action="store_true",
        dest="disable_brake",
        help="Ignore seen_ids and never stop early — for historical dumps",
    )
    args = parser.parse_args()

    asyncio.run(
        run(
            portal=args.portal,
            url=args.url,
            max_pages=args.pages,
            start_page=args.start_page,
            disable_brake=args.disable_brake,
        )
    )
