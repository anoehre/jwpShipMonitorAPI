"""Scraping der JadeWeserPort-Schiffsankünfte per HTTP.

Die Seite rendert die Tabelle serverseitig – ein einfacher HTTP-GET reicht,
ein Browser ist nicht nötig. Der HTML-Aufbau (Stand 2026):

    <div class="arrivals">
      <div class="headline"> ... </div>
      <div class="line">
        <div>
          <div>Maersk Virgina (PGS)</div>   <!-- Name (Linie) -->
          <div>12.06.2026 03:30</div>       <!-- Ankunft -->
          <div>13.06.2026 23:59</div>       <!-- Abfahrt -->
        </div>
        <div>
          <div class="unvis">&nbsp;</div>   <!-- Platzhalter -->
          <div>65.433</div>                 <!-- TDW -->
          <div>Fest</div>                   <!-- Status -->
        </div>
      </div>
      ...
    </div>
"""
import re
from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup

from . import config

_NAME_LINE_RE = re.compile(r"^(?P<name>.*?)\s*\((?P<line>[^)]*)\)\s*$")
_DATE_FMT = "%d.%m.%Y %H:%M"


def _parse_name_and_line(text: str) -> tuple[str, Optional[str]]:
    """Trennt 'Maersk Virgina (PGS)' in Name und Linie auf."""
    text = text.strip()
    m = _NAME_LINE_RE.match(text)
    if not m:
        return text, None
    name = m.group("name").strip()
    line = m.group("line").strip() or None
    return (name or text), line


def _parse_datetime(text: str, tz: ZoneInfo) -> Optional[datetime]:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, _DATE_FMT).replace(tzinfo=tz)
    except ValueError:
        return None


def _parse_tdw(text: str) -> Optional[int]:
    """'65.433' -> 65433. Tausenderpunkte entfernen."""
    digits = re.sub(r"[^\d]", "", text or "")
    return int(digits) if digits else None


def parse_arrivals(html: str) -> List[dict]:
    """Parst das HTML zu einer Liste von Schiffs-Dicts.

    Reine Funktion – dadurch isoliert testbar (ohne Netzwerk).
    """
    tz = ZoneInfo(config.TIMEZONE)
    soup = BeautifulSoup(html, "lxml")

    ships: List[dict] = []
    for line in soup.select(".arrivals .line"):
        # Alle Blatt-<div> in Dokumentreihenfolge einsammeln.
        cells = line.select(":scope > div > div")
        # Den leeren Platzhalter ('unvis') herausfiltern.
        values = [
            c.get_text(strip=True)
            for c in cells
            if "unvis" not in (c.get("class") or [])
        ]
        # Erwartet: [name(linie), ankunft, abfahrt, tdw, status]
        if len(values) < 5:
            continue
        name_line, arr_raw, dep_raw, tdw_raw, status = values[:5]

        name, line_name = _parse_name_and_line(name_line)
        ships.append(
            {
                "name": name,
                "line": line_name,
                "arrival": _parse_datetime(arr_raw, tz),
                "departure": _parse_datetime(dep_raw, tz),
                "arrival_raw": arr_raw or None,
                "departure_raw": dep_raw or None,
                "tdw": _parse_tdw(tdw_raw),
                "status": status,
            }
        )
    return ships


async def fetch_html(client: httpx.AsyncClient) -> str:
    """Ruft die Seite per HTTP-GET ab und liefert das HTML."""
    resp = await client.get(config.SOURCE_URL)
    resp.raise_for_status()
    return resp.text


async def scrape(client: httpx.AsyncClient) -> List[dict]:
    """Holt die Seite und parst die Schiffsliste."""
    html = await fetch_html(client)
    return parse_arrivals(html)
