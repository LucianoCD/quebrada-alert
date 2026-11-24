"""Nodo de cabecera: mide, guarda en su SQLite, evalúa el semáforo localmente y transmite cuando puede.

Sin enlace entra en ISLAND_MODE: sigue registrando con número de secuencia y, al volver la
conexión, vacía la cola marcando los registros atrasados con is_historical.
"""

import json
import sqlite3
import threading
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from quebrada import hydrology
from quebrada.edge.escenarios import ESCENARIOS, Estado
from quebrada.schemas import Conectividad, Emergencia, Metricas, Nacimiento, Nivel, Telemetria, topico

ESQUEMA = """
create table if not exists lecturas (
    seq integer primary key,
    ts text not null,
    lluvia_mm real not null,
    nivel_cm real not null,
    carga text not null,
    enviado integer not null default 0
);
create table if not exists meta (clave text primary key, valor text not null);
"""

# Una función de envío recibe una lista de mensajes {topic, payload} y devuelve True si el backend confirmó.
Envio = Callable[[list[dict]], bool]


class Nodo:
    def __init__(
        self,
        node_id: str,
        basin_id: str,
        ruta_db: Path | str,
        enviar: Envio,
        enviar_respaldo: Envio | None = None,
        inicio: datetime | None = None,
        lluvia_previa_72h_mm: float = 0.0,
        keepalive_s: float = 900.0,
        escala_tiempo: float = 1.0,
        lote: int = 200,
    ):
        self.node_id, self.basin_id = node_id, basin_id
        self.enviar, self.enviar_respaldo = enviar, enviar_respaldo
        self.keepalive_s, self.escala_tiempo, self.lote = keepalive_s, escala_tiempo, lote
        self.db = sqlite3.connect(ruta_db, check_same_thread=False)
        self.db.execute("pragma journal_mode=wal")
        self.db.execute("pragma synchronous=normal")
        self.db.executescript(ESQUEMA)
        self.reloj = inicio or datetime.now(timezone.utc)
        ultima = self.db.execute("select max(ts) from lecturas").fetchone()[0]
        if ultima:  # al reanudar, el reloj no retrocede respecto de lo ya guardado
            iso = f"{ultima[:-1]}+00:00" if ultima.endswith("Z") else ultima
            self.reloj = max(self.reloj, datetime.fromisoformat(iso))
        self.estado = Estado(lluvia_previa_72h_mm=lluvia_previa_72h_mm)
        self.enlace_activo = True  # enlace principal (celular)
        self.respaldo_activo = True  # enlace de respaldo de corto alcance (LoRa)
        self.conectividad = Conectividad.EN_LINEA
        self.nivel = Nivel.VERDE
        self.baliza = False
        self.nacido = False
        self.emergencia_enviada = Nivel.VERDE
        self.registro: list[str] = []
        self.ultima: Telemetria | None = None
        self._lock = threading.RLock()
        self._tx_lock = threading.Lock()

    # --- almacenamiento local -------------------------------------------------------------

    def _meta(self, clave: str, defecto: int = 0) -> int:
        fila = self.db.execute("select valor from meta where clave = ?", (clave,)).fetchone()
        return int(fila[0]) if fila else defecto

    def _guardar_meta(self, clave: str, valor: int) -> None:
        self.db.execute("insert or replace into meta values (?, ?)", (clave, str(valor)))

    def en_cola(self) -> int:
        with self._lock:
            return self.db.execute("select count(*) from lecturas where enviado = 0").fetchone()[0]

    def ultimo_seq(self) -> int:
        with self._lock:
            return self.db.execute("select coalesce(max(seq), -1) from lecturas").fetchone()[0]

    def _suma_lluvia(self, minutos: float) -> float:
        desde = (self.reloj - timedelta(minutes=minutos)).isoformat()
        consulta = "select coalesce(sum(lluvia_mm), 0) from lecturas where ts > ?"
        return self.db.execute(consulta, (desde,)).fetchone()[0]

    def _nivel_hace(self, minutos: float) -> float | None:
        hasta = (self.reloj - timedelta(minutes=minutos)).isoformat()
        consulta = "select nivel_cm from lecturas where ts <= ? order by seq desc limit 1"
        fila = self.db.execute(consulta, (hasta,)).fetchone()
        return fila[0] if fila else None

    def _anotar(self, texto: str) -> None:
        self.registro.append(f"{self.reloj:%H:%M:%S} {texto}")
        del self.registro[:-50]

    # --- ciclo de medición ----------------------------------------------------------------

    def paso(self) -> Telemetria:
        """Avanza el reloj un intervalo de muestreo, mide, evalúa y transmite. Devuelve la lectura."""
        with self._lock:
            dt = hydrology.intervalo_muestreo_s(self.nivel)
            self.reloj += timedelta(seconds=dt)
            medido = self.estado.avanzar(self.reloj.timestamp(), dt)
            previo = self._nivel_hace(15)
            metricas = Metricas(
                rain_mm_15m=round(self._suma_lluvia(15) + medido["lluvia_mm"], 2),
                rain_mm_60m=round(self._suma_lluvia(60) + medido["lluvia_mm"], 2),
                antecedent_rain_72h_mm=round(
                    self.estado.lluvia_previa_72h_mm + self._suma_lluvia(72 * 60) + medido["lluvia_mm"], 2
                ),
                water_level_cm=round(medido["nivel_cm"], 1),
                water_level_rise_15m_cm=round(max(0.0, medido["nivel_cm"] - previo), 1) if previo is not None else 0.0,
                turbidity_proxy_ntu=round(medido["turbidez_ntu"], 1),
                battery_soc_pct=round(self.estado.bateria_pct, 1),
            )
            anterior = self.nivel
            self.nivel = hydrology.clasificar(metricas, hydrology.umbrales_para(self.basin_id))
            if self.nivel != anterior:
                self._anotar(f"Semáforo local: {anterior.name} -> {self.nivel.name}")
            if self.nivel is Nivel.VERDE:
                self.emergencia_enviada = Nivel.VERDE
            self.baliza = self.nivel is Nivel.ROJO
            seq = self.ultimo_seq() + 1
            lectura = Telemetria(
                node_id=self.node_id,
                basin_id=self.basin_id,
                seq=seq,
                timestamp_utc=self.reloj,
                connectivity_state=self.conectividad,
                metrics=metricas,
                edge_local_alert=self.nivel,
            )
            with self.db:
                self.db.execute(
                    "insert into lecturas (seq, ts, lluvia_mm, nivel_cm, carga) values (?, ?, ?, ?, ?)",
                    (seq, self.reloj.isoformat(), medido["lluvia_mm"], medido["nivel_cm"], lectura.model_dump_json()),
                )
            self.ultima = lectura

        self.sincronizar()

        with self._lock:
            if self.conectividad is Conectividad.ISLA and lectura.connectivity_state is not Conectividad.ISLA:
                lectura = lectura.model_copy(update={"connectivity_state": Conectividad.ISLA})
                self.ultima = lectura
        self._emergencia(lectura)
        return lectura

    # --- transmisión ----------------------------------------------------------------------

    def _transmitir_sin_lock(self, mensajes: list[dict]) -> bool:
        try:
            return bool(self.enviar(mensajes))
        except Exception:
            return False

    def sincronizar(self) -> int:
        """Envía lo pendiente en orden de secuencia. Devuelve cuántas lecturas confirmó el backend."""
        with self._tx_lock:
            confirmadas = 0
            with self._lock:
                estaba_en_isla = self.conectividad is Conectividad.ISLA
            anoto_reconexion = False
            while True:
                with self._lock:
                    filas = self.db.execute(
                        "select seq, carga from lecturas where enviado = 0 order by seq limit ?", (self.lote,)
                    ).fetchall()
                    if not filas:
                        break
                    ultimo = self.ultimo_seq()
                    enlace = self.enlace_activo
                    mensajes = []
                    if not self.nacido:
                        mensajes.append({"topic": topico("NBIRTH", self.node_id), "payload": self._nacimiento()})
                    for seq, carga in filas:
                        datos = json.loads(carga)
                        # Solo la lectura recién tomada es telemetría en vivo; las atrasadas conservan ISLAND_MODE.
                        datos["is_historical"] = seq != ultimo
                        datos["connectivity_state"] = (
                            Conectividad.ISLA.value if seq != ultimo else Conectividad.EN_LINEA.value
                        )
                        mensajes.append({"topic": topico("NDATA", self.node_id), "payload": datos})

                ok = self._transmitir_sin_lock(mensajes) if enlace else False

                with self._lock:
                    if not ok:
                        if self.conectividad is Conectividad.EN_LINEA:
                            self._anotar("Sin enlace: paso a ISLAND_MODE, las lecturas quedan en la cola local")
                        self.conectividad, self.nacido = Conectividad.ISLA, False
                        return confirmadas
                    with self.db:
                        self.db.executemany("update lecturas set enviado = 1 where seq = ?", [(s,) for s, _ in filas])
                    if estaba_en_isla and not anoto_reconexion:
                        self._anotar("Enlace restablecido: vaciando la cola local")
                        anoto_reconexion = True
                    if not self.nacido:
                        self._guardar_meta("bd_seq", self._meta("bd_seq") + 1)
                        self.db.commit()
                        self.nacido = True
                    confirmadas += len(filas)
            with self._lock:
                if confirmadas > 0:
                    self.conectividad = Conectividad.EN_LINEA
                    self.emergencia_enviada = Nivel.VERDE
            return confirmadas

    def _nacimiento(self) -> dict:
        return Nacimiento(
            node_id=self.node_id,
            basin_id=self.basin_id,
            bd_seq=self._meta("bd_seq"),
            timestamp_utc=self.reloj,
            keepalive_s=self.keepalive_s,
            time_scale=self.escala_tiempo,
        ).model_dump(mode="json")

    def _emergencia(self, lectura: Telemetria) -> None:
        """Aislado y con umbral crítico: emite un paquete corto por el enlace de respaldo, una vez por nivel."""
        with self._lock:
            critico = self.nivel.orden >= Nivel.NARANJA.orden
            if self.conectividad is not Conectividad.ISLA or not critico:
                return
            if self.nivel.orden <= self.emergencia_enviada.orden:
                return
            nivel_objetivo = self.nivel
            usar_respaldo = bool(self.respaldo_activo and self.enviar_respaldo)
            paquete = Emergencia(
                node_id=self.node_id,
                basin_id=self.basin_id,
                seq=lectura.seq,
                timestamp_utc=lectura.timestamp_utc,
                edge_local_alert=nivel_objetivo,
                rain_mm_15m=lectura.metrics.rain_mm_15m,
                water_level_rise_15m_cm=lectura.metrics.water_level_rise_15m_cm,
            ).model_dump(mode="json")
            if nivel_objetivo is Nivel.ROJO:
                self._anotar(f"Alerta autónoma {nivel_objetivo.name}: baliza local y paquete de emergencia por LoRa")
            else:
                self._anotar(f"Alerta autónoma {nivel_objetivo.name}: paquete de emergencia por LoRa")

        entregado = False
        if usar_respaldo and self.enviar_respaldo is not None:
            try:
                entregado = bool(self.enviar_respaldo([{"topic": topico("NDATA", self.node_id), "payload": paquete}]))
            except Exception:
                entregado = False

        with self._lock:
            if entregado:
                if nivel_objetivo.orden > self.emergencia_enviada.orden and self.nivel is not Nivel.VERDE:
                    self.emergencia_enviada = nivel_objetivo
            else:
                self._anotar("El paquete de emergencia no llegó al gateway; se reintenta en la próxima lectura")

    def aplicar_control(
        self,
        *,
        escenario: str | None = None,
        enlace_activo: bool | None = None,
        respaldo_activo: bool | None = None,
        lluvia_previa_72h_mm: float | None = None,
    ) -> dict:
        """Aplica órdenes de control de la demo de forma segura frente a concurrencia."""
        with self._lock:
            if escenario is not None:
                if escenario not in ESCENARIOS:
                    raise ValueError(f"Escenario desconocido: {escenario}")
                self.estado.cambiar(escenario, self.reloj.timestamp())
            if enlace_activo is not None:
                self.enlace_activo = enlace_activo
            if respaldo_activo is not None:
                self.respaldo_activo = respaldo_activo
            if lluvia_previa_72h_mm is not None:
                self.estado.lluvia_previa_72h_mm = max(0.0, lluvia_previa_72h_mm)
            return self.resumen()

    def resumen(self) -> dict:
        with self._lock:
            return {
                "node_id": self.node_id,
                "basin_id": self.basin_id,
                "connectivity_state": self.conectividad.value,
                "enlace_activo": self.enlace_activo,
                "respaldo_activo": self.respaldo_activo,
                "en_cola": self.en_cola(),
                "ultimo_seq": self.ultimo_seq(),
                "edge_local_alert": self.nivel.value,
                "baliza": self.baliza,
                "escenario": self.estado.escenario,
                "reloj": self.reloj.isoformat(),
                "ultima": self.ultima.model_dump(mode="json") if self.ultima else None,
                "registro": self.registro[-12:],
            }
