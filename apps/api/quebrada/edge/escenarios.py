"""Generador de lluvia, nivel y turbidez de la estación simulada. Los valores no son mediciones."""

import math
from dataclasses import dataclass, field

# Perfil satelital CMORPH (NOAA NCEI) sobre Volcán el 10/01/2017 entre las 11 y 15 UTC (tramos de 30 min).
# Acumulado exacto: 48,6 mm; pico: 25,6 mm/h. Ver docs/fuentes_datos_quebrada_alert.md §3.1.
_VOLCAN_2017_CMORPH_MM_H = (0.4, 4.2, 7.1, 19.7, 25.6, 16.9, 15.5, 7.8)


def _volcan_2017_cmorph(t: float) -> float:
    if t < 0 or t >= 30 * len(_VOLCAN_2017_CMORPH_MM_H):
        return 0.0
    return _VOLCAN_2017_CMORPH_MM_H[int(t // 30)]


# Intensidad de lluvia (mm/h) según los minutos transcurridos desde el inicio del escenario.
ESCENARIOS = {
    "normal": lambda t: 0.0,
    "llovizna": lambda t: 3.0,
    # Tormenta sobre suelo húmedo: sostenida, sin pico convectivo.
    "tormenta_moderada": lambda t: 14.0 if t < 120 else 0.0,
    # Celda convectiva: sube a 130 mm/h en 15 minutos y decae en la hora siguiente.
    "tormenta_convectiva": lambda t: 130.0 * (t / 15 if t < 15 else math.exp(-(t - 15) / 20)) if t < 150 else 0.0,
    # Estimación satelital histórica del alud de Volcán (no es medición pluviométrica en cabecera).
    "volcan_2017_cmorph": _volcan_2017_cmorph,
}

METADATOS_ESCENARIOS: dict[str, dict[str, str]] = {
    "normal": {"etiqueta": "Sin lluvia", "origen": "sintetico", "nota": "Línea base seca para simulación."},
    "llovizna": {"etiqueta": "Llovizna", "origen": "sintetico", "nota": "Lluvia estratiforme continua de 3 mm/h."},
    "tormenta_moderada": {
        "etiqueta": "Tormenta moderada",
        "origen": "sintetico",
        "nota": "Tormenta sostenida de 14 mm/h durante 120 min.",
    },
    "tormenta_convectiva": {
        "etiqueta": "Tormenta convectiva",
        "origen": "sintetico",
        "nota": "Celda convectiva sintética con pico de 130 mm/h a los 15 min.",
    },
    "volcan_2017_cmorph": {
        "etiqueta": "Volcán 2017 (CMORPH)",
        "origen": "estimacion_satelital_cmorph",
        "nota": (
            "Estimación satelital CMORPH 8 km / 30 min del 10/01/2017 (48,6 mm; pico 25,6 mm/h y 6,4 mm/15 min), "
            "no medición en cabecera: iguala el umbral global de Caine (1980) para 15 min (6,36 mm), pero queda "
            "en AMARILLO bajo los umbrales ilustrativos actuales (15 mm/15 min) por suavizado espacial."
        ),
    },
}


@dataclass
class Estado:
    """Respuesta simplificada del cauce: un reservorio lineal que la lluvia llena y que se vacía solo."""

    escenario: str = "normal"
    inicio_s: float = 0.0
    nivel_base_cm: float = 20.0
    almacenado_mm: float = 0.0
    bateria_pct: float = 92.0
    lluvia_previa_72h_mm: float = 0.0
    _extra: dict = field(default_factory=dict)

    def cambiar(self, escenario: str, ahora_s: float) -> None:
        if escenario not in ESCENARIOS:
            raise ValueError(f"Escenario desconocido: {escenario}")
        self.escenario, self.inicio_s = escenario, ahora_s

    def avanzar(self, ahora_s: float, dt_s: float) -> dict:
        """Avanza dt_s segundos y devuelve la lluvia caída (mm), el nivel (cm) y la turbidez (NTU)."""
        minutos = (ahora_s - self.inicio_s) / 60
        intensidad = ESCENARIOS[self.escenario](minutos)
        lluvia = intensidad * dt_s / 3600
        vaciado = 1 - math.exp(-dt_s / 1500)  # constante de recesión de 25 minutos
        self.almacenado_mm += lluvia - self.almacenado_mm * vaciado
        nivel = self.nivel_base_cm + 6.0 * self.almacenado_mm
        turbidez = 40 + 35 * self.almacenado_mm + 4 * intensidad
        consumo = 0.02 if intensidad == 0 else 0.05
        self.bateria_pct = max(5.0, self.bateria_pct - consumo * dt_s / 300)
        return {"lluvia_mm": lluvia, "nivel_cm": nivel, "turbidez_ntu": turbidez}
