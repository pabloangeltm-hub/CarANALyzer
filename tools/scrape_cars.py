"""
Car listing scraper — Playwright async + stealth.
Bypasses basic bot detection (Cloudflare, Datadome) on Spanish car portals.

Architecture:
    CarScraper (abstract base)
    └── MilanunciosScraper  ← V1 implementation (proof of concept)

Output format per listing (compatible with valuation_engine.py):
    {
        "portal":  "milanuncios",
        "brand":   "BMW",
        "model":   "320d",
        "year":    2019,
        "mileage": 145000,   # int | None
        "price":   14500.0,  # float | None
        "title":   "BMW 320d 2019 Diesel",
        "url":     "https://www.milanuncios.com/..."
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
import json
import os
import random
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

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
_DELAY_BETWEEN_PAGES = (2.5, 5.0)
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
    """

    PORTAL_NAME: str = "base"

    async def scrape(self, url: str, max_pages: int = 3) -> list[dict]:
        """
        Launch a stealth browser, iterate through pages, and collect listings.
        Returns a flat list of raw car dicts.

        Hit & Run architecture: each page gets a fresh context + page + stealth
        injection so Datadome sees zero accumulated bot fingerprint across pages.
        """
        results: list[dict] = []

        async with async_playwright() as pw:
            browser = await self._launch_browser(pw)
            try:
                for page_num in range(1, max_pages + 1):
                    context = await browser.new_context(
                        viewport=_VIEWPORT,
                        user_agent=random.choice(_USER_AGENTS),
                        locale="es-ES",
                        timezone_id="Europe/Madrid",
                        extra_http_headers={"Accept-Language": "es-ES,es;q=0.9"},
                    )
                    page = await context.new_page()
                    await Stealth().apply_stealth_async(page)

                    try:
                        page_url = self._paginate_url(url, page_num)
                        print(f"[{self.PORTAL_NAME}] page {page_num}/{max_pages} → {page_url}")

                        ok = await self._navigate(page, page_url)
                        if not ok:
                            print(f"[{self.PORTAL_NAME}] navigation failed — stopping early")
                            break

                        listings = await self._extract_listings(page)
                        print(f"[{self.PORTAL_NAME}] extracted {len(listings)} listing(s) from page {page_num}")
                        results.extend(listings)
                    finally:
                        await context.close()

                    if page_num < max_pages:
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

    Default search URL:
        https://www.milanuncios.com/coches-de-segunda-mano/

    Pagination pattern:
        https://www.milanuncios.com/coches-de-segunda-mano/?pagina=2

    Selector notes:
        Milanuncios uses React with server-side rendering. Class names are
        stable semantic BEM names (ma-AdCard, ma-AdPrice, ma-AdTag) as of
        April 2026. Mark any selector with # VERIFY if it stops matching
        after a portal update.
    """

    PORTAL_NAME = "milanuncios"
    BASE_URL    = "https://www.milanuncios.com/coches-de-segunda-mano/"

    # VERIFY these selectors after any Milanuncios frontend update
    # V2 frontend — wildcard class matching for resilience against minification
    _SEL_CARD        = "article[class*='ma-AdCardV2']"
    _SEL_TITLE       = "[class*='ma-AdCardListingV2-TitleRow'], [class*='ma-AdCardV2-title']"
    _SEL_LINK        = "a[class*='ma-AdCardV2-link']"
    _SEL_PRICE       = "[class*='ma-AdCardV2-price'], [class*='ma-AdPrice']"
    _SEL_TAG_LABELS  = "[class*='ma-AdCardV2-tag'], [class*='ma-AdTag-label']"

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

    async def _extract_listings(self, page: Page) -> list[dict]:
        await self._handle_cookies(page)

        # Wait for at least one listing card to appear
        try:
            await page.wait_for_selector(self._SEL_CARD, timeout=12_000)
        except Exception:
            # Either a bot challenge was triggered or the search has no results
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

        cards = await page.query_selector_all(self._SEL_CARD)
        results: list[dict] = []

        for card in cards:
            try:
                item = await self._parse_card(card)
                if item is not None:
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
        for link_sel in (self._SEL_LINK, "a"):
            link_el = await card.query_selector(link_sel)
            if link_el:
                href = await link_el.get_attribute("href") or ""
            if href:
                break
        url = f"https://www.milanuncios.com{href}" if href.startswith("/") else href

        # ── Price ────────────────────────────────────────────────────
        price_el  = await card.query_selector(self._SEL_PRICE)
        price_raw = (await price_el.inner_text()).strip() if price_el else ""
        price     = self.parse_price(price_raw)

        # Discard anuncios trampa immediately
        if price is not None and price < MIN_VALID_PRICE:
            return None

        # ── Detail badges (year, mileage, fuel) ─────────────────────
        tag_els     = await card.query_selector_all(self._SEL_TAG_LABELS)
        tag_texts   = [(await el.inner_text()).strip() for el in tag_els]

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

        # ── Brand / model (best-effort from title) ───────────────────
        brand, model = self._split_brand_model(title)

        return {
            "portal":  self.PORTAL_NAME,
            "brand":   brand,
            "model":   model,
            "year":    year,
            "mileage": mileage,
            "price":   price,
            "title":   title,
            "url":     url,
        }

    @staticmethod
    def _split_brand_model(title: str) -> tuple[Optional[str], Optional[str]]:
        """
        'BMW 320d 2019 Diesel' → ('BMW', '320d')
        'BMW - 320d 2019'      → ('BMW', '320d')
        Milanuncios titles follow: Brand [–] Model [Year] [extras…]
        Lone hyphens and dashes are stripped before splitting.
        """
        # Strip lone separators (hyphen, en-dash, em-dash) surrounded by spaces
        cleaned = re.sub(r"\s+[-–—]\s+", " ", title.strip())
        parts = [p for p in cleaned.split() if p not in ("-", "–", "—")]
        if len(parts) >= 2:
            return parts[0].upper(), parts[1]
        if len(parts) == 1:
            return parts[0].upper(), None
        return None, None


# ---------------------------------------------------------------------------
# Portal registry — add new scrapers here
# ---------------------------------------------------------------------------

SCRAPERS: dict[str, type[CarScraper]] = {
    "milanuncios": MilanunciosScraper,
    # "cochesnet":   CochesNetScraper,    # V2
    # "autoscout24": AutoScout24Scraper,  # V2
}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def run(portal: str, url: str, max_pages: int) -> str:
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
    results = await scraper.scrape(url, max_pages=max_pages)

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
        help="Search URL to scrape (default: Milanuncios base URL)",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=3,
        help="Number of pages to scrape (default: 3)",
    )
    args = parser.parse_args()

    asyncio.run(run(portal=args.portal, url=args.url, max_pages=args.pages))
