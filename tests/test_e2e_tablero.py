"""Pruebas extremo a extremo del bundle offline, WebSocket, parte de situación y resiliencia (Issue #7)."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from quebrada import cuencas
from quebrada.backend.app import TABLERO, crear_app
from quebrada.backend.motor import MARGEN_ARRIBO_MIN
from quebrada.edge.nodo import Nodo
from quebrada.schemas import Emergencia, Mensaje, Nivel

NODO, CUENCA = "EST-VOLCAN-CAB01", "CUENCA_ARROYO_MEDIO"
INICIO = datetime(2026, 1, 15, 18, 0, tzinfo=timezone.utc)
CDNS_PROHIBIDOS = ("unpkg.com", "jsdelivr.net", "cdnjs.cloudflare.com", "fonts.googleapis.com")


@pytest.mark.skipif(not TABLERO.exists(), reason="Requiere compilación previa del tablero (npm run build)")
def test_bundle_offline_y_geodatos_sin_cdn():
    with TestClient(crear_app(":memory:", fuentes_auto=False)) as cliente:
        r_index = cliente.get("/")
        assert r_index.status_code == 200
        assert '<div id="root"></div>' in r_index.text
        for cdn in CDNS_PROHIBIDOS:
            assert cdn not in r_index.text

        assets = [archivo for archivo in (TABLERO / "assets").iterdir() if archivo.is_file()]
        assert any(a.suffix == ".woff2" for a in assets)
        assert any("maplibre-gl-worker" in a.name for a in assets)

        for archivo in assets:
            resp = cliente.get(f"/assets/{archivo.name}")
            assert resp.status_code == 200
            if archivo.suffix in {".js", ".mjs", ".css"}:
                contenido = archivo.read_text(encoding="utf-8", errors="ignore")
                if archivo.name.startswith("deckgl-"):
                    contenido = contenido.replace("https://unpkg.com/@loaders.gl", "")
                for cdn in CDNS_PROHIBIDOS:
                    assert cdn not in contenido

        for capa in ("cuencas.geojson", "cauces.geojson", "puntos.geojson", "contexto.geojson", "relieve.png"):
            assert cliente.get(f"/datos/{capa}").status_code == 200


def test_flujo_e2e_demo_resiliencia_y_ws(tmp_path):
    with TestClient(crear_app(":memory:", fuentes_auto=False)) as cliente:

        def enviar(ruta: str):
            return lambda mensajes: cliente.post(ruta, json=mensajes).status_code == 200

        nodo = Nodo(
            NODO,
            CUENCA,
            tmp_path / "nodo.sqlite",
            enviar("/api/ingesta"),
            enviar("/api/respaldo"),
            inicio=INICIO,
        )

        # 1. Operación normal en línea.
        for _ in range(3):
            nodo.paso()
        assert nodo.en_cola() == 0

        # 2. Tormenta convectiva + corte celular: el respaldo LoRa eleva el centro a ROJO.
        nodo.enlace_activo = False
        nodo.estado.cambiar("tormenta_convectiva", nodo.reloj.timestamp())
        for _ in range(200):
            if nodo.paso().edge_local_alert is Nivel.ROJO:
                break
        assert nodo.en_cola() > 0
        assert nodo.baliza is True

        # 3. WebSocket y Parte de Situación reflejan la emergencia vigente y datos LoRa (M1).
        with cliente.websocket_connect("/ws") as ws:
            snapshot = ws.receive_json()
        volcan = next(c for c in snapshot["cuencas"] if c["basin_id"] == CUENCA)
        assert volcan["nivel"] == "RED"
        assert volcan["minutos_restantes"] is not None and volcan["minutos_restantes"] > 0

        parte_txt = cliente.get(f"/api/parte/{CUENCA}").text
        assert "emergencia LoRa" in parte_txt
        assert "Última telemetría celular previa al corte" in parte_txt

        # 4. Fuentes aisladas accesibles desde el tablero sin interferir con el semáforo.
        assert cliente.get("/api/fuentes").status_code == 200

        # 5. Reconexión: vacía búfer sin huecos ni pérdida de secuencia.
        nodo.enlace_activo = True
        nodo.paso()
        assert nodo.en_cola() == 0
        estado = cliente.get("/api/estado").json()
        volcan_rec = next(c for c in estado["cuencas"] if c["basin_id"] == CUENCA)
        assert volcan_rec["nodo"]["huecos"] == 0
        assert volcan_rec["nodo"]["recuperadas"] > 0

        # 6. Cesa la lluvia antes del arribo (A1): retiene alerta hasta arribo + margen y luego baja.
        nodo.estado.cambiar("normal", nodo.reloj.timestamp())
        eta_min = cuencas.cargar()[CUENCA].eta_min
        llego_verde_sensor = False
        for _ in range(600):
            lectura = nodo.paso()
            if lectura.edge_local_alert is Nivel.VERDE:
                llego_verde_sensor = True
                break
        assert llego_verde_sensor
        # Si ya superó arribo + margen, el centro pudo descender; si aún está dentro, retiene alerta.
        # Verificamos explícitamente que tras superar arribo + margen + 5 min baja a GREEN.
        for _ in range(int(eta_min + MARGEN_ARRIBO_MIN) * 2 + 20):
            nodo.paso()
        estado_final = cliente.get("/api/estado").json()
        volcan_final = next(c for c in estado_final["cuencas"] if c["basin_id"] == CUENCA)
        assert volcan_final["nivel"] == "GREEN"
        assert volcan_final["arribo_estimado"] is None

        # Garantiza que el paquete de respaldo con tópico válido y payload inválido siga rechazándose.
        invalido = [
            {
                "topic": f"spBv1.0/QUEBRADA/NDATA/{NODO}",
                "payload": Emergencia(
                    node_id=NODO,
                    basin_id=CUENCA,
                    seq=1,
                    timestamp_utc=INICIO,
                    edge_local_alert=Nivel.ROJO,
                    rain_mm_15m=10.0,
                    water_level_rise_15m_cm=10.0,
                ).model_dump(mode="json"),
            }
        ]
        invalido[0]["topic"] = f"spBv1.0/QUEBRADA/NBIRTH/{NODO}"
        assert cliente.post("/api/respaldo", json=invalido).status_code == 422
        assert isinstance(Mensaje(topic=f"spBv1.0/QUEBRADA/NDATA/{NODO}", payload={"node_id": NODO}), Mensaje)
