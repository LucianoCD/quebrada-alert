"""Pruebas de resiliencia, concurrencia y vaciado multi-lote del nodo edge (Issue #2)."""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from quebrada.backend.motor import Motor
from quebrada.edge.nodo import Nodo
from quebrada.edge.proceso import crear_app
from quebrada.schemas import Conectividad, Emergencia, Mensaje, Nivel

NODO, CUENCA = "EST-VOLCAN-CAB01", "CUENCA_ARROYO_MEDIO"
INICIO = datetime(2026, 1, 15, 18, 0, tzinfo=timezone.utc)


def test_primer_paso_sin_enlace_refleja_island_mode(tmp_path):
    motor = Motor()
    nodo = Nodo(
        NODO,
        CUENCA,
        tmp_path / "nodo.sqlite",
        lambda m: motor.procesar([Mensaje(**x) for x in m]) is not None,
        inicio=INICIO,
    )
    nodo.enlace_activo = False
    lectura = nodo.paso()
    assert lectura.connectivity_state is Conectividad.ISLA
    assert nodo.ultima is not None
    assert nodo.ultima.connectivity_state is Conectividad.ISLA
    assert nodo.en_cola() == 1


def test_vaciado_multi_lote_con_fallo_intermedio(tmp_path):
    motor = Motor()
    fallos_restantes = {"principal": 0}

    def enviar_principal(mensajes: list[dict]) -> bool:
        if fallos_restantes["principal"] > 0:
            fallos_restantes["principal"] -= 1
            return False
        motor.procesar([Mensaje(**m) for m in mensajes])
        return True

    def enviar_respaldo(mensajes: list[dict]) -> bool:
        for m in mensajes:
            motor.emergencia(Emergencia(**m["payload"]))
        return True

    nodo = Nodo(NODO, CUENCA, tmp_path / "nodo.sqlite", enviar_principal, enviar_respaldo, inicio=INICIO, lote=3)
    nodo.enlace_activo = False
    nodo.estado.cambiar("tormenta_convectiva", nodo.reloj.timestamp())

    while nodo.en_cola() < 8 or nodo.nivel is not Nivel.ROJO:
        nodo.paso()
        if nodo.ultimo_seq() > 150:
            break

    total_encolado = nodo.en_cola()
    assert total_encolado >= 8
    assert nodo.emergencia_enviada is Nivel.ROJO

    # Al reconectar, aceptamos el primer lote (3 lecturas) pero hacemos fallar el segundo.
    class _Controlado:
        lotes = 0

    def principal_intermitente(mensajes: list[dict]) -> bool:
        _Controlado.lotes += 1
        if _Controlado.lotes == 2:
            return False
        motor.procesar([Mensaje(**m) for m in mensajes])
        return True

    nodo.enviar = principal_intermitente
    nodo.enlace_activo = True
    confirmadas = nodo.sincronizar()

    assert confirmadas == 3
    assert nodo.en_cola() == total_encolado - 3
    assert nodo.conectividad is Conectividad.ISLA
    assert nodo.emergencia_enviada is Nivel.ROJO

    # Ahora permitimos vaciar todos los lotes restantes.
    nodo.enviar = enviar_principal
    confirmadas_resto = nodo.sincronizar()
    assert confirmadas_resto == total_encolado - 3
    assert nodo.en_cola() == 0
    assert nodo.conectividad is Conectividad.EN_LINEA
    assert nodo.emergencia_enviada is Nivel.VERDE
    assert motor.huecos(NODO) == 0

    ultimo_seq = nodo.ultimo_seq()
    historicas = motor.db.execute("select count(*) from telemetria where is_historical").fetchone()[0]
    vivas = motor.db.execute(
        "select count(*) from telemetria where not is_historical and seq = ?", [ultimo_seq]
    ).fetchone()[0]
    assert historicas == ultimo_seq
    assert vivas == 1


def test_reintento_respaldo_lora_tras_fallo(tmp_path):
    motor = Motor()
    estado_lora = {"disponible": False, "envios": 0}

    def respaldo(mensajes: list[dict]) -> bool:
        if not estado_lora["disponible"]:
            return False
        estado_lora["envios"] += 1
        for m in mensajes:
            motor.emergencia(Emergencia(**m["payload"]))
        return True

    nodo = Nodo(
        NODO,
        CUENCA,
        tmp_path / "nodo.sqlite",
        lambda m: motor.procesar([Mensaje(**x) for x in m]) is not None,
        respaldo,
        inicio=INICIO,
    )
    nodo.enlace_activo = False
    nodo.estado.cambiar("tormenta_convectiva", nodo.reloj.timestamp())

    for _ in range(150):
        lectura = nodo.paso()
        if lectura.edge_local_alert.orden >= Nivel.NARANJA.orden:
            break
    assert nodo.emergencia_enviada is Nivel.VERDE
    assert any("no llegó al gateway" in linea for linea in nodo.registro)

    estado_lora["disponible"] = True
    nodo.paso()
    assert nodo.emergencia_enviada.orden >= Nivel.NARANJA.orden
    assert estado_lora["envios"] == 1
    assert motor.estado[CUENCA].nivel.orden >= Nivel.NARANJA.orden


def test_concurrencia_paso_estado_y_control(tmp_path):
    motor = Motor()
    nodo = Nodo(
        NODO,
        CUENCA,
        tmp_path / "nodo.sqlite",
        lambda m: motor.procesar([Mensaje(**x) for x in m]) is not None,
        inicio=INICIO,
    )

    def trabajador_pasos() -> None:
        for _ in range(15):
            nodo.paso()

    def trabajador_lecturas() -> None:
        for _ in range(30):
            res = nodo.resumen()
            assert res["node_id"] == NODO

    def trabajador_control() -> None:
        for i in range(10):
            nodo.aplicar_control(
                escenario="llovizna" if i % 2 == 0 else "normal",
                lluvia_previa_72h_mm=float(i),
            )

    with ThreadPoolExecutor(max_workers=4) as pool:
        futuros = [
            pool.submit(trabajador_pasos),
            pool.submit(trabajador_lecturas),
            pool.submit(trabajador_control),
            pool.submit(trabajador_lecturas),
        ]
        for futuro in futuros:
            futuro.result()

    assert nodo.ultimo_seq() == 14

    with TestClient(crear_app(nodo, escala=60.0)) as cliente:
        r_estado = cliente.get("/estado")
        assert r_estado.status_code == 200
        assert r_estado.json()["node_id"] == NODO

        r_ok = cliente.post("/control", json={"escenario": "tormenta_moderada", "enlace_activo": False})
        assert r_ok.status_code == 200
        assert r_ok.json()["escenario"] == "tormenta_moderada"
        assert r_ok.json()["enlace_activo"] is False

        r_err = cliente.post("/control", json={"escenario": "inexistente"})
        assert r_err.status_code == 422


def test_m2_segunda_tormenta_en_mismo_corte_reemite_lora(tmp_path):
    motor = Motor()
    emergencias: list[Emergencia] = []

    def respaldo(mensajes: list[dict]) -> bool:
        for m in mensajes:
            paquete = Emergencia(**m["payload"])
            emergencias.append(paquete)
            motor.emergencia(paquete)
        return True

    nodo = Nodo(
        NODO,
        CUENCA,
        tmp_path / "m2.sqlite",
        lambda m: motor.procesar([Mensaje(**x) for x in m]) is not None,
        respaldo,
        inicio=INICIO,
    )
    nodo.paso()
    nodo.enlace_activo = False

    # Primera tormenta en corte: llega a ROJO y emite por LoRa.
    nodo.estado.cambiar("tormenta_convectiva", nodo.reloj.timestamp())
    for _ in range(300):
        if nodo.paso().edge_local_alert is Nivel.ROJO:
            break
    assert len(emergencias) >= 1
    envios_primera = len(emergencias)

    # Cesa la lluvia sin recuperar enlace celular hasta volver a VERDE.
    nodo.estado.cambiar("normal", nodo.reloj.timestamp())
    for _ in range(1000):
        if nodo.paso().edge_local_alert is Nivel.VERDE:
            break
    assert nodo.nivel is Nivel.VERDE
    assert nodo.emergencia_enviada is Nivel.VERDE

    # Segunda tormenta dentro del mismo corte: debe volver a emitir paquete LoRa.
    nodo.estado.cambiar("tormenta_convectiva", nodo.reloj.timestamp())
    for _ in range(300):
        if nodo.paso().edge_local_alert is Nivel.ROJO:
            break
    assert len(emergencias) > envios_primera


def test_lecturas_historicas_conservan_island_mode_y_aviso_naranja_sin_baliza(tmp_path):
    lotes_recibidos: list[list[dict]] = []
    motor = Motor()

    def principal(mensajes: list[dict]) -> bool:
        lotes_recibidos.append(mensajes)
        motor.procesar([Mensaje(**m) for m in mensajes])
        return True

    nodo = Nodo(NODO, CUENCA, tmp_path / "isla.sqlite", principal, lambda m: True, inicio=INICIO)
    nodo.paso()
    nodo.enlace_activo = False
    nodo.estado.cambiar("tormenta_convectiva", nodo.reloj.timestamp())
    for _ in range(150):
        lectura = nodo.paso()
        if lectura.edge_local_alert is Nivel.NARANJA:
            break
    assert any(
        "Alerta autónoma NARANJA: paquete de emergencia por LoRa" in linea and "baliza" not in linea
        for linea in nodo.registro
    )

    nodo.enlace_activo = True
    nodo.paso()
    ultimo_lote = lotes_recibidos[-1]
    ndata = [m["payload"] for m in ultimo_lote if m["topic"].endswith(f"/NDATA/{NODO}")]
    historicas = [p for p in ndata if p["is_historical"]]
    vivas = [p for p in ndata if not p["is_historical"]]
    assert len(historicas) >= 1
    assert all(p["connectivity_state"] == Conectividad.ISLA.value for p in historicas)
    assert len(vivas) == 1
    assert vivas[0]["connectivity_state"] == Conectividad.EN_LINEA.value


def test_resumen_no_bloquea_durante_envio_lento(tmp_path):
    en_envio = threading.Event()
    liberar = threading.Event()

    def envio_lento(_mensajes: list[dict]) -> bool:
        en_envio.set()
        assert liberar.wait(timeout=3.0)
        return True

    nodo = Nodo(NODO, CUENCA, tmp_path / "lento.sqlite", envio_lento, inicio=INICIO)
    hilo = threading.Thread(target=nodo.paso)
    hilo.start()
    assert en_envio.wait(timeout=2.0)

    # Mientras el hilo de envío espera a la red, resumen() debe responder sin bloquearse.
    res = nodo.resumen()
    assert res["node_id"] == NODO
    liberar.set()
    hilo.join(timeout=3.0)
    assert not hilo.is_alive()
