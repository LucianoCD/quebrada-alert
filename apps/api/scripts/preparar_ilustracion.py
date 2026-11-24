"""Genera la ilustración del corredor de la landing a partir de los datos geográficos ya preparados.

Lee el MDE descargado por preparar_geodatos.py (data_raw/mde.tif) y los GeoJSON de docs/data/, y deja en
apps/web/src/assets/ el relieve sombreado (WebP) y un módulo JS con las geometrías ya proyectadas a píxeles,
para que la landing dibuje el mapa sin depender del backend ni de teselas externas.
Requiere: pip install -e ".[geo]"
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from quebrada.hydrology import kirpich_min

RAIZ = Path(__file__).resolve().parents[3]
MDE = RAIZ / "data_raw" / "mde.tif"
DATOS = RAIZ / "docs" / "data"
SALIDA = RAIZ / "apps" / "web" / "src" / "assets"
# Encuadre del corredor Volcán–Tilcara, con margen al este para las etiquetas.
OESTE, SUR, ESTE, NORTE = -65.735, -23.995, -65.205, -23.452
ANCHO = 1200
LOCALIDADES = ("Maimará",)

# Tinte por altura (m s. n. m. -> RGB): fondo de valle oscuro, cumbres claras.
TINTE = [
    (1500, (14, 26, 44)),
    (2600, (20, 36, 60)),
    (3400, (30, 50, 78)),
    (4200, (46, 69, 100)),
    (5000, (80, 104, 135)),
    (5600, (134, 154, 178)),
]
LUZ_CALIDA, SOMBRA_FRIA = (255, 214, 170), (4, 9, 20)


def _suavizar(a: Any, pasadas: int) -> Any:
    import numpy as np

    for _ in range(pasadas):
        b = np.pad(a, 1, mode="edge")
        a = (
            b[:-2, :-2]
            + 2 * b[:-2, 1:-1]
            + b[:-2, 2:]
            + 2 * b[1:-1, :-2]
            + 4 * b[1:-1, 1:-1]
            + 2 * b[1:-1, 2:]
            + b[2:, :-2]
            + 2 * b[2:, 1:-1]
            + b[2:, 2:]
        ) / 16
    return a


def relieve(ancho: int, alto: int) -> Any:
    """Relieve sombreado con tinte hipsométrico, como imagen RGB."""
    import numpy as np
    import rasterio
    from PIL import Image
    from rasterio.enums import Resampling
    from rasterio.windows import from_bounds

    with rasterio.open(MDE) as src:
        ventana = from_bounds(OESTE, SUR, ESTE, NORTE, src.transform)
        z = src.read(1, window=ventana, out_shape=(alto, ancho), resampling=Resampling.cubic).astype("float64")
    z = _suavizar(z, 1)
    metros_px = (NORTE - SUR) * 110_800 / alto
    dy, dx = np.gradient(z, metros_px)

    def sombra(azimut: float, altura: float, exageracion: float) -> Any:
        az, al = math.radians(azimut), math.radians(altura)
        luz = np.array([math.sin(az) * math.cos(al), math.cos(az) * math.cos(al), math.sin(al)])
        # Normal de la superficie (x al este, y al norte, z arriba); las filas crecen hacia el sur.
        nx, ny, nz = -dx * exageracion, dy * exageracion, np.ones_like(z)
        return np.clip((nx * luz[0] + ny * luz[1] + nz * luz[2]) / np.sqrt(nx**2 + ny**2 + nz**2), 0, 1)

    # Luz principal del noroeste más dos de relleno, para que ninguna ladera quede plana.
    luz = 0.6 * sombra(315, 42, 1.6) + 0.25 * sombra(270, 55, 1.6) + 0.15 * sombra(15, 55, 1.6)
    llano = math.sin(math.radians(42)) * 0.6 + math.sin(math.radians(55)) * 0.4
    relativo = luz - llano  # 0 en terreno llano; positivo a la luz, negativo a la sombra
    # Oclusión ambiental barata: los fondos de quebrada quedan más oscuros que su entorno.
    hundido = np.clip((_suavizar(z, 24) - z) / 260, -1, 1)

    cotas = np.array([c for c, _ in TINTE], dtype="float64")
    color = np.stack([np.interp(z, cotas, [rgb[i] for _, rgb in TINTE]) for i in range(3)], axis=-1)
    claro = np.clip(relativo, 0, None)[..., None] * 1.9
    oscuro = np.clip(-relativo * 1.15 + np.clip(hundido, 0, None) * 0.3, 0, 0.7)[..., None]
    color = color * (1 + claro * 0.9) + np.array(LUZ_CALIDA) * claro * 0.16
    color = color * (1 - oscuro) + np.array(SOMBRA_FRIA) * oscuro

    return Image.fromarray(np.clip(color, 0, 255).astype("uint8"), "RGB")


def main() -> None:
    alto = round(
        ANCHO * (NORTE - SUR) * 110_800 / ((ESTE - OESTE) * 111_320 * math.cos(math.radians((SUR + NORTE) / 2)))
    )
    km_px = (NORTE - SUR) * 110.8 / alto

    def px(lon: float, lat: float) -> tuple[float, float]:
        return round((lon - OESTE) / (ESTE - OESTE) * ANCHO, 1), round((NORTE - lat) / (NORTE - SUR) * alto, 1)

    def trazo(coords: list, cerrar: bool = False) -> str:
        puntos = [px(*c[:2]) for c in coords]
        limpio = [
            p for i, p in enumerate(puntos) if i == 0 or math.dist(p, puntos[i - 1]) >= 1.5 or i == len(puntos) - 1
        ]
        return "M" + "L".join(f"{x:g},{y:g}" for x, y in limpio) + ("Z" if cerrar else "")

    def lineas(feature: dict) -> str:
        """Une los tramos de una MultiLineString, descartando los que caen fuera del encuadre."""
        partes = []
        for tramo in feature["geometry"]["coordinates"]:
            dentro = [c for c in tramo if OESTE - 0.02 <= c[0] <= ESTE + 0.02 and SUR - 0.03 <= c[1] <= NORTE + 0.03]
            if len(dentro) >= 2:
                partes.append(trazo(dentro))
        return "".join(partes)

    def leer(nombre: str) -> list:
        return json.loads((DATOS / nombre).read_text(encoding="utf-8"))["features"]

    cauces = {f["properties"]["basin_id"]: f["geometry"]["coordinates"] for f in leer("cauces.geojson")}
    puntos = leer("puntos.geojson")
    contexto = {f["properties"]["tipo"]: f for f in leer("contexto.geojson")}

    def punto(tipo: str, basin_id: str) -> list:
        return next(
            p["geometry"]["coordinates"]
            for p in puntos
            if p["properties"]["tipo"] == tipo and p["properties"].get("basin_id") == basin_id
        )

    cuencas = []
    for f in leer("cuencas.geojson"):
        p = f["properties"]
        cauce, estacion, impacto = (
            cauces[p["basin_id"]],
            punto("estacion", p["basin_id"]),
            punto("impacto", p["basin_id"]),
        )
        # Tramo estación -> RN 9: por ahí baja la onda de crecida que anima la ilustración. El cauce
        # sigue hasta el río Grande, así que se corta en el vértice más próximo al cruce.
        desde = min(range(len(cauce)), key=lambda i: math.dist(cauce[i], estacion))
        hasta = min(range(desde, len(cauce)), key=lambda i: math.dist(cauce[i], impacto))
        cuencas.append(
            {
                "basin_id": p["basin_id"],
                "localidad": p["localidad"],
                "curso": p["curso"],
                "area_km2": p["area_km2"],
                "largo_km": round(p["largo_estacion_impacto_m"] / 1000, 1),
                "pendiente_pct": round(p["pendiente_estacion_impacto"] * 100, 1),
                "cota_estacion_m": p["cota_estacion_m"],
                "eta_min": round(kirpich_min(p["largo_estacion_impacto_m"], p["pendiente_estacion_impacto"])),
                "contorno": trazo(f["geometry"]["coordinates"][0], cerrar=True),
                "cauce": trazo(cauce),
                "tramo": [px(*c) for c in [estacion, *cauce[desde + 1 : hasta], impacto]],
                "estacion": px(*estacion),
                "cruce": px(*impacto),
            }
        )

    SALIDA.mkdir(parents=True, exist_ok=True)
    relieve(ANCHO, alto).save(SALIDA / "corredor-relieve.webp", quality=82, method=6)
    corredor = {
        "ancho": ANCHO,
        "alto": alto,
        "km_px": round(km_px, 5),
        "rn9": lineas(contexto["rn9"]),
        "rio": lineas(contexto["rio"]),
        "localidades": [
            {"nombre": p["properties"]["nombre"], "xy": px(*p["geometry"]["coordinates"])}
            for p in puntos
            if p["properties"]["tipo"] == "localidad" and p["properties"]["nombre"] in LOCALIDADES
        ],
        "cuencas": cuencas,
    }
    cuerpo = json.dumps(corredor, ensure_ascii=False, separators=(",", ":"))
    (SALIDA / "corredor.js").write_text(
        "// Generado por apps/api/scripts/preparar_ilustracion.py a partir de docs/data/. No editar a mano.\n"
        f"export default {cuerpo};\n",
        encoding="utf-8",
    )
    print(f"Ilustración: {ANCHO}x{alto} px, {km_px * 1000:.0f} m/px, {len(cuencas)} cuencas")


if __name__ == "__main__":
    main()
