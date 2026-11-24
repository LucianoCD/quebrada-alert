"""Pruebas HTTP y de persistencia del backend y contratos Sparkplug B (Issue #3)."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from quebrada import cuencas
from quebrada.backend.app import crear_app, puertos_nodos
from quebrada.backend.motor import MARGEN_ARRIBO_MIN, Motor
from quebrada.schemas import Emergencia, Mensaje, Metricas, Nacimiento, Nivel

NODO, CUENCA = "EST-VOLCAN-CAB01", "CUENCA_ARROYO_MEDIO"
INICIO = datetime(2026, 1, 15, 18, 0, tzinfo=timezone.utc)


def _metricas(**cambios) -> dict:
    base = dict(
        rain_mm_15m=0.0,
        rain_mm_60m=0.0,
        antecedent_rain_72h_mm=0.0,
        water_level_cm=20.0,
        water_level_rise_15m_cm=0.0,
        turbidity_proxy_ntu=40.0,
        battery_soc_pct=90.0,
    )
    return Metricas(**{**base, **cambios}).model_dump()


def _ndata(seq: int, ts: datetime = INICIO, is_historical: bool = False, **metricas_cambios) -> dict:
    return {
        "topic": f"spBv1.0/QUEBRADA/NDATA/{NODO}",
        "payload": {
            "node_id": NODO,
            "basin_id": CUENCA,
            "seq": seq,
            "timestamp_utc": ts.isoformat(),
            "is_historical": is_historical,
            "metrics": _metricas(**metricas_cambios),
        },
    }


@pytest.mark.parametrize(
    "topic",
    [
        "invalido",
        "spBv1.0/QUEBRADA",
        "otra/QUEBRADA/NDATA/EST-VOLCAN-CAB01",
        "spBv1.0/QUEBRADA/NDEATH/EST-VOLCAN-CAB01",
        "spBv1.0/QUEBRADA/NDATA/",
    ],
)
def test_ingesta_topico_malformado_devuelve_422(topic):
    with TestClient(crear_app(":memory:", fuentes_auto=False)) as cliente:
        r = cliente.post("/api/ingesta", json=[{"topic": topic, "payload": {"node_id": NODO}}])
        assert r.status_code == 422


def test_ingesta_node_id_inconsistente_devuelve_422():
    sobre = _ndata(0)
    sobre["topic"] = "spBv1.0/QUEBRADA/NDATA/OTRO-NODO"
    with TestClient(crear_app(":memory:", fuentes_auto=False)) as cliente:
        r = cliente.post("/api/ingesta", json=[sobre])
        assert r.status_code == 422


def test_respaldo_http_solo_subir_y_descenso_en_vivo():
    with TestClient(crear_app(":memory:", fuentes_auto=False)) as cliente:
        rojo = {
            "topic": f"spBv1.0/QUEBRADA/NDATA/{NODO}",
            "payload": Emergencia(
                node_id=NODO,
                basin_id=CUENCA,
                seq=1,
                timestamp_utc=INICIO,
                edge_local_alert=Nivel.ROJO,
                rain_mm_15m=32.0,
                water_level_rise_15m_cm=42.0,
            ).model_dump(mode="json"),
        }
        assert cliente.post("/api/respaldo", json=[rojo]).status_code == 200

        # Un respaldo de menor nivel jamás debe bajar la cuenca (solo_subir=True).
        amarillo = {
            "topic": f"spBv1.0/QUEBRADA/NDATA/{NODO}",
            "payload": Emergencia(
                node_id=NODO,
                basin_id=CUENCA,
                seq=2,
                timestamp_utc=INICIO + timedelta(minutes=1),
                edge_local_alert=Nivel.AMARILLO,
                rain_mm_15m=0.0,
                water_level_rise_15m_cm=0.0,
            ).model_dump(mode="json"),
        }
        assert cliente.post("/api/respaldo", json=[amarillo]).status_code == 200
        estado = cliente.get("/api/estado").json()
        volcan = next(c for c in estado["cuencas"] if c["basin_id"] == CUENCA)
        assert volcan["nivel"] == "RED"
        assert volcan["arribo_estimado"] is not None

        # Tópico NBIRTH en respaldo debe rechazarse con 422.
        nbirth = {
            "topic": f"spBv1.0/QUEBRADA/NBIRTH/{NODO}",
            "payload": rojo["payload"],
        }
        assert cliente.post("/api/respaldo", json=[nbirth]).status_code == 422

        # Solo la telemetría en vivo permite descender, pero mantiene el episodio hasta arribo + margen (A1).
        assert cliente.post("/api/ingesta", json=[_ndata(3, ts=INICIO + timedelta(minutes=2))]).status_code == 200
        estado_retenido = cliente.get("/api/estado").json()
        volcan_retenido = next(c for c in estado_retenido["cuencas"] if c["basin_id"] == CUENCA)
        assert volcan_retenido["nivel"] == "RED"
        assert volcan_retenido["arribo_estimado"] is not None

        eta_total = cuencas.cargar()[CUENCA].eta_min + MARGEN_ARRIBO_MIN + 1.0
        assert (
            cliente.post("/api/ingesta", json=[_ndata(4, ts=INICIO + timedelta(minutes=eta_total))]).status_code == 200
        )
        estado_final = cliente.get("/api/estado").json()
        volcan_final = next(c for c in estado_final["cuencas"] if c["basin_id"] == CUENCA)
        assert volcan_final["nivel"] == "GREEN"
        assert volcan_final["arribo_estimado"] is None


def test_parte_cuenca_desconocida_devuelve_404():
    with TestClient(crear_app(":memory:", fuentes_auto=False)) as cliente:
        assert cliente.get("/api/parte/CUENCA_INEXISTENTE").status_code == 404


def test_reinicio_backend_conserva_minutos_restantes_y_ultima(tmp_path):
    ruta_emergencia = str(tmp_path / "emergencia.duckdb")
    motor1 = Motor(ruta_emergencia)
    motor1.emergencia(
        Emergencia(
            node_id=NODO,
            basin_id=CUENCA,
            seq=1,
            timestamp_utc=INICIO,
            edge_local_alert=Nivel.ROJO,
            rain_mm_15m=30.0,
            water_level_rise_15m_cm=40.0,
        )
    )
    motor1.db.close()

    motor1_reabierto = Motor(ruta_emergencia)
    volcan_em = next(c for c in motor1_reabierto.resumen()["cuencas"] if c["basin_id"] == CUENCA)
    assert volcan_em["nivel"] == "RED"
    assert volcan_em["minutos_restantes"] is not None and volcan_em["minutos_restantes"] > 0
    motor1_reabierto.db.close()

    ruta_vivo = str(tmp_path / "vivo.duckdb")
    motor2 = Motor(ruta_vivo)
    motor2.procesar(
        [
            Mensaje(**_ndata(0, ts=INICIO, is_historical=True)),
            Mensaje(**_ndata(1, ts=INICIO + timedelta(minutes=1), rain_mm_15m=30.0, water_level_rise_15m_cm=40.0)),
        ]
    )
    motor2.db.close()

    motor2_reabierto = Motor(ruta_vivo)
    volcan_vivo = next(c for c in motor2_reabierto.resumen()["cuencas"] if c["basin_id"] == CUENCA)
    assert volcan_vivo["nivel"] == "RED"
    assert volcan_vivo["minutos_restantes"] is not None and volcan_vivo["minutos_restantes"] > 0
    assert volcan_vivo["nodo"]["ultima"] is not None
    assert volcan_vivo["nodo"]["ultima"]["seq"] == 1
    assert volcan_vivo["nodo"]["recuperadas"] == 1
    motor2_reabierto.db.close()


def test_recuperacion_desordenada_ordena_seq():
    motor = Motor()
    lote = [Mensaje(**_ndata(seq, ts=INICIO + timedelta(minutes=seq), is_historical=True)) for seq in [5, 2, 4, 3]]
    motor.procesar(lote)
    rec = next(e for e in motor.eventos() if e["tipo"] == "RECUPERACION")
    assert "seq 2 a 5" in rec["detalle"]


def test_puertos_nodos_ignora_entradas_malformadas(monkeypatch):
    monkeypatch.setenv("QUEBRADA_NODOS", "EST-A=8101,MALFORMADO,=8102,EST-B=abc,EST-C=8103")
    assert puertos_nodos() == {"EST-A": 8101, "EST-C": 8103}


def test_a1_alerta_se_mantiene_hasta_arribo_estimado():
    motor = Motor()
    t0 = INICIO
    eta_min = cuencas.cargar()[CUENCA].eta_min
    motor.procesar([Mensaje(**_ndata(0, ts=t0, rain_mm_15m=20.0))])
    assert motor.estado[CUENCA].nivel is Nivel.NARANJA
    arribo = motor.estado[CUENCA].arribo_estimado
    assert arribo is not None

    # La lluvia cesa a los 15 minutos, pero la crecida aún está en tránsito.
    motor.procesar([Mensaje(**_ndata(1, ts=t0 + timedelta(minutes=15), rain_mm_15m=0.0))])
    assert motor.estado[CUENCA].nivel is Nivel.NARANJA
    assert motor.estado[CUENCA].arribo_estimado == arribo

    # Recién después de arribo_estimado + MARGEN_ARRIBO_MIN vuelve a VERDE.
    motor.procesar([Mensaje(**_ndata(2, ts=t0 + timedelta(minutes=eta_min + MARGEN_ARRIBO_MIN + 0.5)))])
    assert motor.estado[CUENCA].nivel is Nivel.VERDE
    assert motor.estado[CUENCA].arribo_estimado is None


def test_a2_corte_total_con_rojo_reciente_activa_alerta_y_eta():
    motor = Motor()
    t0 = INICIO
    eta_min = cuencas.cargar()[CUENCA].eta_min
    # Corte total: pico ROJO a los 5 min, reconexión 20 min después ya en AMARILLO (quedan > 30 min de arribo).
    t_pico = t0 + timedelta(minutes=5)
    t_reconexion = t0 + timedelta(minutes=25)
    lote = [
        Mensaje(
            **_ndata(
                0,
                ts=t_pico,
                is_historical=True,
                rain_mm_15m=30.0,
                water_level_rise_15m_cm=40.0,
                turbidity_proxy_ntu=700.0,
            )
        ),
        Mensaje(**_ndata(1, ts=t_reconexion, is_historical=False, rain_mm_60m=12.0)),
    ]
    motor.procesar(lote)
    estado = motor.estado[CUENCA]
    assert estado.nivel is Nivel.ROJO
    assert estado.arribo_estimado == t_pico + timedelta(minutes=eta_min)
    res = next(c for c in motor.resumen()["cuencas"] if c["basin_id"] == CUENCA)
    assert res["nivel"] == "RED"
    assert res["minutos_restantes"] == pytest.approx(eta_min - 20.0, abs=0.5)


def test_m1_parte_muestra_datos_de_emergencia_lora_sin_contradiccion():
    motor = Motor()
    motor.procesar([Mensaje(**_ndata(0, ts=INICIO, rain_mm_15m=3.6))])
    motor.emergencia(
        Emergencia(
            node_id=NODO,
            basin_id=CUENCA,
            seq=10,
            timestamp_utc=INICIO + timedelta(minutes=15),
            edge_local_alert=Nivel.ROJO,
            rain_mm_15m=25.1,
            water_level_rise_15m_cm=38.0,
        )
    )
    texto = motor.parte(CUENCA)
    assert "emergencia LoRa" in texto
    assert "25.1 mm en 15 min" in texto
    assert "38.0 cm en 15 min" in texto
    assert "Última telemetría celular previa al corte" in texto


def test_m3_reinicio_rapido_backend_conserva_keepalive_y_escala(tmp_path):
    ruta = str(tmp_path / "keepalive.duckdb")
    reloj = [0.0]
    motor1 = Motor(ruta, reloj=lambda: reloj[0])
    motor1.procesar(
        [
            Mensaje(
                topic=f"spBv1.0/QUEBRADA/NBIRTH/{NODO}",
                payload=Nacimiento(
                    node_id=NODO,
                    basin_id=CUENCA,
                    bd_seq=0,
                    timestamp_utc=INICIO,
                    keepalive_s=12.5,
                    time_scale=60.0,
                ).model_dump(mode="json"),
            )
        ]
    )
    motor1.db.close()

    reloj2 = [0.0]
    motor2 = Motor(ruta, reloj=lambda: reloj2[0])
    assert motor2.nodos[NODO].en_linea is True
    assert motor2.nodos[NODO].keepalive_s == 12.5
    assert motor2.nodos[NODO].escala == 60.0
    assert motor2.vigilar() == []

    reloj2[0] = 13.0
    assert motor2.vigilar() == [NODO]
    assert motor2.nodos[NODO].en_linea is False
    motor2.db.close()


def test_historia_limite_negativo_devuelve_422():
    with TestClient(crear_app(":memory:", fuentes_auto=False)) as cliente:
        assert cliente.get(f"/api/historia/{NODO}?limite=-1").status_code == 422
        assert cliente.get(f"/api/historia/{NODO}?limite=0").status_code == 422
