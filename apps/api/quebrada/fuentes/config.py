"""Catálogo de fuentes y estaciones a sincronizar (docs/fuentes_datos_quebrada_alert.md)."""

from __future__ import annotations

import os
from dataclasses import dataclass

from quebrada.fuentes.models import FuenteId


@dataclass(frozen=True)
class EstacionExterna:
    estacion_id: str
    nombre: str
    lat: float
    lon: float
    fuente: FuenteId
    # Código SNIH de precipitación acumulada (MuestraDatos.js: precipitacion = 20).
    codigo_variable: str | None = None
    variable: str = "precipitacion_mm"


# Pluviómetros SNIH de referencia (no están en cabecera; no se mezclan con nodos simulados).
ESTACIONES_SNIH: tuple[EstacionExterna, ...] = (
    EstacionExterna(
        estacion_id="280049",
        nombre="Volcán (SNIH)",
        lat=-23.9171,
        lon=-65.4640,
        fuente=FuenteId.SNIH,
        codigo_variable="20",
    ),
    EstacionExterna(
        estacion_id="10040",
        nombre="Humahuaca Esc. Agrotécnica 3 (SNIH)",
        lat=-23.2054,
        lon=-65.3495,
        fuente=FuenteId.SNIH,
        codigo_variable="20",
    ),
)

# Cuatro puntos de cabecera para Open-Meteo (ERA5 / pronóstico).
ESTACIONES_OPEN_METEO: tuple[EstacionExterna, ...] = (
    EstacionExterna("EST-VOLCAN-CAB01", "Cabecera Volcán", -23.94457, -65.51103, FuenteId.OPEN_METEO_FORECAST),
    EstacionExterna("EST-TUMBAYA-CAB01", "Cabecera Tumbaya", -23.82764, -65.58301, FuenteId.OPEN_METEO_FORECAST),
    EstacionExterna("EST-PURMAMARCA-CAB01", "Cabecera Purmamarca", -23.66519, -65.5802, FuenteId.OPEN_METEO_FORECAST),
    EstacionExterna("EST-TILCARA-CAB01", "Cabecera Tilcara", -23.58151, -65.32926, FuenteId.OPEN_METEO_FORECAST),
)

SNIH_BASE = os.environ.get("QUEBRADA_SNIH_BASE", "https://snih.hidricosargentina.gob.ar")
OPEN_METEO_FORECAST_URL = os.environ.get("QUEBRADA_OPEN_METEO_FORECAST_URL", "https://api.open-meteo.com/v1/forecast")
OPEN_METEO_ARCHIVE_URL = os.environ.get(
    "QUEBRADA_OPEN_METEO_ARCHIVE_URL", "https://archive-api.open-meteo.com/v1/archive"
)

# Intervalos por defecto (segundos). Overridables por entorno.
INTERVALO_SNIH_S = int(os.environ.get("QUEBRADA_FUENTES_SNIH_INTERVAL_S", "3600"))
INTERVALO_OPEN_METEO_S = int(os.environ.get("QUEBRADA_FUENTES_OPEN_METEO_INTERVAL_S", "1800"))
DIAS_SNIH = int(os.environ.get("QUEBRADA_FUENTES_SNIH_DIAS", "7"))
DIAS_ARCHIVE = int(os.environ.get("QUEBRADA_FUENTES_ARCHIVE_DIAS", "3"))
AUTO_HABILITADO = os.environ.get("QUEBRADA_FUENTES_AUTO", "1") not in ("0", "false", "False")


def intervalo_fuente(fuente: FuenteId) -> int:
    if fuente is FuenteId.SNIH:
        return INTERVALO_SNIH_S
    return INTERVALO_OPEN_METEO_S
