# Offizielles Playwright-Python-Image: Browser + Systemabhängigkeiten sind
# bereits vorinstalliert. Version muss zu playwright in requirements.txt passen.
FROM mcr.microsoft.com/playwright/python:v1.49.1-noble

WORKDIR /app

# Abhängigkeiten zuerst (besseres Layer-Caching).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sicherstellen, dass der Chromium-Browser vorhanden ist (idempotent).
RUN playwright install chromium

COPY app ./app

ENV PYTHONUNBUFFERED=1
# Railway stellt $PORT bereit; lokal 8000 als Fallback.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
