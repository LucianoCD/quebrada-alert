"""Contratos de datos compartidos por los nodos, el backend y el tablero."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

GRUPO = "QUEBRADA"


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
    timestamp_utc: datetime
    is_historical: bool = False
    connectivity_state: Conectividad = Conectividad.EN_LINEA
    metrics: Metricas
    edge_local_alert: Nivel = Nivel.VERDE


class Nacimiento(BaseModel):
    """NBIRTH: el nodo anuncia que está en línea."""

    node_id: str
    basin_id: str
    bd_seq: int
    timestamp_utc: datetime
    keepalive_s: float  # segundos reales sin mensajes tras los cuales el backend lo da por caído
    time_scale: float = 1.0  # segundos simulados por segundo real (1 en campo)


class Emergencia(BaseModel):
    """Paquete corto que el nodo emite por el enlace de respaldo (LoRa) al detectar un umbral crítico."""

    node_id: str
    basin_id: str
    seq: int
    timestamp_utc: datetime
    edge_local_alert: Nivel
    rain_mm_15m: float
    water_level_rise_15m_cm: float


class Mensaje(BaseModel):
    """Sobre con la semántica de tópicos de Sparkplug B: spBv1.0/<grupo>/<tipo>/<nodo>."""

    topic: str
    payload: dict

    @property
    def tipo(self) -> str:
        return self.topic.split("/")[2]


def topico(tipo: str, node_id: str) -> str:
    return f"spBv1.0/{GRUPO}/{tipo}/{node_id}"
