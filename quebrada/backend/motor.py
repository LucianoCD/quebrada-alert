"""Ingesta, reconciliación y motor de alertas del centro de comando.

Todas las lecturas se guardan en DuckDB. Solo la telemetría en vivo y los paquetes de emergencia
cambian el semáforo: las lecturas recuperadas tras un corte (is_historical) completan la serie
pero no disparan alertas.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import duckdb

from quebrada import cuencas, hydrology
from quebrada.schemas import Emergencia, Mensaje, Nacimiento, Nivel, Telemetria

ESQUEMA = """
create table if not exists telemetria (
    node_id varchar, basin_id varchar, seq bigint, ts timestamptz, is_historical boolean,
    rain_mm_15m double, rain_mm_60m double, antecedent_rain_72h_mm double, water_level_cm double,
    water_level_rise_15m_cm double, turbidity_proxy_ntu double, battery_soc_pct double,
    edge_local_alert varchar, recibido timestamptz default now(),
    primary key (node_id, seq)
);
create table if not exists eventos (
    id bigint primary key, ts timestamptz, basin_id varchar, node_id varchar, tipo varchar,
    nivel varchar, origen varchar, detalle varchar
);
"""


@dataclass
class EstadoNodo:
    node_id: str
    basin_id: str
    en_linea: bool = False
    keepalive_s: float = 900.0
    escala: float = 1.0
    visto: float = 0.0  # reloj monótono del servidor en el último mensaje
    ultimo_ts: datetime | None = None
    reloj_ts: datetime | None = None  # marca más reciente recibida por cualquier enlace
    reloj_visto: float = 0.0
    ultima: dict | None = None
    recuperadas: int = 0


@dataclass
class EstadoCuenca:
    basin_id: str
    nivel: Nivel = Nivel.VERDE
    origen: str = "sin datos"  # telemetría en vivo o paquete de emergencia
    desde: datetime | None = None
    arribo_estimado: datetime | None = None
    eventos: list = field(default_factory=list)


class Motor:
    def __init__(self, ruta_db: str = ":memory:", reloj=time.monotonic):
        self.db = duckdb.connect(ruta_db)
        self.db.execute(ESQUEMA)
        self.reloj = reloj
        self.cuencas = cuencas.cargar()
        self.estado = {c: EstadoCuenca(c) for c in self.cuencas}
        self.nodos = {c.node_id: EstadoNodo(c.node_id, c.basin_id) for c in self.cuencas.values()}
        self._id = self.db.execute("select coalesce(max(id), 0) from eventos").fetchone()[0]
        # Al reabrir una base existente se reconstruye el semáforo a partir de los eventos guardados.
        consulta = "select basin_id, nivel, ts, origen from eventos where tipo in ('ALERTA', 'DESCENSO') order by id"
        for basin_id, nivel, ts, origen in self.db.execute(consulta).fetchall():
            if basin_id in self.estado:
                self._transicion(basin_id, Nivel(nivel), ts, origen)

    # --- entrada --------------------------------------------------------------------------

    def procesar(self, mensajes: list[Mensaje]) -> dict:
        """Procesa un lote del enlace principal. Devuelve cuántas lecturas eran nuevas y cuántas repetidas."""
        nuevas = repetidas = 0
        recuperadas: dict[str, list[Telemetria]] = {}
        for m in mensajes:
            if m.tipo == "NBIRTH":
                self._nacimiento(Nacimiento(**m.payload))
            elif m.tipo == "NDATA":
                lectura = Telemetria(**m.payload)
                nodo = self._nodo(lectura.node_id, lectura.basin_id)
                if not self._guardar(lectura):
                    repetidas += 1
                    continue
                nuevas += 1
                nodo.visto = self.reloj()
                self._marcar(nodo, lectura.timestamp_utc)
                if lectura.is_historical:
                    recuperadas.setdefault(lectura.node_id, []).append(lectura)
                else:
                    self._en_vivo(nodo, lectura)
            else:
                raise ValueError(f"Tipo de mensaje no admitido: {m.tipo}")
        for node_id, lecturas in recuperadas.items():
            self._recuperacion(self.nodos[node_id], lecturas)
        return {"nuevas": nuevas, "repetidas": repetidas}

    def emergencia(self, paquete: Emergencia) -> None:
        """Paquete del enlace de respaldo: sube el semáforo aunque el enlace principal esté caído."""
        self._marcar(self._nodo(paquete.node_id, paquete.basin_id), paquete.timestamp_utc)
        detalle = f"Paquete de emergencia LoRa: {paquete.rain_mm_15m:.1f} mm en 15 min"
        self._nivel(paquete.basin_id, paquete.node_id, paquete.edge_local_alert, paquete.timestamp_utc,
                    "emergencia", detalle, solo_subir=True)  # fmt: skip

    def vigilar(self) -> list[str]:
        """Da por caídos (NDEATH) los nodos que superaron su tiempo de vida sin mensajes."""
        caidos = []
        for nodo in self.nodos.values():
            if nodo.en_linea and self.reloj() - nodo.visto > nodo.keepalive_s:
                nodo.en_linea = False
                caidos.append(nodo.node_id)
                self._evento(self.hora_estimada(nodo), nodo.basin_id, nodo.node_id, "NDEATH", None, "servidor",
                             "Sin mensajes del nodo: enlace principal caído")  # fmt: skip
        return caidos

    # --- reglas ---------------------------------------------------------------------------

    def _nodo(self, node_id: str, basin_id: str) -> EstadoNodo:
        if basin_id not in self.estado:
            raise ValueError(f"Cuenca desconocida: {basin_id}")
        return self.nodos.setdefault(node_id, EstadoNodo(node_id, basin_id))

    def _marcar(self, nodo: EstadoNodo, ts: datetime) -> None:
        if nodo.reloj_ts is None or ts > nodo.reloj_ts:
            nodo.reloj_ts, nodo.reloj_visto = ts, self.reloj()

    def _nacimiento(self, n: Nacimiento) -> None:
        nodo = self._nodo(n.node_id, n.basin_id)
        self._marcar(nodo, n.timestamp_utc)
        nodo.keepalive_s, nodo.escala, nodo.visto = n.keepalive_s, n.time_scale, self.reloj()
        if not nodo.en_linea:
            nodo.en_linea = True
            self._evento(n.timestamp_utc, n.basin_id, n.node_id, "NBIRTH", None, "nodo", "Nodo en línea")

    def _guardar(self, x: Telemetria) -> bool:
        m = x.metrics
        fila = self.db.execute(
            "insert into telemetria values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now()) "
            "on conflict do nothing returning seq",
            [
                x.node_id,
                x.basin_id,
                x.seq,
                x.timestamp_utc,
                x.is_historical,
                m.rain_mm_15m,
                m.rain_mm_60m,
                m.antecedent_rain_72h_mm,
                m.water_level_cm,
                m.water_level_rise_15m_cm,
                m.turbidity_proxy_ntu,
                m.battery_soc_pct,
                x.edge_local_alert.value,
            ],  # fmt: skip
        ).fetchone()
        return fila is not None

    def _en_vivo(self, nodo: EstadoNodo, x: Telemetria) -> None:
        if nodo.ultimo_ts and x.timestamp_utc < nodo.ultimo_ts:
            return  # llegó fuera de orden: queda guardada, pero no pisa un estado más reciente
        if not nodo.en_linea:
            self._evento(
                x.timestamp_utc, x.basin_id, x.node_id, "EN_LINEA", None, "nodo", "El nodo volvió a transmitir"
            )
        nodo.en_linea, nodo.ultimo_ts, nodo.ultima = True, x.timestamp_utc, x.model_dump(mode="json")
        # El servidor recalcula el semáforo con las mismas reglas que el nodo.
        nivel = hydrology.clasificar(x.metrics)
        m = x.metrics
        detalle = f"{m.rain_mm_15m:.1f} mm en 15 min, ascenso de {m.water_level_rise_15m_cm:.0f} cm en 15 min"
        self._nivel(x.basin_id, x.node_id, nivel, x.timestamp_utc, "telemetría en vivo", detalle)

    def _recuperacion(self, nodo: EstadoNodo, lecturas: list[Telemetria]) -> None:
        nodo.recuperadas += len(lecturas)
        peor = max(lecturas, key=lambda x: x.edge_local_alert.orden)
        detalle = (
            f"{len(lecturas)} lecturas recuperadas del búfer local (seq {lecturas[0].seq} a {lecturas[-1].seq}); "
            f"nivel local máximo durante el corte: {peor.edge_local_alert.name} a las "
            f"{peor.timestamp_utc:%H:%M} UTC. No genera alerta."
        )
        self._evento(lecturas[-1].timestamp_utc, nodo.basin_id, nodo.node_id, "RECUPERACION", None, "nodo", detalle)

    def _nivel(self, basin_id, node_id, nivel: Nivel, ts: datetime, origen: str, detalle: str,
               solo_subir: bool = False) -> None:  # fmt: skip
        e = self.estado[basin_id]
        if nivel == e.nivel or (solo_subir and nivel.orden < e.nivel.orden):
            if nivel == e.nivel and not solo_subir:
                e.origen = origen
            return
        sube = nivel.orden > e.nivel.orden
        self._transicion(basin_id, nivel, ts, origen)
        self._evento(ts, basin_id, node_id, "ALERTA" if sube else "DESCENSO", nivel, origen, detalle)

    def _transicion(self, basin_id: str, nivel: Nivel, ts: datetime, origen: str) -> None:
        e = self.estado[basin_id]
        critico, era_critico = nivel.orden >= Nivel.NARANJA.orden, e.nivel.orden >= Nivel.NARANJA.orden
        if critico and not era_critico:
            e.arribo_estimado = ts + timedelta(minutes=self.cuencas[basin_id].eta_min)
        elif not critico:
            e.arribo_estimado = None
        e.nivel, e.origen, e.desde = nivel, origen, ts

    def _evento(self, ts, basin_id, node_id, tipo, nivel: Nivel | None, origen, detalle) -> None:
        self._id += 1
        fila = [self._id, ts, basin_id, node_id, tipo, nivel.value if nivel else None, origen, detalle]
        self.db.execute("insert into eventos values (?, ?, ?, ?, ?, ?, ?, ?)", fila)

    # --- consulta -------------------------------------------------------------------------

    def hora_estimada(self, nodo: EstadoNodo) -> datetime | None:
        """Hora del nodo estimada por el servidor: última marca recibida más el tiempo transcurrido."""
        if nodo.reloj_ts is None:
            return None
        return nodo.reloj_ts + timedelta(seconds=(self.reloj() - nodo.reloj_visto) * nodo.escala)

    def eventos(self, limite: int = 40, basin_id: str | None = None) -> list[dict]:
        filtro = "where basin_id = ?" if basin_id else ""
        filas = self.db.execute(
            f"select id, ts, basin_id, node_id, tipo, nivel, origen, detalle from eventos {filtro} "
            "order by id desc limit ?",
            ([basin_id] if basin_id else []) + [limite],
        ).fetchall()
        claves = ["id", "ts", "basin_id", "node_id", "tipo", "nivel", "origen", "detalle"]
        return [dict(zip(claves, [f[0], f[1].isoformat(), *f[2:]], strict=True)) for f in filas]

    def historia(self, node_id: str, limite: int = 2000) -> list[dict]:
        filas = self.db.execute(
            "select seq, ts, is_historical, rain_mm_15m, rain_mm_60m, water_level_cm, turbidity_proxy_ntu, "
            "edge_local_alert from (select * from telemetria where node_id = ? order by seq desc limit ?) "
            "order by seq",
            [node_id, limite],
        ).fetchall()
        claves = ["seq", "ts", "is_historical", "rain_mm_15m", "rain_mm_60m", "water_level_cm",
                  "turbidity_proxy_ntu", "edge_local_alert"]  # fmt: skip
        return [dict(zip(claves, [f[0], f[1].isoformat(), *f[2:]], strict=True)) for f in filas]

    def huecos(self, node_id: str) -> int:
        """Cantidad de números de secuencia faltantes entre el primero y el último recibidos."""
        consulta = "select coalesce(max(seq) - min(seq) + 1 - count(*), 0) from telemetria where node_id = ?"
        return self.db.execute(consulta, [node_id]).fetchone()[0]

    def resumen(self) -> dict:
        salida = []
        for c in self.cuencas.values():
            e, nodo = self.estado[c.basin_id], self.nodos[c.node_id]
            ahora = self.hora_estimada(nodo)
            restante = None
            if e.arribo_estimado and ahora:
                restante = (e.arribo_estimado - ahora).total_seconds() / 60
            salida.append({
                "basin_id": c.basin_id, "localidad": c.localidad, "curso": c.curso, "nivel": e.nivel.value,
                "origen": e.origen, "desde": e.desde.isoformat() if e.desde else None,
                "accion": hydrology.ACCIONES[e.nivel], "eta_min": round(c.eta_min, 1), "tc_min": round(c.tc_min, 1),
                "arribo_estimado": e.arribo_estimado.isoformat() if e.arribo_estimado else None,
                "minutos_restantes": round(restante, 1) if restante is not None else None,
                "nodo": {
                    "node_id": nodo.node_id, "en_linea": nodo.en_linea, "ultima": nodo.ultima,
                    "hora_estimada": ahora.isoformat() if ahora else None, "escala": nodo.escala,
                    "recuperadas": nodo.recuperadas, "huecos": self.huecos(nodo.node_id),
                },
            })  # fmt: skip
        return {"cuencas": salida, "eventos": self.eventos()}

    def parte(self, basin_id: str) -> str:
        """Parte de situación en texto, para adjuntar a la comunicación con los organismos."""
        c, e = self.cuencas[basin_id], self.estado[basin_id]
        nodo = self.nodos[c.node_id]
        m = (nodo.ultima or {}).get("metrics", {})
        lineas = [
            "PARTE DE SITUACIÓN - QuebradaAlert (DEMOSTRACIÓN CON DATOS SIMULADOS)",
            f"Cuenca: {c.curso} ({c.localidad}) - {c.area_km2} km2",
            f"Nivel: {e.nivel.name} desde {e.desde:%Y-%m-%d %H:%M} UTC" if e.desde else f"Nivel: {e.nivel.name}",
            f"Origen del dato: {e.origen}",
            f"Estación {c.node_id}: {'en línea' if nodo.en_linea else 'sin enlace principal'}",
        ]
        if m:
            lineas.append(f"Lluvia: {m['rain_mm_15m']} mm en 15 min, {m['rain_mm_60m']} mm en 60 min, "
                          f"{m['antecedent_rain_72h_mm']} mm en 72 h")  # fmt: skip
            lineas.append(f"Nivel del cauce: {m['water_level_cm']} cm (ascenso de {m['water_level_rise_15m_cm']} cm "
                          "en 15 min)")  # fmt: skip
        if e.arribo_estimado:
            lineas.append(f"Arribo estimado a la RN 9: {e.arribo_estimado:%H:%M} UTC "
                          f"(Kirpich, {c.eta_min:.0f} min desde la estación; valor orientativo)")  # fmt: skip
        lineas += [f"Recomendación: {hydrology.ACCIONES[e.nivel]}",
                   "La decisión de corte o evacuación corresponde a Defensa Civil, la DPRH y Vialidad Nacional.",
                   "", "Últimos eventos:"]  # fmt: skip
        lineas += [
            f"  {x['ts'][:19]} {x['tipo']} {x['nivel'] or ''} {x['detalle']}" for x in self.eventos(10, basin_id)
        ]
        return "\n".join(lineas)
