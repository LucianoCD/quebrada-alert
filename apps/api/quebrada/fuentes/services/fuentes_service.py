"""Orquestación de obtención + persistencia de fuentes externas."""

from __future__ import annotations

from datetime import datetime, timezone

import duckdb
import httpx

from quebrada.fuentes.clients.open_meteo import OpenMeteoClient
from quebrada.fuentes.clients.snih import SnihClient
from quebrada.fuentes.config import intervalo_fuente
from quebrada.fuentes.models import FuenteEstado, FuenteId, ResultadoSincronizacion
from quebrada.fuentes.repositories.fuentes_repository import FuentesRepository

CATALOGO = {
    FuenteId.SNIH: (
        "SNIH — lluvia observada",
        "Estaciones 280049 (Volcán) y 10040 (Humahuaca). Capa de referencia, no dispara alertas.",
    ),
    FuenteId.OPEN_METEO_FORECAST: (
        "Open-Meteo — pronóstico",
        "Precipitación horaria en las 4 cabeceras (plan gratuito no comercial).",
    ),
    FuenteId.OPEN_METEO_ARCHIVE: (
        "Open-Meteo — archivo ERA5",
        "Reanálisis horario reciente en las 4 cabeceras para clima base.",
    ),
}


class FuentesService:
    def __init__(self, db: duckdb.DuckDBPyConnection, cliente: httpx.AsyncClient | None = None):
        self.repo = FuentesRepository(db)
        self._cliente = cliente

    def listar_fuentes(self) -> list[FuenteEstado]:
        salida = []
        for fuente, (nombre, descripcion) in CATALOGO.items():
            salida.append(
                FuenteEstado(
                    id=fuente,
                    nombre=nombre,
                    descripcion=descripcion,
                    intervalo_s=intervalo_fuente(fuente),
                    habilitada=True,
                    ultima=self.repo.ultima_sincronizacion(fuente),
                )
            )
        return salida

    async def sincronizar(self, fuente: FuenteId | None = None) -> list[ResultadoSincronizacion]:
        objetivos = [fuente] if fuente is not None else list(FuenteId)
        return [await self._una(f) for f in objetivos]

    async def _una(self, fuente: FuenteId) -> ResultadoSincronizacion:
        iniciado = datetime.now(timezone.utc)
        try:
            if fuente is FuenteId.SNIH:
                async with SnihClient(cliente=self._cliente) as cliente:
                    lecturas = await cliente.obtener_lecturas()
            elif fuente is FuenteId.OPEN_METEO_FORECAST:
                async with OpenMeteoClient(cliente=self._cliente) as cliente:
                    lecturas = await cliente.obtener_pronostico()
            elif fuente is FuenteId.OPEN_METEO_ARCHIVE:
                async with OpenMeteoClient(cliente=self._cliente) as cliente:
                    lecturas = await cliente.obtener_archivo()
            else:
                raise ValueError(f"Fuente no soportada: {fuente}")
            nuevas, repetidas = self.repo.guardar_lecturas(lecturas)
            resultado = ResultadoSincronizacion(
                fuente=fuente,
                estado="ok",
                nuevas=nuevas,
                repetidas=repetidas,
                detalle=f"{len(lecturas)} lecturas recibidas",
                iniciado=iniciado,
                finalizado=datetime.now(timezone.utc),
            )
        except Exception as error:  # noqa: BLE001 — se registra y no tumba el scheduler
            resultado = ResultadoSincronizacion(
                fuente=fuente,
                estado="error",
                nuevas=0,
                repetidas=0,
                detalle=f"{type(error).__name__}: {error}" if str(error) else type(error).__name__,
                iniciado=iniciado,
                finalizado=datetime.now(timezone.utc),
            )
        return self.repo.registrar_sincronizacion(resultado)

    def lecturas(self, **kwargs) -> list[dict]:
        return self.repo.listar_lecturas(**kwargs)

    def sincronizaciones(self, limite: int = 50) -> list[ResultadoSincronizacion]:
        return self.repo.listar_sincronizaciones(limite)
