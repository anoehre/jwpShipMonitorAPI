"""Pydantic-Modelle für die API-Antworten."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Ship(BaseModel):
    """Ein einzelner Schiffseintrag aus der Schiffsankünfte-Tabelle."""

    name: str = Field(..., description="Schiffsname", examples=["Maersk Virginia"])
    line: Optional[str] = Field(
        None, description="Liniendienst / Service (Klammerzusatz)", examples=["PGS"]
    )
    arrival: Optional[datetime] = Field(
        None, description="Ankunftszeit (ISO 8601, mit Zeitzone)"
    )
    departure: Optional[datetime] = Field(
        None, description="Abfahrtszeit (ISO 8601, mit Zeitzone)"
    )
    arrival_raw: Optional[str] = Field(
        None, description="Ankunftszeit wie auf der Seite angezeigt"
    )
    departure_raw: Optional[str] = Field(
        None, description="Abfahrtszeit wie auf der Seite angezeigt"
    )
    tdw: Optional[int] = Field(
        None, description="Tragfähigkeit (deadweight tonnage)", examples=[65433]
    )
    status: str = Field(..., description="Status, z. B. 'Fest' oder 'Avisiert'")


class ShipsResponse(BaseModel):
    """Antwort des Haupt-Endpunkts."""

    scraped_at: datetime = Field(..., description="Zeitpunkt des Scrapens")
    source: str = Field(..., description="Quell-URL")
    window_hours: int = Field(..., description="Zeitfenster für Ankünfte in Stunden")
    at_port: List[Ship] = Field(
        ..., description="Schiffe, die aktuell am Hafen liegen (Status 'Fest')"
    )
    arriving_next_24h: List[Ship] = Field(
        ..., description="Schiffe, die innerhalb des Zeitfensters ankommen"
    )


class HealthResponse(BaseModel):
    status: str
    browser_ready: bool
