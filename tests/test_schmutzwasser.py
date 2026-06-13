"""Tests für die S7-Wert-Dekodierung der Mischwassereinleitung."""
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.schmutzwasser import (
    _decode_date,
    _decode_time,
    _rsa_pkcs1v15_encrypt,
    ampel_status,
)

TZ = ZoneInfo("Europe/Berlin")


def test_decode_date_epoch():
    assert _decode_date(0) == date(1990, 1, 1)


def test_decode_date_known_value():
    # 13312 Tage seit 1990-01-01 -> 13.06.2026 (live verifiziert)
    assert _decode_date(13312) == date(2026, 6, 13)


def test_decode_time_known_value_matches_display():
    # 48363958 ms -> Rohzeit 13:26, Anzeige der Quellseite 14:26 (+1h via new Date)
    t = _decode_time(48363958, TZ)
    assert (t.hour, t.minute) == (14, 26)


def test_decode_time_midnight_has_plus_one_offset():
    # 0 ms -> 1970-01-01 00:00 UTC -> Europe/Berlin 01:00 (konstanter +1h-Versatz)
    t = _decode_time(0, TZ)
    assert t.hour == 1


def test_ampel_rot_wenn_juenger_als_24h():
    now = datetime(2026, 6, 13, 12, 0, tzinfo=TZ)
    event = now - timedelta(hours=5)
    assert ampel_status(event, now, 24) == "rot"


def test_ampel_gruen_wenn_aelter_als_24h():
    now = datetime(2026, 6, 13, 12, 0, tzinfo=TZ)
    event = now - timedelta(hours=30)
    assert ampel_status(event, now, 24) == "grün"


def test_ampel_grenze_genau_24h_ist_gruen():
    now = datetime(2026, 6, 13, 12, 0, tzinfo=TZ)
    event = now - timedelta(hours=24)
    assert ampel_status(event, now, 24) == "grün"


def test_ampel_zukunft_ist_rot():
    now = datetime(2026, 6, 13, 12, 0, tzinfo=TZ)
    event = now + timedelta(hours=1)
    assert ampel_status(event, now, 24) == "rot"


def test_rsa_output_is_even_length_hex():
    # 1024-bit Beispielmodulus, Exponent 65537; Ausgabe muss gültiges Hex sein.
    n = (1 << 1023) | 1  # ungerade, 1024 bit
    e = 65537
    h = _rsa_pkcs1v15_encrypt(b"hallo", n, e)
    assert len(h) % 2 == 0
    int(h, 16)  # parst als Hex
