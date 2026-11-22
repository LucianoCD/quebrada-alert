"""DTOs de la capa de fuentes externas."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FuenteId(str, Enum):
    SNIH = "snih"
    OPEN_METEO_FORECAST = "open_meteo_forecast"
    OPEN_METEO_ARCHIVE = "open_meteo_archive"


class OrigenLectura(str, Enum):
    OBSERVADO = "OBSERVADO"
    PRONOSTICO = "PRONOSTICO"
    REANALISIS = "REANALISIS"


class LecturaExterna(BaseModel):
    fuente: FuenteId
    estacion_id: str
    variable: str
    ts: datetime
    valor: float
    unidad: str = "mm"
    origen: OrigenLectura
    lat: float | None = None
    lon: float | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class ResultadoSincronizacion(BaseModel):
    fuente: FuenteId
    estado: str  # ok | error | parcial
    nuevas: int = 0
    repetidas: int = 0
    detalle: str = ""
    iniciado: datetime | None = None
    finalizado: datetime | None = None


class FuenteEstado(BaseModel):
    id: FuenteId
    nombre: str
    descripcion: str
    intervalo_s: int
    habilitada: bool
    ultima: ResultadoSincronizacion | None = None
