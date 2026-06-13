"""Unit-Tests für den HTML-Parser (ohne Browser)."""
from app.scraper import parse_arrivals

# Verkürztes, aber strukturgetreues Abbild der echten Seite.
SAMPLE_HTML = """
<div class="arrivals">
  <div class="headline">
    <div><div>Schiffsname (Linie)</div><div>Ankunft</div><div>Abfahrt</div></div>
    <div><div class="unvis">&nbsp;</div><div>TDW</div><div>Status</div></div>
  </div>
  <div class="line">
    <div>
      <div>Maersk Virgina (PGS)</div>
      <div>12.06.2026 03:30</div>
      <div>13.06.2026 23:59</div>
    </div>
    <div>
      <div class="unvis">&nbsp;</div>
      <div>65.433</div>
      <div>Fest</div>
    </div>
  </div>
  <div class="line">
    <div>
      <div>Longeden ()</div>
      <div>15.06.2026 08:00</div>
      <div>16.06.2026 18:00</div>
    </div>
    <div>
      <div class="unvis">&nbsp;</div>
      <div>8.467</div>
      <div>Avisiert</div>
    </div>
  </div>
</div>
"""


def test_parses_all_rows():
    ships = parse_arrivals(SAMPLE_HTML)
    assert len(ships) == 2


def test_name_and_line_split():
    ships = parse_arrivals(SAMPLE_HTML)
    assert ships[0]["name"] == "Maersk Virgina"
    assert ships[0]["line"] == "PGS"
    # Leere Linie -> None
    assert ships[1]["name"] == "Longeden"
    assert ships[1]["line"] is None


def test_tdw_parsed_as_int():
    ships = parse_arrivals(SAMPLE_HTML)
    assert ships[0]["tdw"] == 65433
    assert ships[1]["tdw"] == 8467


def test_datetime_parsed_with_timezone():
    ships = parse_arrivals(SAMPLE_HTML)
    arr = ships[0]["arrival"]
    assert arr is not None
    assert arr.year == 2026 and arr.month == 6 and arr.day == 12
    assert arr.hour == 3 and arr.minute == 30
    assert arr.tzinfo is not None


def test_status_preserved():
    ships = parse_arrivals(SAMPLE_HTML)
    assert ships[0]["status"] == "Fest"
    assert ships[1]["status"] == "Avisiert"
