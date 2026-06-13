# JadeWeserPort Schiffsankünfte API

FastAPI-Service, der die [Schiffsankünfte des JadeWeserPort](https://www.jadeweserport.de/schiff-schiene/schiffsankuenfte-jadeweserport/)
per HTTP (`httpx` + `BeautifulSoup`) scrapt und liefert:

- **Schiffe, die aktuell am Hafen liegen** (Status `Fest`)
- **Schiffe, die in den nächsten 24 Stunden ankommen**

Die Seite rendert die Tabelle serverseitig, daher genügt ein einfacher
HTTP-Request – kein Browser nötig.

Es wird **keine Datenbank** verwendet – gescrapt wird bei Bedarf. Ein kurzer
In-Memory-Cache (Standard 60 s) verhindert lediglich einen HTTP-Request bei
jedem einzelnen Aufruf.

## Endpunkte

| Methode | Pfad               | Beschreibung                                            |
|---------|--------------------|---------------------------------------------------------|
| GET     | `/ships`           | Beides: Schiffe am Hafen **und** Ankünfte der nächsten 24 h |
| GET     | `/ships/at-port`   | Nur Schiffe am Hafen (Status `Fest`)                    |
| GET     | `/ships/at-port-dakboardOutput` | Schiffe am Hafen im [DAKboard](https://dakboard.com)-Array-Format (`value`/`title`/`subtitle`) |
| GET     | `/ships/arriving`  | Nur Ankünfte der nächsten 24 h                          |
| GET     | `/schmutzwassereinleitung` | Datum/Uhrzeit der letzten Mischwassereinleitung (Banter Siel, Wilhelmshaven) |
| GET     | `/health`          | Healthcheck (für Railway)                               |
| GET     | `/docs`            | OpenAPI / Swagger UI                                    |

### Beispielantwort `/ships`

```json
{
  "scraped_at": "2026-06-13T16:29:14+02:00",
  "source": "https://www.jadeweserport.de/schiff-schiene/schiffsankuenfte-jadeweserport/",
  "window_hours": 24,
  "at_port": [
    {
      "name": "Maersk Virginia",
      "line": "PGS",
      "arrival": "2026-06-12T03:30:00+02:00",
      "departure": "2026-06-13T23:59:00+02:00",
      "arrival_raw": "12.06.2026 03:30",
      "departure_raw": "13.06.2026 23:59",
      "tdw": 65433,
      "status": "Fest"
    }
  ],
  "arriving_next_24h": [
    {
      "name": "GSL Tegea",
      "line": "AL4",
      "arrival": "2026-06-14T01:30:00+02:00",
      "departure": "2026-06-15T20:00:00+02:00",
      "arrival_raw": "14.06.2026 01:30",
      "departure_raw": "15.06.2026 20:00",
      "tdw": 68131,
      "status": "Avisiert"
    }
  ]
}
```

### Beispielantwort `/ships/at-port-dakboardOutput`

Top-Level-Array im von DAKboard erwarteten Format (`value` Pflicht, `title`/`subtitle` optional):

```json
[
  {
    "value": "Maersk Virginia",
    "title": "PGS",
    "subtitle": "Ankunft 12.06.2026 03:30 · Abfahrt 13.06.2026 23:59"
  }
]
```

### Beispielantwort `/schmutzwassereinleitung`

```json
{
  "datum": "2026-06-13",
  "uhrzeit": "14:26",
  "status": "rot",
  "zeitpunkt": "2026-06-13T14:26:00+02:00",
  "datum_raw": 13312,
  "uhrzeit_raw": 48363958,
  "scraped_at": "2026-06-13T23:34:19+02:00",
  "source": "http://93.240.84.156/webMI/"
}
```

`status` ist eine Bade-Ampel: **`rot`**, wenn die letzte Einleitung weniger als
24 h her ist (Baden eher nicht ratsam), sonst **`grün`**. Die Schwelle ist über
`JWP_WODE_AMPEL_HOURS` konfigurierbar; der Status wird bei jedem Abruf frisch
berechnet.

Quelle ist ein atvise/webMI-SCADA-System (Siemens-S7-SPS). Der Handshake
(RSA-Session + MD5-Digests) wird in reinem Python nachgebaut – **kein Browser
nötig**. Die Rohwerte sind S7-Typen: `datum_raw` = Tage seit 1990-01-01,
`uhrzeit_raw` = Millisekunden seit Mitternacht. Die Uhrzeit spiegelt bewusst die
Anzeige der Originalseite (deren JS rechnet via `new Date(ms)` konstant +1 h).

## Lokal ausführen

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

uvicorn app.main:app --reload
```

Dann: <http://127.0.0.1:8000/docs>

### Tests

```powershell
pip install pytest
pytest -q
```

Die Tests prüfen den HTML-Parser isoliert (ohne Netzwerk).

## Deployment auf Railway

Das Projekt enthält ein schlankes `Dockerfile` (Basis `python:3.12-slim`) und
eine `railway.json`. Railway baut automatisch über das Dockerfile.

1. Repository nach GitHub pushen.
2. In Railway: **New Project → Deploy from GitHub repo**.
3. Railway erkennt das `Dockerfile` und baut das Image.
4. Der Service lauscht auf `$PORT` (von Railway gesetzt). Healthcheck: `/health`.

Alternativ via CLI:

```bash
railway up
```

## Konfiguration (Environment-Variablen)

| Variable                   | Default                              | Beschreibung                                  |
|----------------------------|--------------------------------------|-----------------------------------------------|
| `JWP_SOURCE_URL`           | JadeWeserPort-URL                    | Zu scrapende Seite                            |
| `JWP_TIMEZONE`             | `Europe/Berlin`                      | Zeitzone der angezeigten Zeiten               |
| `JWP_ARRIVAL_WINDOW_HOURS` | `24`                                 | Zeitfenster für "ankommende Schiffe"          |
| `JWP_AT_PORT_STATUS`       | `fest`                               | Status, der "liegt am Hafen" bedeutet         |
| `JWP_CACHE_TTL_SECONDS`    | `60`                                 | Cache-TTL in Sekunden (`0` = aus)             |
| `JWP_HTTP_TIMEOUT_SECONDS` | `20`                                 | Timeout für den HTTP-Request (Sekunden)       |
| `JWP_USER_AGENT`           | Chrome-UA                            | User-Agent für den HTTP-Request               |
| `JWP_WODE_URL`             | atvise-webMI-URL                     | Daten-Endpunkt der Mischwassereinleitung      |
| `JWP_WODE_ADDR_DATE`       | S7-Knotenadresse                     | OPC-UA-Adresse des Datums-Knotens             |
| `JWP_WODE_ADDR_TIME`       | S7-Knotenadresse                     | OPC-UA-Adresse des Uhrzeit-Knotens            |
| `JWP_WODE_AMPEL_HOURS`     | `24`                                 | Schwelle für die Bade-Ampel (rot/grün) in h   |

## Hinweise

- Die Quelle weist darauf hin, dass die Daten **ohne Gewähr** und Änderungen
  vorbehalten sind.
- `arrival`/`departure` sind ISO-8601 mit Zeitzone; `*_raw` enthält den
  Originaltext der Seite.
```
