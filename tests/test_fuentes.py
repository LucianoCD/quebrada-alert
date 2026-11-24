"""Capa MVC de fuentes externas: clientes, repositorio, servicio y endpoints."""

import asyncio
from datetime import datetime, timedelta, timezone

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
from quebrada.fuentes.services.scheduler import FuentesScheduler


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


def test_scheduler_reintenta_errores_sin_consumir_el_intervalo():
    class ServicioConError:
        async def sincronizar(self, fuente):
            return [ResultadoSincronizacion(fuente=fuente, estado="error", detalle="timeout")]

    scheduler = FuentesScheduler(ServicioConError())
    asyncio.run(scheduler._correr_pendientes(forzar=True))
    assert scheduler._ultima == {}


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

    r_syncs = client.get("/api/fuentes/sincronizaciones")
    assert r_syncs.status_code == 200
    assert r_syncs.json()["sincronizaciones"] == []

    r_por_fuente = client.get("/api/fuentes/open_meteo_forecast/lecturas")
    assert r_por_fuente.status_code == 200
    assert r_por_fuente.json()["fuente"] == "open_meteo_forecast"
    assert len(r_por_fuente.json()["lecturas"]) == 1


def test_pronostico_actualiza_valor_en_conflicto():
    db = duckdb.connect(":memory:")
    repo = FuentesRepository(db)
    ts = datetime(2026, 11, 23, 18, 0, tzinfo=timezone.utc)
    inicial = LecturaExterna(
        fuente=FuenteId.OPEN_METEO_FORECAST,
        estacion_id="EST-VOLCAN-CAB01",
        variable="precipitacion_mm",
        ts=ts,
        valor=0.0,
        origen=OrigenLectura.PRONOSTICO,
    )
    actualizada = inicial.model_copy(update={"valor": 22.5})

    assert repo.guardar_lecturas([inicial]) == (1, 0)
    assert repo.guardar_lecturas([actualizada]) == (0, 1)
    assert repo.contar_lecturas(FuenteId.OPEN_METEO_FORECAST) == 1
    lecturas = repo.listar_lecturas(fuente=FuenteId.OPEN_METEO_FORECAST)
    assert lecturas[0]["valor"] == 22.5


def test_open_meteo_client_archivo():
    payload = {
        "hourly": {
            "time": ["2026-11-21T12:00"],
            "precipitation": [3.4],
        }
    }

    async def correr():
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        async with httpx.AsyncClient(transport=transport) as cliente:
            async with OpenMeteoClient(cliente=cliente) as om:
                return await om.obtener_archivo(estaciones=ESTACIONES_OPEN_METEO[:1], dias=2)

    lecturas = asyncio.run(correr())
    assert len(lecturas) == 1
    assert lecturas[0].fuente is FuenteId.OPEN_METEO_ARCHIVE
    assert lecturas[0].origen is OrigenLectura.REANALISIS
    assert lecturas[0].valor == 3.4


def test_snih_respuesta_no_ok_y_timeout_detalle_no_vacio():
    async def correr_no_ok():
        payload = {"d": {"RespuestaOK": False, "MsgErr": "sin permiso"}}
        transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        async with httpx.AsyncClient(transport=transport) as cliente:
            async with SnihClient(cliente=cliente) as snih:
                await snih.obtener_lecturas(estaciones=ESTACIONES_SNIH[:1], dias=1)

    try:
        asyncio.run(correr_no_ok())
        raise AssertionError("Debía fallar cuando RespuestaOK es False")
    except RuntimeError as error:
        assert "sin permiso" in str(error)

    async def correr_timeout():
        def fallar_timeout(request):
            raise httpx.ReadTimeout("")

        transport = httpx.MockTransport(fallar_timeout)
        async with httpx.AsyncClient(transport=transport) as cliente:
            svc = FuentesService(duckdb.connect(":memory:"), cliente=cliente)
            return await svc.sincronizar(FuenteId.OPEN_METEO_FORECAST)

    resultados = asyncio.run(correr_timeout())
    assert resultados[0].estado == "error"
    assert resultados[0].detalle == "ReadTimeout"


def test_scheduler_aplica_backoff_exponencial_tras_error():
    reloj = [datetime(2026, 11, 23, 12, 0, tzinfo=timezone.utc)]
    llamadas: list[FuenteId] = []
    estado_respuesta = {"estado": "error"}

    class ServicioAlternante:
        async def sincronizar(self, fuente):
            llamadas.append(fuente)
            return [ResultadoSincronizacion(fuente=fuente, estado=estado_respuesta["estado"], detalle="fallo")]

    scheduler = FuentesScheduler(ServicioAlternante(), reloj=lambda: reloj[0])
    asyncio.run(scheduler._correr_pendientes(forzar=True))
    assert len(llamadas) == len(FuenteId)

    # A los 10 s sigue en backoff (30 s para el 1er fallo): no vuelve a intentar.
    reloj[0] += timedelta(seconds=10)
    asyncio.run(scheduler._correr_pendientes(forzar=False))
    assert len(llamadas) == len(FuenteId)

    # A los 31 s ya venció el 1er backoff; vuelve a intentar y pasa a 60 s en el 2º fallo.
    reloj[0] += timedelta(seconds=21)
    asyncio.run(scheduler._correr_pendientes(forzar=False))
    assert len(llamadas) == 2 * len(FuenteId)

    reloj[0] += timedelta(seconds=45)
    asyncio.run(scheduler._correr_pendientes(forzar=False))
    assert len(llamadas) == 2 * len(FuenteId)

    # A los 60 s del 2º fallo se recupera y limpia el estado de backoff.
    estado_respuesta["estado"] = "ok"
    reloj[0] += timedelta(seconds=20)
    asyncio.run(scheduler._correr_pendientes(forzar=False))
    assert len(llamadas) == 3 * len(FuenteId)
    assert scheduler._fallos == {}
    assert scheduler._siguiente_reintento == {}


def test_n7_snih_y_era5_actualizan_valor_revisado():
    db = duckdb.connect(":memory:")
    repo = FuentesRepository(db)
    ts = datetime(2026, 11, 23, 18, 0, tzinfo=timezone.utc)
    for fuente, est, origen, v_ini, v_rev in [
        (FuenteId.SNIH, "280049", OrigenLectura.OBSERVADO, 1.0, 5.5),
        (FuenteId.OPEN_METEO_ARCHIVE, "EST-VOLCAN-CAB01", OrigenLectura.REANALISIS, 2.0, 7.5),
    ]:
        inicial = LecturaExterna(
            fuente=fuente,
            estacion_id=est,
            variable="precipitacion_mm",
            ts=ts,
            valor=v_ini,
            origen=origen,
        )
        revisada = inicial.model_copy(update={"valor": v_rev})
        assert repo.guardar_lecturas([inicial]) == (1, 0)
        assert repo.guardar_lecturas([revisada]) == (0, 1)
        assert repo.contar_lecturas(fuente) == 1
        assert repo.listar_lecturas(fuente=fuente)[0]["valor"] == v_rev
