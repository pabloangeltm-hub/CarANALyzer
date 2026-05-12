"""
Benchmark Milanuncios scraping strategies.

F1-T01 compares the current Playwright + stealth approach against Scrapling's
StealthyFetcher on Milanuncios search pages. The script records page-level
latency, block signals, extracted listing counts, and field coverage, then
writes JSON and Markdown reports under .tmp/.

Usage:
    python tools/benchmark_scrapers.py
    python tools/benchmark_scrapers.py --pages 20 --methods both
    python tools/benchmark_scrapers.py --methods scrapling --url "https://..."
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import json
import math
import random
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.scrape_cars import (  # noqa: E402
    MIN_VALID_PRICE,
    MilanunciosScraper,
    _AUTH_STATE_PATH,
    _CHROME_ARGS,
    _SESSIONS_DIR,
    _USER_AGENTS,
    _VIEWPORT,
    _WINDOWS_UA,
)

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")


FIELD_NAMES = ("ad_id", "brand", "model", "year", "mileage", "price", "url")
DEFAULT_OUTPUT_DIR = ROOT / ".tmp"


@dataclass
class PageMetric:
    method: str
    page_num: int
    url: str
    blocked: bool
    latency_ms: int
    http_status: Optional[int]
    cards_count: int
    listings_count: int
    field_coverage: dict[str, float]
    title: Optional[str] = None
    error: Optional[str] = None


def _percentile(values: list[int], percentile: float) -> Optional[int]:
    if not values:
        return None
    ordered = sorted(values)
    index = math.ceil((percentile / 100) * len(ordered)) - 1
    return ordered[max(0, min(index, len(ordered) - 1))]


def _coverage(listings: list[dict[str, Any]]) -> dict[str, float]:
    if not listings:
        return {field: 0.0 for field in FIELD_NAMES}
    return {
        field: round(
            sum(1 for listing in listings if listing.get(field) not in (None, "", []))
            / len(listings),
            4,
        )
        for field in FIELD_NAMES
    }


def _summarize(method: str, metrics: list[PageMetric]) -> dict[str, Any]:
    latencies = [metric.latency_ms for metric in metrics]
    successful = [metric for metric in metrics if not metric.blocked and not metric.error]
    total_listings = sum(metric.listings_count for metric in metrics)
    avg_coverage: dict[str, float] = {}
    for field in FIELD_NAMES:
        weighted_total = sum(
            metric.field_coverage[field] * metric.listings_count
            for metric in metrics
            if metric.listings_count
        )
        avg_coverage[field] = (
            round(weighted_total / total_listings, 4) if total_listings else 0.0
        )

    return {
        "method": method,
        "pages_attempted": len(metrics),
        "pages_successful": len(successful),
        "blocked_pages": sum(1 for metric in metrics if metric.blocked),
        "errored_pages": sum(1 for metric in metrics if metric.error),
        "block_rate": round(
            sum(1 for metric in metrics if metric.blocked) / len(metrics), 4
        )
        if metrics
        else None,
        "latency_ms_avg": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "latency_ms_p50": _percentile(latencies, 50),
        "latency_ms_p95": _percentile(latencies, 95),
        "total_listings": total_listings,
        "avg_listings_per_successful_page": round(total_listings / len(successful), 2)
        if successful
        else 0.0,
        "field_coverage": avg_coverage,
    }


def _session_pool() -> list[str]:
    pool = sorted(glob.glob(str(ROOT / _SESSIONS_DIR / "*.json")))
    if not pool and (ROOT / _AUTH_STATE_PATH).exists():
        pool = [str(ROOT / _AUTH_STATE_PATH)]
    random.shuffle(pool)
    return pool


def _cookies_from_storage_state(path: Optional[str]) -> list[dict[str, Any]]:
    if not path:
        return []
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    cookies = payload.get("cookies", [])
    return cookies if isinstance(cookies, list) else []


def _page_url(scraper: MilanunciosScraper, base_url: str, page_num: int) -> str:
    return scraper._paginate_url(base_url, page_num)


def _looks_blocked(title: Optional[str], cards_count: int, body: str = "") -> bool:
    title_l = (title or "").lower()
    body_l = body.lower()
    if "pardon our interruption" in title_l:
        return True
    if "datadome" in body_l and cards_count == 0:
        return True
    return cards_count == 0


def _has_block_signal(title: Optional[str], cards_count: int, body: str = "") -> bool:
    if title is None and cards_count == 0 and not body:
        return False
    return _looks_blocked(title, cards_count, body)


async def _close_safely(closeable: Any, label: str) -> None:
    try:
        await asyncio.wait_for(closeable.close(), timeout=10)
    except Exception as exc:
        print(f"[cleanup] {label} close failed: {type(exc).__name__}: {exc}")


async def benchmark_playwright(
    base_url: str,
    start_page: int,
    pages: int,
    timeout_ms: int,
    use_session_pool: bool,
) -> list[PageMetric]:
    scraper = MilanunciosScraper()
    sessions = _session_pool() if use_session_pool else []
    metrics: list[PageMetric] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=_CHROME_ARGS)
        try:
            for offset in range(pages):
                page_num = start_page + offset
                url = _page_url(scraper, base_url, page_num)
                started = time.perf_counter()
                http_status: Optional[int] = None
                cards_count = 0
                listings: list[dict[str, Any]] = []
                title: Optional[str] = None
                error: Optional[str] = None
                session_path = sessions[offset % len(sessions)] if sessions else None

                context_kwargs: dict[str, Any] = {
                    "viewport": _VIEWPORT,
                    "user_agent": _WINDOWS_UA if session_path else random.choice(_USER_AGENTS),
                    "locale": "es-ES",
                    "timezone_id": "Europe/Madrid",
                    "extra_http_headers": {"Accept-Language": "es-ES,es;q=0.9"},
                }
                if session_path:
                    context_kwargs["storage_state"] = session_path

                context = await browser.new_context(**context_kwargs)
                page = await context.new_page()
                await Stealth().apply_stealth_async(page)
                hard_timeout = max(60.0, (timeout_ms / 1000) + 90.0)
                try:
                    async with asyncio.timeout(hard_timeout):
                        response = await page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=timeout_ms,
                        )
                        http_status = response.status if response else None
                        await asyncio.sleep(random.uniform(1.0, 2.0))
                        title = await page.title()
                        listings = await scraper._extract_listings(page)
                        cards_count = len(await page.query_selector_all(scraper._SEL_CARD))
                except TimeoutError:
                    error = f"TimeoutError: page exceeded {hard_timeout:.0f}s wall timeout"
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                finally:
                    await _close_safely(context, "playwright context")

                latency_ms = int((time.perf_counter() - started) * 1000)
                blocked = _has_block_signal(title, cards_count)
                metrics.append(
                    PageMetric(
                        method="playwright",
                        page_num=page_num,
                        url=url,
                        blocked=blocked,
                        latency_ms=latency_ms,
                        http_status=http_status,
                        cards_count=cards_count,
                        listings_count=len(listings),
                        field_coverage=_coverage(listings),
                        title=title,
                        error=error,
                    )
                )
                print(
                    f"[playwright] page={page_num} blocked={blocked} "
                    f"listings={len(listings)} latency_ms={latency_ms}"
                )
        finally:
            await browser.close()

    return metrics


async def _scrapling_page_action(page: Any) -> None:
    for selector in MilanunciosScraper._COOKIE_SELECTORS:
        try:
            await page.click(selector, timeout=2_000)
            break
        except Exception:
            continue

    scroll_pos = 0
    for _ in range(80):
        page_height = await page.evaluate("document.body.scrollHeight")
        if scroll_pos >= page_height:
            break
        scroll_pos = min(scroll_pos + random.randint(260, 420), page_height)
        await page.evaluate(f"window.scrollTo(0, {scroll_pos});")
        await asyncio.sleep(random.uniform(0.2, 0.45))
    await asyncio.sleep(random.uniform(0.8, 1.2))


def _response_body(response: Any) -> str:
    for attr in ("html_content", "body", "text", "html"):
        value = getattr(response, attr, None)
        if callable(value):
            try:
                value = value()
            except TypeError:
                continue
        if isinstance(value, bytes):
            value = value.decode(getattr(response, "encoding", None) or "utf-8", errors="replace")
        if isinstance(value, str) and value.strip():
            return value
    return str(response)


def _first_text(node: Any, selector: str) -> str:
    match = node.select_one(selector)
    return match.get_text(" ", strip=True) if match else ""


def _script_json_parse_payload(script_text: str, variable_name: str) -> Optional[dict[str, Any]]:
    pattern = re.compile(
        rf"window\.{re.escape(variable_name)}\s*=\s*JSON\.parse\("
        r"(?P<payload>\"(?:\\.|[^\"\\])*\")\)\s*;?",
        re.S,
    )
    match = pattern.search(script_text)
    if not match:
        return None
    try:
        raw_json = json.loads(match.group("payload"))
        payload = json.loads(raw_json)
    except (TypeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _extract_initial_props(soup: BeautifulSoup) -> Optional[dict[str, Any]]:
    for script in soup.find_all("script"):
        script_text = script.string or script.get_text() or ""
        if "window.__INITIAL_PROPS__" not in script_text:
            continue
        payload = _script_json_parse_payload(script_text, "__INITIAL_PROPS__")
        if payload:
            return payload
    return None


def _tag_value(ad: dict[str, Any], tag_type: str) -> str:
    for tag in ad.get("tags") or []:
        if not isinstance(tag, dict):
            continue
        if str(tag.get("type") or "").lower() == tag_type:
            return str(tag.get("text") or "")
    return ""


def _price_from_initial_ad(ad: dict[str, Any]) -> Optional[float]:
    price = ad.get("price")
    if not isinstance(price, dict):
        return None

    values: list[float] = []
    for key in ("cashPrice", "financedPrice"):
        price_block = price.get(key)
        if not isinstance(price_block, dict):
            continue
        value = price_block.get("value")
        if isinstance(value, (int, float)):
            values.append(float(value))

    return min(values) if values else None


def _location_from_initial_ad(ad: dict[str, Any]) -> Optional[str]:
    location = ad.get("location")
    if not isinstance(location, dict):
        return None

    city = location.get("city") if isinstance(location.get("city"), dict) else {}
    province = location.get("province") if isinstance(location.get("province"), dict) else {}
    parts = [city.get("name"), province.get("name")]
    return ", ".join(str(part) for part in parts if part)


def _initial_ad_to_listing(ad: dict[str, Any]) -> Optional[dict[str, Any]]:
    ad_id = str(ad.get("id") or "").strip()
    title = str(ad.get("title") or "").strip()
    url = str(ad.get("url") or "").strip()
    if not ad_id or not title or not url:
        return None

    listing_url = f"https://www.milanuncios.com{url}" if url.startswith("/") else url
    price = _price_from_initial_ad(ad)
    if price is not None and price < MIN_VALID_PRICE:
        return None

    brand, model = MilanunciosScraper._split_brand_model(title)
    year = MilanunciosScraper.parse_year(_tag_value(ad, "año")) or MilanunciosScraper.parse_year(title)
    mileage = MilanunciosScraper.parse_mileage(_tag_value(ad, "kilómetros"))

    return {
        "portal": "milanuncios",
        "ad_id": ad_id,
        "brand": brand,
        "model": model,
        "year": year,
        "mileage": mileage,
        "price": price,
        "title": title,
        "description": ad.get("description") or None,
        "url": listing_url,
        "seller_type": ad.get("sellerType") or None,
        "location": _location_from_initial_ad(ad),
    }


def _extract_initial_prop_listings(soup: BeautifulSoup) -> list[dict[str, Any]]:
    initial_props = _extract_initial_props(soup)
    if not initial_props:
        return []

    ad_list = (
        initial_props.get("adListPagination", {})
        .get("adList", {})
        .get("ads", [])
    )
    if not isinstance(ad_list, list):
        return []

    listings: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ad in ad_list:
        if not isinstance(ad, dict):
            continue
        listing = _initial_ad_to_listing(ad)
        if not listing:
            continue
        ad_id = listing["ad_id"]
        if ad_id in seen:
            continue
        seen.add(ad_id)
        listings.append(listing)
    return listings


def _extract_scrapling_listings(html: str) -> tuple[list[dict[str, Any]], int, Optional[str]]:
    scraper = MilanunciosScraper()
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    cards = soup.select(scraper._SEL_CARD)
    initial_listings = _extract_initial_prop_listings(soup)
    if initial_listings:
        return initial_listings, max(len(cards), len(initial_listings)), title

    listings: list[dict[str, Any]] = []
    seen: set[str] = set()

    for card in cards:
        title_text = _first_text(card, scraper._SEL_TITLE)
        if not title_text:
            continue

        href = ""
        for selector in (scraper._SEL_LINK, "a[href^='/']", "a[href]", "a"):
            link = card.select_one(selector)
            if link and link.get("href"):
                href = str(link["href"])
                break
        if not href:
            continue

        listing_url = f"https://www.milanuncios.com{href}" if href.startswith("/") else href
        match = re.search(r"(\d{6,})", listing_url)
        ad_id = match.group(1) if match else href.strip("/").replace("/", "-")
        if ad_id in seen:
            continue

        price = MilanunciosScraper.parse_price(_first_text(card, scraper._SEL_PRICE))
        if price is not None and price < MIN_VALID_PRICE:
            continue

        tag_texts = [
            tag.get_text(" ", strip=True)
            for tag in card.select(scraper._SEL_TAG_LABELS)
        ]
        year = None
        mileage = None
        for tag in tag_texts:
            if year is None:
                year = MilanunciosScraper.parse_year(tag)
            if mileage is None and "km" in tag.lower():
                mileage = MilanunciosScraper.parse_mileage(tag)
        if year is None:
            year = MilanunciosScraper.parse_year(title_text)

        brand, model = MilanunciosScraper._split_brand_model(title_text)
        seen.add(ad_id)
        listings.append(
            {
                "portal": "milanuncios",
                "ad_id": ad_id,
                "brand": brand,
                "model": model,
                "year": year,
                "mileage": mileage,
                "price": price,
                "title": title_text,
                "description": _first_text(card, scraper._SEL_DESCRIPTION) or None,
                "url": listing_url,
            }
        )

    return listings, len(cards), title


async def benchmark_scrapling(
    base_url: str,
    start_page: int,
    pages: int,
    timeout_ms: int,
    use_session_pool: bool,
) -> list[PageMetric]:
    try:
        from scrapling.fetchers import StealthyFetcher
    except ImportError as exc:
        raise RuntimeError(
            "Scrapling is not installed. Run: python -m pip install scrapling"
        ) from exc

    scraper = MilanunciosScraper()
    sessions = _session_pool() if use_session_pool else []
    metrics: list[PageMetric] = []

    for offset in range(pages):
        page_num = start_page + offset
        url = _page_url(scraper, base_url, page_num)
        started = time.perf_counter()
        http_status: Optional[int] = None
        cards_count = 0
        listings: list[dict[str, Any]] = []
        title: Optional[str] = None
        error: Optional[str] = None
        body = ""
        session_path = sessions[offset % len(sessions)] if sessions else None
        cookies = _cookies_from_storage_state(session_path)

        try:
            hard_timeout = max(60.0, (timeout_ms / 1000) + 90.0)
            response = await asyncio.wait_for(
                StealthyFetcher.async_fetch(
                    url,
                    headless=True,
                    timeout=timeout_ms,
                    wait=1_000,
                    wait_selector=scraper._SEL_CARD,
                    wait_selector_state="attached",
                    locale="es-ES",
                    timezone_id="Europe/Madrid",
                    block_webrtc=True,
                    hide_canvas=True,
                    google_search=True,
                    page_action=_scrapling_page_action,
                    cookies=cookies or None,
                    useragent=_WINDOWS_UA if session_path else None,
                    extra_headers={"Accept-Language": "es-ES,es;q=0.9"},
                ),
                timeout=hard_timeout,
            )
            http_status = getattr(response, "status", None)
            body = _response_body(response)
            listings, cards_count, title = _extract_scrapling_listings(body)
        except TimeoutError:
            error = f"TimeoutError: page exceeded {hard_timeout:.0f}s wall timeout"
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        latency_ms = int((time.perf_counter() - started) * 1000)
        blocked = _has_block_signal(title, cards_count, body)
        metrics.append(
            PageMetric(
                method="scrapling",
                page_num=page_num,
                url=url,
                blocked=blocked,
                latency_ms=latency_ms,
                http_status=http_status,
                cards_count=cards_count,
                listings_count=len(listings),
                field_coverage=_coverage(listings),
                title=title,
                error=error,
            )
        )
        print(
            f"[scrapling] page={page_num} blocked={blocked} "
            f"listings={len(listings)} latency_ms={latency_ms}"
        )

    return metrics


def _write_reports(
    output_dir: Path,
    started_at: str,
    url: str,
    pages: int,
    all_metrics: dict[str, list[PageMetric]],
    find_skills_note: str,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = {
        method: _summarize(method, metrics)
        for method, metrics in all_metrics.items()
    }
    payload = {
        "started_at": started_at,
        "base_url": url,
        "pages": pages,
        "find_skills": find_skills_note,
        "summaries": summaries,
        "pages_detail": {
            method: [asdict(metric) for metric in metrics]
            for method, metrics in all_metrics.items()
        },
    }
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"scraper_benchmark_{stamp}.json"
    md_path = output_dir / f"scraper_benchmark_{stamp}.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Scraper Benchmark",
        "",
        f"- Started: {started_at}",
        f"- Base URL: {url}",
        f"- Pages per method: {pages}",
        f"- /find-skills: {find_skills_note}",
        "",
        "| Method | Pages | Block rate | Avg latency ms | p50 | p95 | Listings | Avg listings/success |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for method, summary in summaries.items():
        lines.append(
            "| {method} | {pages} | {block_rate} | {avg} | {p50} | {p95} | {listings} | {avg_listings} |".format(
                method=method,
                pages=summary["pages_attempted"],
                block_rate=summary["block_rate"],
                avg=summary["latency_ms_avg"],
                p50=summary["latency_ms_p50"],
                p95=summary["latency_ms_p95"],
                listings=summary["total_listings"],
                avg_listings=summary["avg_listings_per_successful_page"],
            )
        )

    lines.extend(["", "## Field Coverage", ""])
    for method, summary in summaries.items():
        coverage = ", ".join(
            f"{field}={value}" for field, value in summary["field_coverage"].items()
        )
        lines.append(f"- {method}: {coverage}")

    lines.extend(["", "## Page Detail", ""])
    lines.append("| Method | Page | Blocked | Status | Cards | Listings | Latency ms | Error |")
    lines.append("|---|---:|---|---:|---:|---:|---:|---|")
    for metrics in all_metrics.values():
        for metric in metrics:
            lines.append(
                f"| {metric.method} | {metric.page_num} | {metric.blocked} | "
                f"{metric.http_status or ''} | {metric.cards_count} | "
                f"{metric.listings_count} | {metric.latency_ms} | "
                f"{(metric.error or '').replace('|', '/')} |"
            )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


async def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark Milanuncios scrapers")
    parser.add_argument("--url", default=MilanunciosScraper.BASE_URL)
    parser.add_argument("--pages", type=int, default=20)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument(
        "--methods",
        choices=("both", "playwright", "scrapling"),
        default="both",
    )
    parser.add_argument("--timeout-ms", type=int, default=45_000)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--no-session-pool",
        action="store_true",
        help="Do not inject saved Milanuncios sessions into the Playwright baseline.",
    )
    args = parser.parse_args()

    started_at = datetime.now().isoformat(timespec="seconds")
    find_skills_note = (
        "d4vinci/scrapling@scrapling-official (1.5K installs); "
        "nextjs/react hydration search found no mature skill (best 56 installs)"
    )
    all_metrics: dict[str, list[PageMetric]] = {}

    if args.methods in ("both", "playwright"):
        all_metrics["playwright"] = await benchmark_playwright(
            base_url=args.url,
            start_page=args.start_page,
            pages=args.pages,
            timeout_ms=args.timeout_ms,
            use_session_pool=not args.no_session_pool,
        )

    if args.methods in ("both", "scrapling"):
        all_metrics["scrapling"] = await benchmark_scrapling(
            base_url=args.url,
            start_page=args.start_page,
            pages=args.pages,
            timeout_ms=args.timeout_ms,
            use_session_pool=not args.no_session_pool,
        )

    json_path, md_path = _write_reports(
        output_dir=Path(args.output_dir),
        started_at=started_at,
        url=args.url,
        pages=args.pages,
        all_metrics=all_metrics,
        find_skills_note=find_skills_note,
    )
    print(f"\n[OK] JSON report: {json_path}")
    print(f"[OK] Markdown report: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
