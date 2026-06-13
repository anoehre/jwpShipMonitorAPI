"""Configuration via environment variables (Railway-friendly)."""
import os

# URL der zu scrapenden Seite
SOURCE_URL = os.getenv(
    "JWP_SOURCE_URL",
    "https://www.jadeweserport.de/schiff-schiene/schiffsankuenfte-jadeweserport/",
)

# Zeitzone der auf der Webseite angegebenen Zeiten
TIMEZONE = os.getenv("JWP_TIMEZONE", "Europe/Berlin")

# Zeitfenster (Stunden) für "ankommende Schiffe"
ARRIVAL_WINDOW_HOURS = int(os.getenv("JWP_ARRIVAL_WINDOW_HOURS", "24"))

# Status-Wert der Schiffe, die aktuell am Hafen liegen
AT_PORT_STATUS = os.getenv("JWP_AT_PORT_STATUS", "fest").lower()

# In-Memory-Cache: TTL in Sekunden (0 = deaktiviert). Verhindert einen
# HTTP-Request bei jedem einzelnen Aufruf, ohne eine DB zu benötigen.
CACHE_TTL_SECONDS = int(os.getenv("JWP_CACHE_TTL_SECONDS", "60"))

# Timeout für den HTTP-Request in Sekunden
HTTP_TIMEOUT_SECONDS = float(os.getenv("JWP_HTTP_TIMEOUT_SECONDS", "20"))

# User-Agent für den HTTP-Request
USER_AGENT = os.getenv(
    "JWP_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
)
