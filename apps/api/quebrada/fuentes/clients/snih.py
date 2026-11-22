"""Cliente HTTP del SNIH (WebMethods ASP.NET documentados en el relevamiento de campo)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

import httpx

from quebrada.fuentes.config import DIAS_SNIH, ESTACIONES_SNIH, SNIH_BASE, EstacionExterna
from quebrada.fuentes.models import FuenteId, LecturaExterna, OrigenLectura

_MS_DATE = re.compile(r"/Date\((-?\d+)([+-]\d{4})?\)/")


def _parse_ms_date(valor: str | None) -> datetime | None:
    if not valor:
        return None
    m = _MS_DATE.fullmatch(str(valor).strip())
    if not m:
        return None
    return datetime.fromtimestamp(int(m.group(1)) / 1000.0, tz=timezone.utc)


class SnihClient:
    """Lluvia observada en estaciones telemétricas SNIH (capa de referencia)."""

    def __init__(self, base: str = SNIH_BASE, cliente: httpx.AsyncClient | None = None):
        self.base = base.rstrip("/")
        self._cliente = cliente
        self._propio = cliente is None

    async def __aenter__(self) -> SnihClient:
        if self._cliente is None:
            self._cliente = httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=120.0), follow_redirects=True)
            self._propio = True
        return self

    async def __aexit__(self, *_) -> None:
        if self._propio and self._cliente is not None:
            await self._cliente.aclose()
            self._cliente = None

    async def _post(self, ruta: str, cuerpo: dict | None = None) -> dict:
        assert self._cliente is not None
        r = await self._cliente.post(
            f"{self.base}/{ruta.lstrip('/')}",
            json=cuerpo or {},
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        r.raise_for_status()
        return r.json().get("d") or {}

    async def obtener_lecturas(
        self,
        estaciones: tuple[EstacionExterna, ...] = ESTACIONES_SNIH,
        dias: int = DIAS_SNIH,
    ) -> list[LecturaExterna]:
        hasta = date.today()
        desde = hasta - timedelta(days=max(1, dias))
        salida: list[LecturaExterna] = []
        for est in estaciones:
            if est.fuente is not FuenteId.SNIH:
                continue
            datos = await self._post(
                "MuestraDatos.aspx/LeerUltimosRegistros",
                {
                    "fechaDesde": desde.isoformat(),
                    "fechaHasta": hasta.isoformat(),
                    "estacion": est.estacion_id,
                    "codigo": est.codigo_variable or "20",
                },
            )
            if not datos.get("RespuestaOK", True):
                raise RuntimeError(f"SNIH {est.estacion_id}: {datos.get('MsgErr') or 'respuesta no OK'}")
            for fila in datos.get("Mediciones") or []:
                ts = _parse_ms_date(fila.get("FechaHora"))
                if ts is None:
                    continue
                mediciones = fila.get("Mediciones") or [fila]
                for med in mediciones:
                    if med.get("Codigo") not in (None, 20, "20") and "Codigo" in med:
                        if str(med.get("Codigo")) != str(est.codigo_variable or "20"):
                            continue
                    valor = med.get("Valor")
                    if valor is None:
                        continue
                    salida.append(
                        LecturaExterna(
                            fuente=FuenteId.SNIH,
                            estacion_id=est.estacion_id,
                            variable=est.variable,
                            ts=ts,
                            valor=float(valor),
                            unidad="mm",
                            origen=OrigenLectura.OBSERVADO,
                            lat=est.lat,
                            lon=est.lon,
                            meta={"nombre": est.nombre, "codigo_snih": est.codigo_variable or "20"},
                        )
                    )
        return salida
