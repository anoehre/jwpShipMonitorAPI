"""Auslesen der 'Letzten Mischwassereinleitung' (Banter Siel, Wilhelmshaven).

Die Quellseite ist ein atvise/webMI-SCADA-System (Hilscher GmbH), das die Werte
einer Siemens-S7-SPS über ein eigenes HTTP-POST-Protokoll liefert. Wir bauen den
Handshake in reinem Python nach (kein Browser):

    POST ?info            -> RSA-Public-Key
    POST ?createsession   -> sessionid           (cipher = RSA-PKCS1v15(salt))
    POST ?createsubscription
    POST ?subscribedata   -> die zwei Knoten
    POST ?publish         -> aktuelle Werte
    POST ?deletesession   -> aufräumen (best effort)

Folge-Requests authentifizieren per X-WebMI-Header: digest = MD5(sessionid:salt:cnonce).

Werte-Kodierung (Siemens S7):
    Datum   = S7 DATE: Tage seit 1990-01-01
    Uhrzeit = S7 TIME_OF_DAY: Millisekunden seit Mitternacht

Hinweis Uhrzeit: Die Quellseite rendert die Stunde via `new Date(ms).getHours()`,
interpretiert die Millisekunden also als Unix-Zeitstempel (1970-01-01) und zeigt
sie in lokaler Zeit. Am 01.01.1970 ist Europe/Berlin = UTC+1, daher zeigt die
Seite konstant `Rohwert + 1 Stunde`. Wir spiegeln dieses Verhalten, damit unsere
Ausgabe der offiziellen Anzeige entspricht.
"""
import hashlib
import secrets
import string
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx

from . import config

_SALT_ALPHABET = string.ascii_letters + string.digits + "+/"


def _rsa_pkcs1v15_encrypt(msg: bytes, n: int, e: int) -> str:
    """RSA-Verschlüsselung mit PKCS#1 v1.5 (Typ 2), Ausgabe als Hex-String."""
    k = (n.bit_length() + 7) // 8
    if len(msg) > k - 11:
        raise ValueError("message too long for RSA key")
    ps = bytes(secrets.choice(range(1, 256)) for _ in range(k - len(msg) - 3))
    em = b"\x00\x02" + ps + b"\x00" + msg
    c = pow(int.from_bytes(em, "big"), e, n)
    h = format(c, "x")
    return ("0" + h) if len(h) % 2 else h


def ampel_status(zeitpunkt: datetime, now: datetime, threshold_hours: int) -> str:
    """Bade-Ampel: 'rot' wenn die Einleitung jünger als `threshold_hours` ist,
    sonst 'grün'. (< Schwelle = rot, >= Schwelle = grün)."""
    if now - zeitpunkt < timedelta(hours=threshold_hours):
        return "rot"
    return "grün"


def _decode_date(days: int) -> date:
    """S7 DATE -> Kalenderdatum (Tage seit 1990-01-01)."""
    return date(1990, 1, 1) + timedelta(days=days)


def _decode_time(tod_ms: int, tz: ZoneInfo) -> datetime:
    """S7 TIME_OF_DAY (ms) -> Zeit, wie sie die Quellseite anzeigt.

    Repliziert `new Date(ms)` (ms als Unix-Epoch interpretiert) und die Anzeige
    in lokaler Zeit – dadurch derselbe +1h-Versatz wie auf der Originalseite.
    """
    dt_utc = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=tod_ms)
    return dt_utc.astimezone(tz)


async def fetch_letzte_einleitung(client: httpx.AsyncClient) -> dict:
    """Liest Datum und Uhrzeit der letzten Mischwassereinleitung."""
    base = config.WODE_URL

    # 1) Server-Info / Public Key
    info = (await client.post(base + "?info")).json()
    n = int(info["encryptionmodulus"], 16)
    e = int(info["encryptionexponent"], 16)

    # 2) Session anlegen (cipher = RSA(salt))
    salt = "".join(secrets.choice(_SALT_ALPHABET) for _ in range(64))
    cipher = _rsa_pkcs1v15_encrypt(salt.encode("ascii"), n, e)
    sess = (await client.post(base + "?createsession", data={"cipher": cipher})).json()
    sid = sess.get("sessionid")
    if not sid:
        raise RuntimeError(f"Keine Session erhalten: {sess}")

    counter = {"z": 0}

    def auth_header() -> dict:
        counter["z"] += 1
        z = counter["z"]
        digest = hashlib.md5(f"{sid}:{salt}:{z}".encode()).hexdigest()
        return {"X-WebMI": f'sessionid="{sid}", cnonce="{z}", digest="{digest}"'}

    try:
        # 3) Subscription anlegen
        sub = (await client.post(base + "?createsubscription", headers=auth_header())).json()
        subid = sub.get("subscriptionid")

        # 4) Knoten abonnieren
        await client.post(
            base + "?subscribedata",
            data={"subscriptionid": subid, "address[]": [config.WODE_ADDR_TIME, config.WODE_ADDR_DATE]},
            headers=auth_header(),
        )

        # 5) Werte abholen
        pub = (await client.post(base + "?publish", headers=auth_header())).json()
    finally:
        # 6) Session schließen (best effort, Fehler ignorieren)
        try:
            await client.post(base + "?deletesession", headers=auth_header())
        except Exception:  # noqa: BLE001
            pass

    # Werte aus dem publish-Ergebnis nach Adresse herausfiltern
    date_val = time_val = None
    for item in pub.get("result", []):
        addr = item.get("address", "")
        if "Datum_letzte_Einleitung" in addr:
            date_val = item.get("value")
        elif "Uhrzeit_letzte_Einleitun" in addr:
            time_val = item.get("value")

    if date_val is None or time_val is None:
        raise RuntimeError(f"Werte nicht im publish-Ergebnis gefunden: {pub}")

    tz = ZoneInfo(config.TIMEZONE)
    d = _decode_date(int(date_val))
    t = _decode_time(int(time_val), tz)
    zeitpunkt = datetime(d.year, d.month, d.day, t.hour, t.minute, tzinfo=tz)

    return {
        "datum": d.isoformat(),
        "uhrzeit": f"{t.hour:02d}:{t.minute:02d}",
        "zeitpunkt": zeitpunkt,
        "datum_raw": int(date_val),
        "uhrzeit_raw": int(time_val),
    }
