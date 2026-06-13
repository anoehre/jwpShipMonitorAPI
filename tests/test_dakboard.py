"""Tests für das DAKboard-Array-Mapping."""
from app.main import _to_dakboard
from app.models import Ship


def _ship(**kw):
    base = dict(name="Maersk Virginia", line="PGS", status="Fest",
               arrival_raw="12.06.2026 03:30", departure_raw="13.06.2026 23:59")
    base.update(kw)
    return Ship(**base)


def test_value_is_ship_name():
    items = _to_dakboard([_ship()])
    assert items[0].value == "Maersk Virginia"


def test_title_is_line():
    items = _to_dakboard([_ship(line="SB1")])
    assert items[0].title == "SB1"


def test_subtitle_contains_arrival_and_departure():
    items = _to_dakboard([_ship()])
    assert items[0].subtitle == "Ankunft 12.06.2026 03:30 · Abfahrt 13.06.2026 23:59"


def test_missing_times_omit_subtitle():
    items = _to_dakboard([_ship(arrival_raw=None, departure_raw=None)])
    assert items[0].subtitle is None


def test_empty_input_yields_empty_list():
    assert _to_dakboard([]) == []
