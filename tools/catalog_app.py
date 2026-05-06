"""
Agartha B2B Catalog — FastAPI app that reads listings from .tmp/agartha.db.

Run:  uvicorn tools.catalog_app:app --reload --port 8000
Auth: browser → visita /?api_key=<value> una vez (guarda cookie de sesión)
      API     → header X-API-Key: <value>
"""

import os
import sqlite3
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

load_dotenv()

API_KEY = os.getenv("API_KEY", "changeme")
DB_PATH = Path(".tmp/agartha.db")
PAGE_SIZE = 25
COOKIE_NAME = "agartha_key"

app = FastAPI(title="Agartha B2B Catalog", docs_url=None, redoc_url=None)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _is_authenticated(request: Request) -> bool:
    return (
        request.cookies.get(COOKIE_NAME) == API_KEY
        or request.headers.get("X-API-Key") == API_KEY
    )


def _query_listings(
    min_roi: float,
    brand: Optional[str],
    forensic_status: Optional[str],
    page: int,
) -> tuple[list[dict], int]:
    if not DB_PATH.exists():
        return [], 0

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conditions = ["roi_neto > 0", "LOWER(COALESCE(forensic_status,'')) != 'damaged'"]
        params: list = []

        if min_roi > 0:
            conditions.append("roi_neto >= ?")
            params.append(min_roi)
        if brand and brand.strip():
            conditions.append("LOWER(brand) LIKE ?")
            params.append(f"%{brand.strip().lower()}%")
        if forensic_status and forensic_status.strip() and forensic_status != "all":
            conditions.append("forensic_status = ?")
            params.append(forensic_status.strip())

        where = " AND ".join(conditions)

        total = conn.execute(
            f"SELECT COUNT(*) FROM listings WHERE {where}", params
        ).fetchone()[0]

        offset = (page - 1) * PAGE_SIZE
        rows = conn.execute(
            f"SELECT portal, brand, model, year, mileage, price, market_price,"
            f" roi_neto, forensic_status, url, scraped_at"
            f" FROM listings WHERE {where}"
            f" ORDER BY roi_neto DESC LIMIT ? OFFSET ?",
            params + [PAGE_SIZE, offset],
        ).fetchall()

        return [dict(r) for r in rows], total
    finally:
        conn.close()


def _get_distinct_statuses() -> list[str]:
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT DISTINCT forensic_status FROM listings"
            " WHERE forensic_status IS NOT NULL ORDER BY forensic_status"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    api_key: Optional[str] = Query(default=None),
    min_roi: float = Query(default=0.0, ge=0),
    brand: Optional[str] = Query(default=None),
    forensic_status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
):
    # ?api_key= in URL → validate, set cookie, redirect (cleans key from URL)
    if api_key is not None:
        if api_key == API_KEY:
            resp = RedirectResponse(url="/", status_code=303)
            resp.set_cookie(COOKIE_NAME, API_KEY, httponly=True, samesite="lax")
            return resp
        return HTMLResponse("<h3>API key inválida.</h3>", status_code=401)

    if not _is_authenticated(request):
        return HTMLResponse(
            "<h3>401 — Acceso denegado.</h3>"
            "<p>Visita <code>/?api_key=TU_CLAVE</code> para iniciar sesión.</p>",
            status_code=401,
        )

    listings, total = _query_listings(min_roi, brand, forensic_status, page)
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    statuses = _get_distinct_statuses()

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "listings": listings,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "page_size": PAGE_SIZE,
            "min_roi": min_roi,
            "brand": brand or "",
            "forensic_status": forensic_status or "all",
            "statuses": statuses,
        },
    )
