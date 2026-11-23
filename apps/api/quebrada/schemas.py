"""Contratos de datos compartidos por los nodos, el backend y el tablero."""

from __future__ import annotations

from enum import Enum

from pydantic import AwareDatetime, BaseModel, Field, field_validator, model_validator

GRUPO = "QUEBRADA"
TIPOS_MENSAJE = frozenset({"NBIRTH", "NDATA"})


class Nivel(str, Enum):
    VERDE = "GREEN"
    AMARILLO = "YELLOW"
    NARANJA = "ORANGE"
    ROJO = "RED"

    @property
    def orden(self) -> int:
        return list(Nivel).index(self)


class Conectividad(str, Enum):
    EN_LINEA = "ONLINE"
    ISLA = "ISLAND_MODE"


class Metricas(BaseModel):
    rain_mm_15m: float = Field(ge=0)
    rain_mm_60m: float = Field(ge=0)
    antecedent_rain_72h_mm: float = Field(ge=0)
    water_level_cm: float
    # Ascenso del nivel en los últimos 15 minutos; se agrega al contrato original porque el semáforo lo usa.
    water_level_rise_15m_cm: float = 0.0
    turbidity_proxy_ntu: float = Field(ge=0)
    battery_soc_pct: float = Field(ge=0, le=100)


class Telemetria(BaseModel):
    node_id: str
    basin_id: str
    seq: int = Field(ge=0)
    timestamp_utc: AwareDatetime
    is_historical: bool = False
    connectivity_state: Conectividad = Conectividad.EN_LINEA
    metrics: Metricas
    edge_local_alert: Nivel = Nivel.VERDE


class Nacimiento(BaseModel):
    """NBIRTH: el nodo anuncia que está en línea."""

    node_id: str
    basin_id: str
    bd_seq: int
    timestamp_utc: AwareDatetime
    keepalive_s: float  # segundos reales sin mensajes tras los cuales el backend lo da por caído
    time_scale: float = 1.0  # segundos simulados por segundo real (1 en campo)


class Emergencia(BaseModel):
    """Paquete corto que el nodo emite por el enlace de respaldo (LoRa) al detectar un umbral crítico."""

    node_id: str
    basin_id: str
    seq: int
    timestamp_utc: AwareDatetime
    edge_local_alert: Nivel
    rain_mm_15m: float
    water_level_rise_15m_cm: float


class Mensaje(BaseModel):
    """Sobre con la semántica de tópicos de Sparkplug B: spBv1.0/<grupo>/<tipo>/<nodo>."""

    topic: str
    payload: dict

    @field_validator("topic")
    @classmethod
    def validar_topic(cls, v: str) -> str:
        partes = v.split("/")
        if (
            len(partes) != 4
            or not all(partes)
            or partes[0] != "spBv1.0"
            or partes[1] != GRUPO
            or partes[2] not in TIPOS_MENSAJE
        ):
            raise ValueError(f"Tópico Sparkplug B inválido: se espera spBv1.0/{GRUPO}/<NBIRTH|NDATA>/<node_id>")
        return v

    @model_validator(mode="after")
    def validar_coincidencia_nodo(self) -> Mensaje:
        nodo_payload = self.payload.get("node_id")
        if nodo_payload is not None and nodo_payload != self.node_id:
            raise ValueError(f"El node_id del payload ({nodo_payload}) no coincide con el tópico ({self.node_id})")
        return self

    @property
    def tipo(self) -> str:
        return self.topic.split("/")[2]

    @property
    def node_id(self) -> str:
        return self.topic.split("/")[3]


def topico(tipo: str, node_id: str) -> str:
    return f"spBv1.0/{GRUPO}/{tipo}/{node_id}"
