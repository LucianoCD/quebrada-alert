"""Endpoints REST de fuentes externas (capa controller)."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from quebrada.fuentes.models import FuenteId


def crear_router() -> APIRouter:
    router = APIRouter(prefix="/api/fuentes", tags=["fuentes"])

    def service(request: Request):
        svc = getattr(request.app.state, "fuentes", None)
        if svc is None:
            raise HTTPException(503, "Servicio de fuentes no inicializado")
        return svc

    @router.get("")
    async def listar(request: Request) -> dict:
        svc = service(request)
        return {
            "fuentes": [f.model_dump(mode="json") for f in svc.listar_fuentes()],
            "lecturas_totales": svc.repo.contar_lecturas(),
        }

    @router.post("/sincronizar")
    async def sincronizar(request: Request, fuente: FuenteId | None = None) -> dict:
        """Si `fuente` se omite, sincroniza todas las fuentes configuradas."""
        resultados = await service(request).sincronizar(fuente)
        return {"resultados": [r.model_dump(mode="json") for r in resultados]}

    @router.get("/sincronizaciones")
    async def sincronizaciones(request: Request, limite: int = 50) -> dict:
        limite = min(max(limite, 1), 500)
        return {"sincronizaciones": [r.model_dump(mode="json") for r in service(request).sincronizaciones(limite)]}

    @router.get("/lecturas")
    async def lecturas(
        request: Request,
        fuente: FuenteId | None = None,
        estacion_id: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        limite: int = 500,
    ) -> dict:
        limite = min(max(limite, 1), 5000)
        return {
            "lecturas": service(request).lecturas(
                fuente=fuente,
                estacion_id=estacion_id,
                desde=desde,
                hasta=hasta,
                limite=limite,
            )
        }

    @router.get("/{fuente}/lecturas")
    async def lecturas_fuente(
        request: Request,
        fuente: FuenteId,
        estacion_id: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        limite: int = 500,
    ) -> dict:
        limite = min(max(limite, 1), 5000)
        return {
            "fuente": fuente.value,
            "lecturas": service(request).lecturas(
                fuente=fuente,
                estacion_id=estacion_id,
                desde=desde,
                hasta=hasta,
                limite=limite,
            ),
        }

    return router
