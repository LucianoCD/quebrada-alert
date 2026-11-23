"""Pruebas de geodatos Terrain-RGB, escenarios históricos y curvas hidrológicas (Issue #8)."""

import importlib.util
from pathlib import Path

import pytest
from quebrada import hydrology
from quebrada.edge.escenarios import ESCENARIOS, METADATOS_ESCENARIOS

RAIZ = Path(__file__).resolve().parents[1]


def _cargar_preparar_geodatos():
    ruta = RAIZ / "apps" / "api" / "scripts" / "preparar_geodatos.py"
    spec = importlib.util.spec_from_file_location("preparar_geodatos", ruta)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_escenario_volcan_2017_cmorph_acumulado_y_pico():
    fn = ESCENARIOS["volcan_2017_cmorph"]
    assert fn(-1.0) == 0.0
    assert fn(240.0) == 0.0
    intensidades = [fn(float(m)) for m in range(240)]
    acumulado_mm = sum(intensidades) / 60.0
    assert acumulado_mm == pytest.approx(48.6, abs=0.05)
    assert max(intensidades) == pytest.approx(25.6)
    assert fn(120.0) == pytest.approx(25.6)
    meta = METADATOS_ESCENARIOS["volcan_2017_cmorph"]
    assert meta["origen"] == "estimacion_satelital_cmorph"
    assert "CMORPH" in meta["etiqueta"]


def test_escenarios_previos_conservados():
    for clave in ("normal", "llovizna", "tormenta_moderada", "tormenta_convectiva"):
        assert clave in ESCENARIOS
        assert clave in METADATOS_ESCENARIOS
        assert ESCENARIOS[clave](10.0) >= 0.0


def test_umbrales_por_cuenca_y_curvas_referencia():
    for cuenca in (
        "CUENCA_ARROYO_MEDIO",
        "CUENCA_TUMBAYA_GRANDE",
        "CUENCA_PURMAMARCA",
        "CUENCA_HUASAMAYO",
    ):
        assert hydrology.umbrales_para(cuenca) == hydrology.UMBRALES
    assert hydrology.umbrales_para(None) == hydrology.UMBRALES
    assert hydrology.umbrales_para("DESCONOCIDA") == hydrology.UMBRALES

    assert hydrology.intensidad_caine_mm_h(1.0) == pytest.approx(14.82)
    assert hydrology.intensidad_guzzetti_mm_h(1.0) == pytest.approx(2.20)
    assert hydrology.intensidad_caine_mm_h(0.5) > hydrology.intensidad_caine_mm_h(2.0)
    with pytest.raises(ValueError):
        hydrology.intensidad_caine_mm_h(0.0)
    with pytest.raises(ValueError):
        hydrology.intensidad_guzzetti_mm_h(-1.0)


def test_terrain_rgb_roundtrip_escalar():
    mod = _cargar_preparar_geodatos()
    for cota in (-10.0, 0.0, 2071.0, 2591.0, 4585.0):
        r, g, b = mod.codificar_elevacion_rgb(cota)
        assert all(0 <= canal <= 255 for canal in (r, g, b))
        assert mod.decodificar_elevacion_rgb(r, g, b) == pytest.approx(cota, abs=0.1)

    for invalida in (-9999.0, float("nan")):
        r, g, b = mod.codificar_elevacion_rgb(invalida)
        assert mod.decodificar_elevacion_rgb(r, g, b) == pytest.approx(0.0, abs=0.1)


def test_terrain_rgb_matriz_numpy():
    np = pytest.importorskip("numpy")
    mod = _cargar_preparar_geodatos()
    mde = np.array([[2071.3, 4585.0], [-9999.0, np.nan]], dtype="float32")
    rgb = mod.codificar_terrain_rgb(mde, nodata=-9999.0)
    assert rgb.dtype == np.uint8
    assert rgb.shape == (2, 2, 3)
    decodificado = mod.decodificar_terrain_rgb(rgb)
    assert decodificado[0, 0] == pytest.approx(2071.3, abs=0.1)
    assert decodificado[0, 1] == pytest.approx(4585.0, abs=0.1)
    assert decodificado[1, 0] == pytest.approx(0.0, abs=0.1)
    assert decodificado[1, 1] == pytest.approx(0.0, abs=0.1)
