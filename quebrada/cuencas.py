"""Atributos morfométricos de las microcuencas, leídos de data/cuencas.geojson."""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from quebrada.hydrology import kirpich_min

DATOS = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class Cuenca:
    basin_id: str
    node_id: str
    localidad: str
    curso: str
    area_km2: float
    largo_cauce_m: float
    pendiente_cauce: float
    largo_estacion_impacto_m: float
    pendiente_estacion_impacto: float

    @property
    def tc_min(self) -> float:
        """Tiempo de concentración de toda la cuenca."""
        return kirpich_min(self.largo_cauce_m, self.pendiente_cauce)

    @property
    def eta_min(self) -> float:
        """Tiempo de arribo estimado desde la estación de cabecera hasta el cruce con la RN 9."""
        return kirpich_min(self.largo_estacion_impacto_m, self.pendiente_estacion_impacto)


@lru_cache
def cargar(ruta: Path = DATOS / "cuencas.geojson") -> dict[str, Cuenca]:
    campos = Cuenca.__dataclass_fields__
    elementos = json.loads(ruta.read_text())["features"]
    cuencas = [Cuenca(**{k: v for k, v in e["properties"].items() if k in campos}) for e in elementos]
    return {c.basin_id: c for c in cuencas}
