"""Proceso de una estación simulada: un nodo, su SQLite y un puerto de control para la consola de crisis.

python -m quebrada.edge.proceso --node EST-VOLCAN-CAB01 --basin CUENCA_ARROYO_MEDIO --puerto 8101
"""

import argparse
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from quebrada.edge.escenarios import ESCENARIOS
from quebrada.edge.nodo import Nodo
from quebrada.hydrology import intervalo_muestreo_s
from quebrada.schemas import Nivel


class Orden(BaseModel):
    escenario: str | None = None
    enlace_activo: bool | None = None
    respaldo_activo: bool | None = None
    lluvia_previa_72h_mm: float | None = None


def crear_app(nodo: Nodo, escala: float) -> FastAPI:
    async def bucle() -> None:
        while True:
            lectura = await asyncio.to_thread(nodo.paso)
            await asyncio.sleep(intervalo_muestreo_s(lectura.edge_local_alert) / escala)

    @asynccontextmanager
    async def ciclo(_: FastAPI):
        tarea = asyncio.create_task(bucle())
        yield
        tarea.cancel()

    app = FastAPI(title=f"Nodo {nodo.node_id}", lifespan=ciclo)

    @app.get("/estado")
    def estado() -> dict:
        return nodo.resumen()

    @app.post("/control")
    def control(orden: Orden) -> dict:
        if orden.escenario is not None:
            if orden.escenario not in ESCENARIOS:
                raise HTTPException(422, f"Escenario desconocido: {orden.escenario}")
            nodo.estado.cambiar(orden.escenario, nodo.reloj.timestamp())
        if orden.enlace_activo is not None:
            nodo.enlace_activo = orden.enlace_activo
        if orden.respaldo_activo is not None:
            nodo.respaldo_activo = orden.respaldo_activo
        if orden.lluvia_previa_72h_mm is not None:
            nodo.estado.lluvia_previa_72h_mm = max(0.0, orden.lluvia_previa_72h_mm)
        return nodo.resumen()

    return app


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--node", required=True)
    p.add_argument("--basin", required=True)
    p.add_argument("--puerto", type=int, required=True)
    p.add_argument("--backend", default="http://127.0.0.1:8000")
    p.add_argument("--escala", type=float, default=60.0, help="segundos simulados por segundo real")
    p.add_argument("--dir", default="var", help="carpeta del SQLite del nodo")
    a = p.parse_args()

    cliente = httpx.Client(timeout=2.0)

    def enviar(ruta: str):
        def f(mensajes: list[dict]) -> bool:
            return cliente.post(f"{a.backend}{ruta}", json=mensajes).status_code == 200

        return f

    Path(a.dir).mkdir(parents=True, exist_ok=True)
    nodo = Nodo(
        a.node,
        a.basin,
        Path(a.dir) / f"{a.node}.sqlite",
        enviar("/api/ingesta"),
        enviar("/api/respaldo"),
        # Margen de 2,5 intervalos del modo de menor frecuencia antes de que el servidor lo dé por caído.
        keepalive_s=2.5 * intervalo_muestreo_s(Nivel.VERDE) / a.escala,
        escala_tiempo=a.escala,
    )
    uvicorn.run(crear_app(nodo, a.escala), host="127.0.0.1", port=a.puerto, log_level="warning")


if __name__ == "__main__":
    main()
