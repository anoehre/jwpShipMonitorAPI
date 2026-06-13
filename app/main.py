"""FastAPI-App für die JadeWeserPort-Schiffsankünfte.

Scrapt bei Bedarf (mit kurzem In-Memory-Cache, ohne Datenbank) und liefert
die Schiffe, die aktuell am Hafen liegen, sowie die in den nächsten 24 Stunden
erwarteten Ankünfte.
"""
import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional
from zoneinfo import ZoneInfo

import httpx
from fastapi import FastAPI, HTTPException

from . import config
from .models import DakboardItem, HealthResponse, Ship, ShipsResponse
from .scraper import scrape


class _Cache:
    """Sehr einfacher TTL-Cache für die gescrapten Rohdaten."""

    def __init__(self, ttl: int):
        self.ttl = ttl
        self._data: Optional[List[dict]] = None
        self._at: float = 0.0
        self.scraped_at: Optional[datetime] = None
        self.lock = asyncio.Lock()

    def get(self) -> Optional[List[dict]]:
        if self._data is not None and (time.monotonic() - self._at) < self.ttl:
            return self._data
        return None

    def set(self, data: List[dict]) -> None:
        self._data = data
        self._at = time.monotonic()
        self.scraped_at = datetime.now(ZoneInfo(config.TIMEZONE))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Einen HTTP-Client für die Prozesslaufzeit teilen (Connection-Reuse).
    app.state.cache = _Cache(config.CACHE_TTL_SECONDS)
    app.state.client = httpx.AsyncClient(
        headers={"User-Agent": config.USER_AGENT},
        timeout=config.HTTP_TIMEOUT_SECONDS,
        follow_redirects=True,
    )
    try:
        yield
    finally:
        await app.state.client.aclose()


app = FastAPI(
    title="JadeWeserPort Schiffsankünfte API",
    description=(
        "Scrapt die Schiffsankünfte des JadeWeserPort und liefert die Schiffe, "
        "die aktuell am Hafen liegen (Status 'Fest'), sowie die in den nächsten "
        "24 Stunden erwarteten Ankünfte."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


async def _get_ships(app: FastAPI) -> List[dict]:
    """Liefert gescrapte Rohdaten – aus dem Cache oder frisch gescrapt."""
    cache: _Cache = app.state.cache

    if config.CACHE_TTL_SECONDS > 0:
        cached = cache.get()
        if cached is not None:
            return cached

    # Lock verhindert parallele Scrapes bei gleichzeitigen Requests.
    async with cache.lock:
        if config.CACHE_TTL_SECONDS > 0:
            cached = cache.get()
            if cached is not None:
                return cached
        try:
            data = await scrape(app.state.client)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=502,
                detail=f"Scraping fehlgeschlagen: {exc}",
            ) from exc
        cache.set(data)
        return data


def _split(ships: List[dict]) -> tuple[List[Ship], List[Ship]]:
    """Teilt die Schiffe in 'am Hafen' und 'Ankunft in den nächsten 24h'."""
    now = datetime.now(ZoneInfo(config.TIMEZONE))
    horizon = now + timedelta(hours=config.ARRIVAL_WINDOW_HOURS)

    at_port: List[Ship] = []
    arriving: List[Ship] = []
    for raw in ships:
        ship = Ship(**raw)
        if (ship.status or "").strip().lower() == config.AT_PORT_STATUS:
            at_port.append(ship)
        if ship.arrival is not None and now <= ship.arrival <= horizon:
            arriving.append(ship)

    arriving.sort(key=lambda s: s.arrival)  # type: ignore[arg-type]
    return at_port, arriving


def _to_dakboard(ships: List[Ship]) -> List[DakboardItem]:
    """Wandelt Schiffe in das von DAKboard erwartete Array-Format um.

    value = Schiffsname, title = Liniendienst, subtitle = Liegezeit (als Text,
    da DAKboard keine Zeitstempel interpretiert).
    """
    items: List[DakboardItem] = []
    for s in ships:
        parts = []
        if s.arrival_raw:
            parts.append(f"Ankunft {s.arrival_raw}")
        if s.departure_raw:
            parts.append(f"Abfahrt {s.departure_raw}")
        items.append(
            DakboardItem(
                value=s.name,
                title=s.line,
                subtitle=" · ".join(parts) or None,
            )
        )
    return items


@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": "JadeWeserPort Schiffsankünfte API",
        "docs": "/docs",
        "endpoints": [
            "/ships",
            "/ships/at-port",
            "/ships/at-port-dakboardOutput",
            "/ships/arriving",
            "/health",
        ],
    }


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health():
    return HealthResponse(status="ok")


@app.get("/ships", response_model=ShipsResponse, tags=["ships"])
async def ships():
    """Schiffe am Hafen (Status 'Fest') und Ankünfte der nächsten 24 Stunden."""
    raw = await _get_ships(app)
    at_port, arriving = _split(raw)
    return ShipsResponse(
        scraped_at=app.state.cache.scraped_at or datetime.now(ZoneInfo(config.TIMEZONE)),
        source=config.SOURCE_URL,
        window_hours=config.ARRIVAL_WINDOW_HOURS,
        at_port=at_port,
        arriving_next_24h=arriving,
    )


@app.get("/ships/at-port", response_model=List[Ship], tags=["ships"])
async def ships_at_port():
    """Nur die Schiffe, die aktuell am Hafen liegen (Status 'Fest')."""
    raw = await _get_ships(app)
    at_port, _ = _split(raw)
    return at_port


@app.get("/ships/arriving", response_model=List[Ship], tags=["ships"])
async def ships_arriving():
    """Nur die Schiffe, die in den nächsten 24 Stunden ankommen."""
    raw = await _get_ships(app)
    _, arriving = _split(raw)
    return arriving


@app.get(
    "/ships/at-port-dakboardOutput",
    response_model=List[DakboardItem],
    response_model_exclude_none=True,
    tags=["ships"],
)
async def ships_at_port_dakboard():
    """Schiffe am Hafen im DAKboard-Array-Format (value/title/subtitle)."""
    raw = await _get_ships(app)
    at_port, _ = _split(raw)
    return _to_dakboard(at_port)
