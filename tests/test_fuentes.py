"""Capa MVC de fuentes externas: clientes, repositorio, servicio y endpoints."""

import asyncio
from datetime import datetime, timezone

import duckdb
import httpx
from fastapi.testclient import TestClient
from quebrada.backend.app import crear_app
from quebrada.fuentes.clients.open_meteo import OpenMeteoClient
from quebrada.fuentes.clients.snih import SnihClient, _parse_ms_date
from quebrada.fuentes.config import ESTACIONES_OPEN_METEO, ESTACIONES_SNIH
from quebrada.fuentes.models import FuenteId, LecturaExterna, OrigenLectura, ResultadoSincronizacion
from quebrada.fuentes.repositories.fuentes_repository import FuentesRepository
from quebrada.fuentes.services.fuentes_service import FuentesService


def test_parse_fecha_snih():
    ts = _parse_ms_date("/Date(1795366800000)/")
    assert ts is not None
    assert ts.tzinfo is not None
    assert ts.year >= 2026


def test_snih_client_parsea_ultimos_registros():
    payload = {
        "d": {
            "RespuestaOK": True,
            "MsgErr": "",
            "Mediciones": [
                {
                    "FechaHora": "/Date(1795366800000)/",
                    "Mediciones": [{"Codigo": 20, "Valor": 1.5}],
                }
            ],
        }
    }

    async def correr():
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        async with httpx.AsyncClient(transport=transport) as cliente:
            async with SnihClient(cliente=cliente) as snih:
                return await snih.obtener_lecturas(estaciones=ESTACIONES_SNIH[:1], dias=3)

    lecturas = asyncio.run(correr())
    assert len(lecturas) == 1
    assert lecturas[0].fuente is FuenteId.SNIH
    assert lecturas[0].estacion_id == "280049"
    assert lecturas[0].valor == 1.5
    assert lecturas[0].origen is OrigenLectura.OBSERVADO


def test_open_meteo_client_pronostico():
    payload = {
        "hourly": {
            "time": ["2026-11-22T12:00", "2026-11-22T13:00"],
            "precipitation": [0.2, 1.1],
        }
    }

    async def correr():
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        async with httpx.AsyncClient(transport=transport) as cliente:
            async with OpenMeteoClient(cliente=cliente) as om:
                return await om.obtener_pronostico(estaciones=ESTACIONES_OPEN_METEO[:1])

    lecturas = asyncio.run(correr())
    assert len(lecturas) == 2
    assert lecturas[0].fuente is FuenteId.OPEN_METEO_FORECAST
    assert lecturas[1].valor == 1.1


def test_repositorio_idempotente():
    db = duckdb.connect(":memory:")
    repo = FuentesRepository(db)
    lectura = LecturaExterna(
        fuente=FuenteId.SNIH,
        estacion_id="280049",
        variable="precipitacion_mm",
        ts=datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc),
        valor=0.5,
        origen=OrigenLectura.OBSERVADO,
    )
    assert repo.guardar_lecturas([lectura]) == (1, 0)
    assert repo.guardar_lecturas([lectura]) == (0, 1)
    assert repo.contar_lecturas(FuenteId.SNIH) == 1


def test_servicio_sincroniza_y_persiste(monkeypatch):
    db = duckdb.connect(":memory:")
    service = FuentesService(db)

    async def fake_snih(self, estaciones=ESTACIONES_SNIH, dias=7):
        return [
            LecturaExterna(
                fuente=FuenteId.SNIH,
                estacion_id="280049",
                variable="precipitacion_mm",
                ts=datetime(2026, 11, 22, 15, 0, tzinfo=timezone.utc),
                valor=2.0,
                origen=OrigenLectura.OBSERVADO,
            )
        ]

    monkeypatch.setattr(SnihClient, "obtener_lecturas", fake_snih)
    resultados = asyncio.run(service.sincronizar(FuenteId.SNIH))
    assert resultados[0].estado == "ok"
    assert resultados[0].nuevas == 1
    assert service.repo.contar_lecturas(FuenteId.SNIH) == 1


def test_endpoints_fuentes():
    app = crear_app(fuentes_auto=False)
    client = TestClient(app)
    svc: FuentesService = app.state.fuentes
    svc.repo.guardar_lecturas(
        [
            LecturaExterna(
                fuente=FuenteId.OPEN_METEO_FORECAST,
                estacion_id="EST-VOLCAN-CAB01",
                variable="precipitacion_mm",
                ts=datetime(2026, 11, 22, 10, 0, tzinfo=timezone.utc),
                valor=0.4,
                origen=OrigenLectura.PRONOSTICO,
            )
        ]
    )

    r = client.get("/api/fuentes")
    assert r.status_code == 200
    cuerpo = r.json()
    assert len(cuerpo["fuentes"]) == 3
    assert cuerpo["lecturas_totales"] == 1

    r = client.get("/api/fuentes/lecturas", params={"fuente": "open_meteo_forecast"})
    assert r.status_code == 200
    assert r.json()["lecturas"][0]["valor"] == 0.4

    async def ok_sync(fuente=None):
        return [
            ResultadoSincronizacion(
                fuente=fuente or FuenteId.SNIH,
                estado="ok",
                nuevas=0,
                repetidas=0,
                detalle="mock",
            )
        ]

    svc.sincronizar = ok_sync  # type: ignore[method-assign]
    r = client.post("/api/fuentes/sincronizar", params={"fuente": "snih"})
    assert r.status_code == 200
    assert r.json()["resultados"][0]["estado"] == "ok"
