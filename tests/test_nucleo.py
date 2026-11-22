from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from quebrada import cuencas, hydrology
from quebrada.backend.app import crear_app
from quebrada.backend.motor import Motor
from quebrada.edge.nodo import Nodo
from quebrada.schemas import Conectividad, Emergencia, Mensaje, Metricas, Nivel

NODO, CUENCA = "EST-VOLCAN-CAB01", "CUENCA_ARROYO_MEDIO"
INICIO = datetime(2026, 1, 15, 18, 0, tzinfo=timezone.utc)


def metricas(**cambios) -> Metricas:
    base = dict(rain_mm_15m=0, rain_mm_60m=0, antecedent_rain_72h_mm=0, water_level_cm=20,
                water_level_rise_15m_cm=0, turbidity_proxy_ntu=40, battery_soc_pct=90)  # fmt: skip
    return Metricas(**{**base, **cambios})


# --- motor hidrológico ----------------------------------------------------------------------


def test_kirpich():
    # 0,0195 · 1000^0,77 · 0,1^-0,385 = 9,6 min
    assert hydrology.kirpich_min(1000, 0.1) == pytest.approx(9.6, abs=0.1)
    assert hydrology.kirpich_min(2000, 0.1) > hydrology.kirpich_min(1000, 0.1)
    assert hydrology.kirpich_min(1000, 0.2) < hydrology.kirpich_min(1000, 0.1)
    with pytest.raises(ValueError):
        hydrology.kirpich_min(1000, 0)


@pytest.mark.parametrize(
    "cambios, esperado",
    [
        ({}, Nivel.VERDE),
        ({"rain_mm_60m": 4}, Nivel.VERDE),
        ({"rain_mm_60m": 12}, Nivel.AMARILLO),
        ({"rain_mm_60m": 3, "antecedent_rain_72h_mm": 35}, Nivel.AMARILLO),  # suelo saturado con lluvia activa
        ({"rain_mm_60m": 0, "antecedent_rain_72h_mm": 35}, Nivel.VERDE),  # suelo saturado, sin lluvia
        ({"rain_mm_15m": 16, "rain_mm_60m": 16}, Nivel.NARANJA),
        ({"water_level_rise_15m_cm": 31}, Nivel.NARANJA),
        ({"rain_mm_15m": 26, "rain_mm_60m": 26}, Nivel.NARANJA),  # lluvia intensa sin respuesta del cauce
        ({"rain_mm_15m": 26, "rain_mm_60m": 26, "water_level_rise_15m_cm": 31}, Nivel.ROJO),
        ({"rain_mm_15m": 26, "rain_mm_60m": 26, "turbidity_proxy_ntu": 800}, Nivel.ROJO),
    ],
)
def test_semaforo(cambios, esperado):
    assert hydrology.clasificar(metricas(**cambios)) is esperado


def test_cuencas_con_atributos_fisicos():
    todas = cuencas.cargar()
    assert CUENCA in todas
    for c in todas.values():
        assert c.area_km2 > 5
        assert 0 < c.largo_estacion_impacto_m < c.largo_cauce_m
        assert 5 < c.eta_min < c.tc_min < 300


# --- nodo y backend -------------------------------------------------------------------------


class Enlace:
    """Une un nodo con un motor sin red: entrega los lotes como lo haría la API."""

    def __init__(self, motor: Motor):
        self.motor, self.lotes = motor, 0

    def principal(self, mensajes: list[dict]) -> bool:
        self.motor.procesar([Mensaje(**m) for m in mensajes])
        self.lotes += 1
        return True

    def respaldo(self, mensajes: list[dict]) -> bool:
        for m in mensajes:
            self.motor.emergencia(Emergencia(**m["payload"]))
        return True


@pytest.fixture
def sistema(tmp_path):
    motor = Motor()
    enlace = Enlace(motor)
    nodo = Nodo(NODO, CUENCA, tmp_path / "nodo.sqlite", enlace.principal, enlace.respaldo, inicio=INICIO)
    return nodo, motor


def alertas(motor: Motor, nivel: Nivel | None = None) -> list[dict]:
    return [e for e in motor.eventos(500) if e["tipo"] == "ALERTA" and (nivel is None or e["nivel"] == nivel.value)]


def cantidad(motor: Motor, donde: str = "true") -> int:
    return motor.db.execute(f"select count(*) from telemetria where {donde}").fetchone()[0]


def test_sqlite_en_modo_wal(sistema):
    nodo, _ = sistema
    assert nodo.db.execute("pragma journal_mode").fetchone()[0] == "wal"


def test_en_linea_llega_en_vivo(sistema):
    nodo, motor = sistema
    for _ in range(5):
        nodo.paso()
    assert nodo.en_cola() == 0
    assert cantidad(motor) == 5
    assert cantidad(motor, "is_historical") == 0
    assert motor.nodos[NODO].en_linea
    assert motor.estado[CUENCA].nivel is Nivel.VERDE


def test_diez_paquetes_sin_enlace_y_reconexion(sistema):
    nodo, motor = sistema
    for _ in range(3):
        nodo.paso()
    nodo.enlace_activo = False
    for _ in range(10):
        lectura = nodo.paso()
    assert nodo.conectividad is Conectividad.ISLA
    assert lectura.connectivity_state is Conectividad.ISLA
    assert nodo.en_cola() == 10
    assert cantidad(motor) == 3

    nodo.enlace_activo = True
    nodo.paso()
    assert nodo.en_cola() == 0
    secuencias = [f[0] for f in motor.db.execute("select seq from telemetria order by seq").fetchall()]
    assert secuencias == list(range(14))  # sin huecos ni repetidos
    assert motor.huecos(NODO) == 0
    # Las diez del corte llegan marcadas como históricas; la que disparó la reconexión, en vivo.
    assert cantidad(motor, "is_historical") == 10
    assert cantidad(motor, "not is_historical and seq = 13") == 1


def test_reenvio_no_duplica(sistema):
    nodo, motor = sistema
    for _ in range(4):
        nodo.paso()
    # El backend recibió el lote pero el nodo no vio la confirmación: lo vuelve a enviar.
    nodo.db.execute("update lecturas set enviado = 0")
    nodo.db.commit()
    nodo.paso()
    assert cantidad(motor) == 5


def test_la_cola_sobrevive_a_un_reinicio(tmp_path):
    motor = Motor()
    enlace = Enlace(motor)
    nodo = Nodo(NODO, CUENCA, tmp_path / "n.sqlite", enlace.principal, inicio=INICIO)
    nodo.enlace_activo = False
    for _ in range(6):
        nodo.paso()
    reloj = nodo.reloj
    nodo.db.close()

    otro = Nodo(NODO, CUENCA, tmp_path / "n.sqlite", enlace.principal, inicio=reloj)
    assert otro.en_cola() == 6
    otro.paso()
    assert otro.ultimo_seq() == 6  # la secuencia continúa
    assert cantidad(motor) == 7 and motor.huecos(NODO) == 0


def tormenta_aislada(nodo: Nodo, respaldo: bool) -> None:
    """Tormenta convectiva completa con el enlace principal caído, hasta que el nodo vuelve a verde."""
    nodo.paso()
    nodo.enlace_activo, nodo.respaldo_activo = False, respaldo
    nodo.estado.cambiar("tormenta_convectiva", nodo.reloj.timestamp())
    vio_rojo = False
    for _ in range(3000):
        lectura = nodo.paso()
        vio_rojo = vio_rojo or lectura.edge_local_alert is Nivel.ROJO
        if vio_rojo and lectura.edge_local_alert is Nivel.VERDE:
            break
    assert vio_rojo and nodo.nivel is Nivel.VERDE


def test_alerta_autonoma_sin_ningun_enlace(sistema):
    nodo, motor = sistema
    nodo.paso()
    nodo.enlace_activo = nodo.respaldo_activo = False
    nodo.estado.cambiar("tormenta_convectiva", nodo.reloj.timestamp())
    for _ in range(200):
        if nodo.paso().edge_local_alert is Nivel.ROJO:
            break
    assert nodo.baliza
    assert any("Alerta autónoma ROJO" in linea for linea in nodo.registro)
    assert motor.estado[CUENCA].nivel is Nivel.VERDE  # el centro no se enteró


def test_tormenta_terminada_no_dispara_alarma_tardia(sistema):
    nodo, motor = sistema
    tormenta_aislada(nodo, respaldo=False)
    assert alertas(motor) == []

    nodo.enlace_activo = True
    nodo.paso()
    assert nodo.en_cola() == 0 and motor.huecos(NODO) == 0
    assert cantidad(motor, "edge_local_alert = 'RED' and is_historical") > 0  # la evidencia quedó guardada
    assert alertas(motor) == []
    assert motor.estado[CUENCA].nivel is Nivel.VERDE
    assert motor.estado[CUENCA].arribo_estimado is None
    recuperacion = [e for e in motor.eventos(500) if e["tipo"] == "RECUPERACION"]
    assert any("ROJO" in e["detalle"] for e in recuperacion)


def test_emergencia_por_respaldo_y_sin_alarmas_duplicadas(sistema):
    nodo, motor = sistema
    nodo.paso()
    nodo.enlace_activo = False
    nodo.estado.cambiar("tormenta_convectiva", nodo.reloj.timestamp())
    for _ in range(200):
        if nodo.paso().edge_local_alert is Nivel.ROJO:
            break
    estado = motor.estado[CUENCA]
    assert estado.nivel is Nivel.ROJO and estado.origen == "emergencia"
    assert cantidad(motor) == 1  # solo llegó el paquete corto, no la telemetría
    # El arribo se cuenta desde el primer nivel crítico, con el tiempo de Kirpich de la cuenca.
    naranja = alertas(motor, Nivel.NARANJA)[0]
    esperado = datetime.fromisoformat(naranja["ts"]).timestamp() + cuencas.cargar()[CUENCA].eta_min * 60
    assert estado.arribo_estimado.timestamp() == pytest.approx(esperado, abs=1)
    arribo = estado.arribo_estimado

    nodo.enlace_activo = True
    nodo.paso()  # vuelca el búfer con la tormenta todavía en curso
    assert motor.huecos(NODO) == 0
    assert len(alertas(motor, Nivel.ROJO)) == 1
    assert len(alertas(motor, Nivel.NARANJA)) == 1
    assert motor.estado[CUENCA].arribo_estimado == arribo  # la cuenta regresiva no se reinicia


def test_nodo_caido_por_falta_de_mensajes(tmp_path):
    ahora = [0.0]
    motor = Motor(reloj=lambda: ahora[0])
    enlace = Enlace(motor)
    nodo = Nodo(NODO, CUENCA, tmp_path / "n.sqlite", enlace.principal, inicio=INICIO, keepalive_s=10)
    nodo.paso()
    assert motor.vigilar() == [] and motor.nodos[NODO].en_linea
    ahora[0] = 11
    assert motor.vigilar() == [NODO]
    assert not motor.nodos[NODO].en_linea
    assert motor.vigilar() == []  # NDEATH se registra una sola vez
    ahora[0] = 12
    nodo.paso()
    assert motor.nodos[NODO].en_linea
    tipos = [e["tipo"] for e in motor.eventos()]
    assert tipos.count("NDEATH") == 1 and tipos[0] == "EN_LINEA"


def test_api(tmp_path):
    with TestClient(crear_app(":memory:", fuentes_auto=False)) as cliente:

        def enviar(ruta):
            return lambda mensajes: cliente.post(ruta, json=mensajes).status_code == 200

        nodo = Nodo(NODO, CUENCA, tmp_path / "n.sqlite", enviar("/api/ingesta"), enviar("/api/respaldo"), inicio=INICIO)
        nodo.estado.cambiar("tormenta_convectiva", nodo.reloj.timestamp())
        for _ in range(200):
            if nodo.paso().edge_local_alert is Nivel.ROJO:
                break
        estado = cliente.get("/api/estado").json()
        volcan = next(c for c in estado["cuencas"] if c["basin_id"] == CUENCA)
        assert volcan["nivel"] == "RED" and volcan["minutos_restantes"] > 0
        assert volcan["nodo"]["huecos"] == 0
        assert len(cliente.get(f"/api/historia/{NODO}").json()) == nodo.ultimo_seq() + 1
        parte = cliente.get(f"/api/parte/{CUENCA}").text
        assert "ROJO" in parte and "Defensa Civil" in parte
        assert cliente.get("/datos/cuencas.geojson").status_code == 200
        malo = [{"topic": "spBv1.0/QUEBRADA/NDATA/X", "payload": {"node_id": "X"}}]
        assert cliente.post("/api/ingesta", json=malo).status_code == 422
        with cliente.websocket_connect("/ws") as ws:
            assert len(ws.receive_json()["cuencas"]) == len(cuencas.cargar())


def nacimiento(ts=INICIO) -> Mensaje:
    carga = {"node_id": NODO, "basin_id": CUENCA, "bd_seq": 0, "timestamp_utc": ts.isoformat(), "keepalive_s": 10}
    return Mensaje(topic=f"spBv1.0/QUEBRADA/NBIRTH/{NODO}", payload=carga)


def dato(seq: int, **cambios) -> Mensaje:
    carga = {"node_id": NODO, "basin_id": CUENCA, "seq": seq, "timestamp_utc": INICIO.isoformat(),
             "metrics": metricas().model_dump(), **cambios}  # fmt: skip
    return Mensaje(topic=f"spBv1.0/QUEBRADA/NDATA/{NODO}", payload=carga)


def paquete(nivel: Nivel = Nivel.ROJO) -> Emergencia:
    return Emergencia(node_id=NODO, basin_id=CUENCA, seq=5, timestamp_utc=INICIO, edge_local_alert=nivel,
                      rain_mm_15m=30, water_level_rise_15m_cm=40)  # fmt: skip


def test_nodo_que_cae_sin_telemetria_en_vivo():
    ahora = [0.0]
    motor = Motor(reloj=lambda: ahora[0])
    motor.procesar([nacimiento(), dato(0, is_historical=True)])
    ahora[0] = 11
    assert motor.vigilar() == [NODO]
    caida = motor.resumen()["eventos"][0]
    assert caida["tipo"] == "NDEATH" and caida["ts"] is not None


def test_emergencia_como_primer_contacto_tiene_cuenta_regresiva():
    motor = Motor()
    motor.emergencia(paquete())
    volcan = next(c for c in motor.resumen()["cuencas"] if c["basin_id"] == CUENCA)
    assert volcan["nivel"] == "RED"
    assert volcan["minutos_restantes"] == pytest.approx(cuencas.cargar()[CUENCA].eta_min, abs=0.5)


def test_reinicio_del_backend_conserva_la_alerta(tmp_path):
    ruta = str(tmp_path / "central.duckdb")
    motor = Motor(ruta)
    motor.emergencia(paquete(Nivel.NARANJA))
    motor.emergencia(paquete(Nivel.ROJO))
    arribo = motor.estado[CUENCA].arribo_estimado
    motor.db.close()

    otro = Motor(ruta)
    estado = otro.estado[CUENCA]
    assert estado.nivel is Nivel.ROJO and estado.origen == "emergencia"
    assert estado.arribo_estimado == arribo


def test_cuenca_desconocida_no_se_guarda():
    motor = Motor()
    with pytest.raises(ValueError):
        motor.procesar([dato(0, basin_id="CUENCA_INEXISTENTE")])
    assert cantidad(motor) == 0
    assert motor.procesar([dato(0)]) == {"nuevas": 1, "repetidas": 0}


def test_marca_de_tiempo_sin_zona_se_rechaza():
    with pytest.raises(ValueError):
        dato_sin_zona = dato(0, timestamp_utc="2026-01-15T18:00:00")
        Motor().procesar([dato_sin_zona])


def test_reanudar_no_cuenta_lluvia_futura(tmp_path):
    nodo = Nodo(NODO, CUENCA, tmp_path / "n.sqlite", lambda m: True, inicio=INICIO)
    nodo.estado.cambiar("tormenta_convectiva", nodo.reloj.timestamp())
    for _ in range(60):
        nodo.paso()
    fin = nodo.reloj
    nodo.db.close()
    otro = Nodo(NODO, CUENCA, tmp_path / "n.sqlite", lambda m: True, inicio=INICIO)  # reloj anterior a lo guardado
    assert otro.reloj == fin
    assert otro.paso().timestamp_utc > fin
