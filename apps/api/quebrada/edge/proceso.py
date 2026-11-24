"""Proceso de una estación simulada: un nodo, su SQLite y un puerto de control para la consola de crisis.

python -m quebrada.edge.proceso --node EST-VOLCAN-CAB01 --basin CUENCA_ARROYO_MEDIO --puerto 8101
"""

import argparse
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from quebrada.edge.nodo import Nodo
from quebrada.hydrology import intervalo_muestreo_s
from quebrada.schemas import Nivel

log = logging.getLogger("quebrada.edge")


class Orden(BaseModel):
    escenario: str | None = None
    enlace_activo: bool | None = None
    respaldo_activo: bool | None = None
    lluvia_previa_72h_mm: float | None = None


def crear_app(nodo: Nodo, escala: float) -> FastAPI:
    async def bucle() -> None:
        while True:
            try:
                lectura = await asyncio.to_thread(nodo.paso)
                espera = intervalo_muestreo_s(lectura.edge_local_alert) / escala
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Error en ciclo de medición del nodo %s; se reintenta en 1 s", nodo.node_id)
                espera = 1.0
            await asyncio.sleep(espera)

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
        try:
            return nodo.aplicar_control(
                escenario=orden.escenario,
                enlace_activo=orden.enlace_activo,
                respaldo_activo=orden.respaldo_activo,
                lluvia_previa_72h_mm=orden.lluvia_previa_72h_mm,
            )
        except ValueError as error:
            raise HTTPException(422, str(error)) from error

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
