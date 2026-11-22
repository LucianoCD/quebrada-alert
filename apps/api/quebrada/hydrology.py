"""Motor hidrológico: semáforo por umbrales y tiempo de arribo. Funciones puras, sin E/S.

Los umbrales son valores de ejemplo, no calibrados con eventos locales.
"""

from dataclasses import dataclass

from quebrada.schemas import Metricas, Nivel


@dataclass(frozen=True)
class Umbrales:
    amarillo_mm_h: float = 10.0
    suelo_saturado_mm_72h: float = 30.0
    lluvia_activa_mm_h: float = 1.0
    naranja_mm_15m: float = 15.0
    naranja_ascenso_cm_15m: float = 30.0
    rojo_mm_15m: float = 25.0
    rojo_ascenso_cm_15m: float = 30.0
    rojo_turbidez_ntu: float = 500.0


UMBRALES = Umbrales()

ACCIONES = {
    Nivel.VERDE: "Monitoreo de rutina.",
    Nivel.AMARILLO: "Avisar a la guardia técnica de la DPRH y verificar el estado de los drenajes urbanos.",
    Nivel.NARANJA: "Pre-alerta a Defensa Civil y Vialidad Nacional; alistar el puesto de corte en la RN 9.",
    Nivel.ROJO: "Recomendar el corte preventivo de la RN 9 y la evacuación de la zona de impacto.",
}


def kirpich_min(largo_m: float, pendiente: float) -> float:
    """Tiempo de concentración de Kirpich (1940) en minutos: 0,0195 · L^0,77 · S^-0,385.

    L es la longitud del cauce en metros y S su pendiente media (m/m). La fórmula se desarrolló para
    cuencas agrícolas pequeñas y describe el escurrimiento de agua, no un flujo de detritos.
    """
    if largo_m <= 0 or pendiente <= 0:
        raise ValueError("La longitud y la pendiente deben ser positivas")
    return 0.0195 * largo_m**0.77 * pendiente**-0.385


def clasificar(m: Metricas, u: Umbrales = UMBRALES) -> Nivel:
    ascenso_brusco = m.water_level_rise_15m_cm > u.rojo_ascenso_cm_15m or m.turbidity_proxy_ntu > u.rojo_turbidez_ntu
    if m.rain_mm_15m > u.rojo_mm_15m and ascenso_brusco:
        return Nivel.ROJO
    if m.rain_mm_15m > u.naranja_mm_15m or m.water_level_rise_15m_cm > u.naranja_ascenso_cm_15m:
        return Nivel.NARANJA
    llueve = m.rain_mm_60m >= u.lluvia_activa_mm_h
    if m.rain_mm_60m >= u.amarillo_mm_h or (m.antecedent_rain_72h_mm > u.suelo_saturado_mm_72h and llueve):
        return Nivel.AMARILLO
    return Nivel.VERDE


def intervalo_muestreo_s(nivel: Nivel) -> int:
    """Segundos entre lecturas: cada 5 minutos en verde (ahorro de batería), cada 30 s en el resto."""
    return 300 if nivel is Nivel.VERDE else 30
