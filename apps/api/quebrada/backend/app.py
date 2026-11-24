"""API del centro de comando: ingesta, estado, WebSocket y archivos del tablero.

uvicorn quebrada.backend.app:app --port 8000
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from quebrada.backend.motor import Motor
from quebrada.cuencas import DATOS
from quebrada.fuentes import FuentesScheduler, FuentesService
from quebrada.fuentes import crear_router as crear_router_fuentes
from quebrada.fuentes.config import AUTO_HABILITADO
from quebrada.schemas import Emergencia, Mensaje

RAIZ = Path(__file__).resolve().parents[4]
TABLERO = RAIZ / "apps" / "web" / "dist"
log = logging.getLogger("quebrada.backend")


def puertos_nodos() -> dict[str, int]:
    """Puertos de control de los nodos simulados, para la consola de crisis: 'NODO=puerto,NODO=puerto'."""
    crudo = os.environ.get("QUEBRADA_NODOS", "")
    puertos: dict[str, int] = {}
    for par in crudo.split(","):
        par = par.strip()
        if not par:
            continue
        k, sep, v = par.partition("=")
        k, v = k.strip(), v.strip()
        if not sep or not k:
            log.warning("Entrada inválida en QUEBRADA_NODOS ignorada: %r", par)
            continue
        try:
            puertos[k] = int(v)
        except ValueError:
            log.warning("Puerto inválido en QUEBRADA_NODOS ignorado: %r", par)
    return puertos


def crear_app(ruta_db: str | None = None, fuentes_auto: bool | None = None) -> FastAPI:
    motor = Motor(ruta_db or os.environ.get("QUEBRADA_DB", ":memory:"))
    fuentes = FuentesService(motor.db)
    scheduler = FuentesScheduler(fuentes, habilitado=AUTO_HABILITADO if fuentes_auto is None else fuentes_auto)
    clientes: set[WebSocket] = set()

    async def difundir() -> None:
        texto = json.dumps(motor.resumen())
        for ws in list(clientes):
            try:
                await ws.send_text(texto)
            except Exception:
                clientes.discard(ws)

    async def vigilancia() -> None:
        while True:
            await asyncio.sleep(1)
            motor.vigilar()
            await difundir()  # también refresca la cuenta regresiva

    @asynccontextmanager
    async def ciclo(_: FastAPI):
        tarea = asyncio.create_task(vigilancia())
        scheduler.iniciar()
        try:
            yield
        finally:
            await scheduler.detener()
            tarea.cancel()

    app = FastAPI(title="QuebradaAlert", lifespan=ciclo)
    app.state.motor = motor
    app.state.fuentes = fuentes
    app.state.fuentes_scheduler = scheduler
    app.include_router(crear_router_fuentes())

    @app.post("/api/ingesta")
    async def ingesta(mensajes: list[Mensaje]) -> dict:
        try:
            resultado = motor.procesar(mensajes)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        await difundir()
        return resultado

    @app.post("/api/respaldo")
    async def respaldo(mensajes: list[Mensaje]) -> dict:
        """Entrada del gateway del enlace de respaldo (LoRa): solo paquetes de emergencia."""
        try:
            for m in mensajes:
                if m.tipo != "NDATA":
                    raise ValueError(f"Tipo de mensaje no admitido en respaldo: {m.tipo}")
                motor.emergencia(Emergencia(**m.payload))
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        await difundir()
        return {"recibidos": len(mensajes)}

    @app.get("/api/estado")
    async def estado() -> dict:
        return motor.resumen()

    @app.get("/api/historia/{node_id}")
    async def historia(node_id: str, limite: int = Query(default=2000, ge=1, le=10000)) -> list[dict]:
        return motor.historia(node_id, limite)

    @app.get("/api/parte/{basin_id}", response_class=PlainTextResponse)
    async def parte(basin_id: str) -> str:
        if basin_id not in motor.cuencas:
            raise HTTPException(404, "Cuenca desconocida")
        return motor.parte(basin_id)

    # Consola de crisis: reenvía las órdenes al puerto de control de cada nodo simulado. No existe en campo.
    @app.get("/api/simulador")
    async def simulador() -> dict:
        salida = {}
        async with httpx.AsyncClient(timeout=1.0) as cliente:
            for node_id, puerto in puertos_nodos().items():
                try:
                    salida[node_id] = (await cliente.get(f"http://127.0.0.1:{puerto}/estado")).json()
                except httpx.HTTPError:
                    salida[node_id] = None
        return salida

    @app.post("/api/simulador/{node_id}")
    async def controlar(node_id: str, orden: dict) -> dict:
        puerto = puertos_nodos().get(node_id)
        if puerto is None:
            raise HTTPException(404, "Nodo sin puerto de control")
        async with httpx.AsyncClient(timeout=2.0) as cliente:
            try:
                r = await cliente.post(f"http://127.0.0.1:{puerto}/control", json=orden)
            except httpx.HTTPError as error:
                raise HTTPException(502, "El nodo simulado no responde") from error
        if r.status_code != 200:
            raise HTTPException(r.status_code, r.text)
        return r.json()

    @app.websocket("/ws")
    async def ws(conexion: WebSocket) -> None:
        await conexion.accept()
        clientes.add(conexion)
        try:
            await conexion.send_text(json.dumps(motor.resumen()))
            while True:
                await conexion.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            clientes.discard(conexion)

    app.mount("/datos", StaticFiles(directory=DATOS), name="datos")
    if TABLERO.exists():
        app.mount("/", StaticFiles(directory=TABLERO, html=True), name="tablero")
    return app


app = crear_app()
