"""Cliente Open-Meteo: pronóstico horario y archivo ERA5 (uso no comercial del plan gratuito)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import httpx

from quebrada.fuentes.config import (
    DIAS_ARCHIVE,
    ESTACIONES_OPEN_METEO,
    OPEN_METEO_ARCHIVE_URL,
    OPEN_METEO_FORECAST_URL,
    EstacionExterna,
)
from quebrada.fuentes.models import FuenteId, LecturaExterna, OrigenLectura


def _pares_horario(payload: dict) -> list[tuple[datetime, float]]:
    horario = payload.get("hourly") or {}
    tiempos = horario.get("time") or []
    valores = horario.get("precipitation") or []
    salida = []
    for ts, valor in zip(tiempos, valores, strict=False):
        if valor is None:
            continue
        momento = datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)
        salida.append((momento, float(valor)))
    return salida


class OpenMeteoClient:
    def __init__(
        self,
        forecast_url: str = OPEN_METEO_FORECAST_URL,
        archive_url: str = OPEN_METEO_ARCHIVE_URL,
        cliente: httpx.AsyncClient | None = None,
    ):
        self.forecast_url = forecast_url
        self.archive_url = archive_url
        self._cliente = cliente
        self._propio = cliente is None

    async def __aenter__(self) -> OpenMeteoClient:
        if self._cliente is None:
            self._cliente = httpx.AsyncClient(timeout=60.0, follow_redirects=True)
            self._propio = True
        return self

    async def __aexit__(self, *_) -> None:
        if self._propio and self._cliente is not None:
            await self._cliente.aclose()
            self._cliente = None

    async def _punto(self, url: str, est: EstacionExterna, params: dict) -> list[LecturaExterna]:
        assert self._cliente is not None
        r = await self._cliente.get(
            url,
            params={
                "latitude": est.lat,
                "longitude": est.lon,
                "hourly": "precipitation",
                "timezone": "UTC",
                **params,
            },
        )
        r.raise_for_status()
        fuente = FuenteId.OPEN_METEO_FORECAST if "forecast" in url else FuenteId.OPEN_METEO_ARCHIVE
        origen = OrigenLectura.PRONOSTICO if fuente is FuenteId.OPEN_METEO_FORECAST else OrigenLectura.REANALISIS
        # El endpoint forecast mezcla pasado reciente + futuro; etiquetamos todo como PRONOSTICO/modelo.
        if "past_days" in params:
            origen = OrigenLectura.PRONOSTICO
        lecturas = []
        for ts, valor in _pares_horario(r.json()):
            lecturas.append(
                LecturaExterna(
                    fuente=fuente,
                    estacion_id=est.estacion_id,
                    variable=est.variable,
                    ts=ts,
                    valor=valor,
                    unidad="mm",
                    origen=origen,
                    lat=est.lat,
                    lon=est.lon,
                    meta={"nombre": est.nombre, "proveedor": "open-meteo"},
                )
            )
        return lecturas

    async def obtener_pronostico(
        self,
        estaciones: tuple[EstacionExterna, ...] = ESTACIONES_OPEN_METEO,
        past_days: int = 1,
        forecast_days: int = 2,
    ) -> list[LecturaExterna]:
        salida: list[LecturaExterna] = []
        for est in estaciones:
            bloque = await self._punto(
                self.forecast_url,
                est,
                {"past_days": past_days, "forecast_days": forecast_days},
            )
            for lectura in bloque:
                lectura.fuente = FuenteId.OPEN_METEO_FORECAST
            salida.extend(bloque)
        return salida

    async def obtener_archivo(
        self,
        estaciones: tuple[EstacionExterna, ...] = ESTACIONES_OPEN_METEO,
        dias: int = DIAS_ARCHIVE,
    ) -> list[LecturaExterna]:
        hasta = date.today() - timedelta(days=1)
        desde = hasta - timedelta(days=max(1, dias) - 1)
        salida: list[LecturaExterna] = []
        for est in estaciones:
            bloque = await self._punto(
                self.archive_url,
                est,
                {"start_date": desde.isoformat(), "end_date": hasta.isoformat()},
            )
            for lectura in bloque:
                lectura.fuente = FuenteId.OPEN_METEO_ARCHIVE
                lectura.origen = OrigenLectura.REANALISIS
            salida.extend(bloque)
        return salida
