"""
Deterministic HTTP utilities for the Agartha scraping layer.

Public API:
    get_session()           → requests.Session with random UA and optional proxy
    fetch(url, **kwargs)    → Response, with automatic retry + exponential backoff
    save_raw(data, name)    → Path  — writes data to .tmp/<name>
"""

import json
import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# User-Agent pool
# ---------------------------------------------------------------------------

_USER_AGENTS = [
    # Chrome / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Chrome / macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Safari / macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    # Edge / Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Chrome / Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]


def random_user_agent() -> str:
    return random.choice(_USER_AGENTS)


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

def get_session(proxy_url: str | None = None) -> requests.Session:
    """Return a Session with a random User-Agent and optional proxy."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": random_user_agent(),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    effective_proxy = proxy_url or os.getenv("PROXY_URL")
    if effective_proxy:
        session.proxies = {"http": effective_proxy, "https": effective_proxy}

    return session


# ---------------------------------------------------------------------------
# Retry + exponential backoff
# ---------------------------------------------------------------------------

def fetch(
    url: str,
    session: requests.Session | None = None,
    method: str = "GET",
    max_retries: int | None = None,
    base_delay: float = 1.0,
    timeout: int | None = None,
    **kwargs: Any,
) -> requests.Response:
    """
    Make an HTTP request with exponential backoff on transient failures.

    Retries on: connection errors, timeouts, and 5xx / 429 status codes.
    Raises the last exception / response error after exhausting retries.

    Backoff formula: base_delay * 2^attempt  ±  25 % jitter
    """
    max_retries = max_retries if max_retries is not None else int(os.getenv("MAX_RETRIES", 3))
    timeout = timeout if timeout is not None else int(os.getenv("REQUEST_TIMEOUT", 30))
    session = session or get_session()

    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = session.request(method, url, timeout=timeout, **kwargs)

            if response.status_code in {429, 500, 502, 503, 504}:
                _wait(attempt, base_delay, response.status_code)
                continue

            response.raise_for_status()
            return response

        except (requests.ConnectionError, requests.Timeout) as exc:
            last_exc = exc
            if attempt < max_retries:
                _wait(attempt, base_delay, None)
            continue

        except requests.HTTPError:
            raise

    if last_exc:
        raise last_exc

    # Should not be reached, but satisfies type checkers
    raise RuntimeError(f"fetch failed after {max_retries} retries: {url}")


def _wait(attempt: int, base_delay: float, status_code: int | None) -> None:
    delay = base_delay * (2 ** attempt)
    jitter = delay * random.uniform(-0.25, 0.25)
    total = max(0.1, delay + jitter)
    if status_code:
        print(f"  [retry] status={status_code}, waiting {total:.1f}s (attempt {attempt + 1})")
    else:
        print(f"  [retry] connection error, waiting {total:.1f}s (attempt {attempt + 1})")
    time.sleep(total)


# ---------------------------------------------------------------------------
# Raw-data persistence
# ---------------------------------------------------------------------------

_TMP_DIR = Path(__file__).resolve().parents[2] / ".tmp"


def save_raw(data: str | bytes | dict | list, name: str) -> Path:
    """
    Write raw data to .tmp/<name>.

    - dict / list  → JSON file (suffix auto-added if missing)
    - str          → text file
    - bytes        → binary file

    Returns the absolute Path of the written file.
    """
    _TMP_DIR.mkdir(parents=True, exist_ok=True)

    # Auto-timestamp to avoid silent overwrites
    stem = Path(name).stem
    suffix = Path(name).suffix

    if isinstance(data, (dict, list)):
        suffix = suffix or ".json"
        path = _TMP_DIR / f"{stem}{suffix}"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    elif isinstance(data, str):
        suffix = suffix or ".txt"
        path = _TMP_DIR / f"{stem}{suffix}"
        path.write_text(data, encoding="utf-8")

    elif isinstance(data, bytes):
        suffix = suffix or ".bin"
        path = _TMP_DIR / f"{stem}{suffix}"
        path.write_bytes(data)

    else:
        raise TypeError(f"save_raw: unsupported data type {type(data)}")

    print(f"  [saved] {path}")
    return path


# ---------------------------------------------------------------------------
# Quick smoke-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("User-Agent sample:", random_user_agent())

    r = fetch("https://httpbin.org/get")
    print("Status:", r.status_code)

    out = save_raw(r.json(), "httpbin_test.json")
    print("Saved to:", out)
