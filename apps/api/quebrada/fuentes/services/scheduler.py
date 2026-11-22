"""Bucle asyncio que sincroniza cada fuente según su intervalo."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from quebrada.fuentes.config import AUTO_HABILITADO, intervalo_fuente
from quebrada.fuentes.models import FuenteId
from quebrada.fuentes.services.fuentes_service import FuentesService

log = logging.getLogger("quebrada.fuentes")


class FuentesScheduler:
    def __init__(self, service: FuentesService, habilitado: bool = AUTO_HABILITADO):
        self.service = service
        self.habilitado = habilitado
        self._tarea: asyncio.Task | None = None
        self._ultima: dict[FuenteId, datetime] = {}

    def iniciar(self) -> None:
        if not self.habilitado or self._tarea is not None:
            return
        self._tarea = asyncio.create_task(self._ciclo(), name="fuentes-scheduler")

    async def detener(self) -> None:
        if self._tarea is None:
            return
        self._tarea.cancel()
        try:
            await self._tarea
        except asyncio.CancelledError:
            pass
        self._tarea = None

    async def _ciclo(self) -> None:
        # Primera pasada al arrancar para poblar la base cuanto antes.
        await self._correr_pendientes(forzar=True)
        while True:
            await asyncio.sleep(30)
            await self._correr_pendientes(forzar=False)

    async def _correr_pendientes(self, forzar: bool) -> None:
        ahora = datetime.now(timezone.utc)
        for fuente in FuenteId:
            ultima = self._ultima.get(fuente)
            vencido = ultima is None or (ahora - ultima).total_seconds() >= intervalo_fuente(fuente)
            if not forzar and not vencido:
                continue
            try:
                resultado = await self.service.sincronizar(fuente)
                self._ultima[fuente] = ahora
                estado = resultado[0].estado if resultado else "?"
                log.info("fuente %s sincronizada: %s", fuente.value, estado)
            except Exception:  # noqa: BLE001
                log.exception("falló la sincronización de %s", fuente.value)
