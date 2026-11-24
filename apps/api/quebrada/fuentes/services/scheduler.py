"""Bucle asyncio que sincroniza cada fuente según su intervalo."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from quebrada.fuentes.config import AUTO_HABILITADO, intervalo_fuente
from quebrada.fuentes.models import FuenteId
from quebrada.fuentes.services.fuentes_service import FuentesService

log = logging.getLogger("quebrada.fuentes")


class FuentesScheduler:
    def __init__(
        self,
        service: FuentesService,
        habilitado: bool = AUTO_HABILITADO,
        reloj: Callable[[], datetime] | None = None,
    ):
        self.service = service
        self.habilitado = habilitado
        self._reloj = reloj or (lambda: datetime.now(timezone.utc))
        self._tarea: asyncio.Task | None = None
        self._ultima: dict[FuenteId, datetime] = {}
        self._fallos: dict[FuenteId, int] = {}
        self._siguiente_reintento: dict[FuenteId, datetime] = {}

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

    def _registrar_fallo(self, fuente: FuenteId, ahora: datetime) -> None:
        fallos = self._fallos.get(fuente, 0) + 1
        self._fallos[fuente] = fallos
        espera_s = min(30 * (2 ** (fallos - 1)), intervalo_fuente(fuente))
        self._siguiente_reintento[fuente] = ahora + timedelta(seconds=espera_s)

    async def _correr_pendientes(self, forzar: bool) -> None:
        ahora = self._reloj()
        for fuente in FuenteId:
            if not forzar:
                proximo = self._siguiente_reintento.get(fuente)
                if proximo is not None and ahora < proximo:
                    continue
                ultima = self._ultima.get(fuente)
                vencido = ultima is None or (ahora - ultima).total_seconds() >= intervalo_fuente(fuente)
                if not vencido:
                    continue
            try:
                resultado = await self.service.sincronizar(fuente)
                estado = resultado[0].estado if resultado else "?"
                if estado == "ok":
                    self._ultima[fuente] = ahora
                    self._fallos.pop(fuente, None)
                    self._siguiente_reintento.pop(fuente, None)
                else:
                    self._registrar_fallo(fuente, ahora)
                log.info("fuente %s sincronizada: %s", fuente.value, estado)
            except Exception:  # noqa: BLE001
                self._registrar_fallo(fuente, ahora)
                log.exception("falló la sincronización de %s", fuente.value)
