"""Genera los datos geográficos de la demo a partir de fuentes abiertas (requiere red; se corre una vez).

- Copernicus DEM GLO-30 (AWS Open Data): microcuencas, cauce principal, longitud, pendiente y teselas Terrain-RGB.
- OpenStreetMap: traza de la RN 9, cursos de agua con nombre y localidades.

Deja en docs/data/ los GeoJSON, el relieve sombreado y las teselas Terrain-RGB que usan el backend y el tablero
sin conexión.
Requiere: pip install -e ".[geo]"
"""

from __future__ import annotations

import json
import math
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[3]
CRUDO = RAIZ / "data_raw"
SALIDA = RAIZ / "docs" / "data"
OESTE, SUR, ESTE, NORTE = -65.75, -24.05, -65.25, -23.45
UTM = "EPSG:32719"
TESELA = "Copernicus_DSM_COG_10_S24_00_W066_00_DEM"
# Área máxima admitida al ajustar la salida: evita engancharse al río Grande, que pasa al lado.
AREA_MAX_KM2 = 1500

# Orden de pysheds: N, NE, E, SE, S, SO, O, NO.
DIRECCIONES = {64: (-1, 0), 128: (-1, 1), 1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1)}

CUENCAS = [
    {"id": "CUENCA_ARROYO_MEDIO", "nodo": "EST-VOLCAN-CAB01", "localidad": "Volcán", "cursos": ["Arroyo del Medio"]},
    {
        "id": "CUENCA_TUMBAYA_GRANDE",
        "nodo": "EST-TUMBAYA-CAB01",
        "localidad": "Tumbaya",
        "cursos": ["Río Tumbaya Grande"],
    },
    {
        "id": "CUENCA_PURMAMARCA",
        "nodo": "EST-PURMAMARCA-CAB01",
        "localidad": "Purmamarca",
        "cursos": ["Río Purmamarca", "Río Purmarmamarca"],
    },
    {"id": "CUENCA_HUASAMAYO", "nodo": "EST-TILCARA-CAB01", "localidad": "Tilcara", "cursos": ["Río Huasamayo"]},
]


def _transformadores():
    from pyproj import Transformer

    a_utm = Transformer.from_crs("EPSG:4326", UTM, always_xy=True).transform
    a_geo = Transformer.from_crs(UTM, "EPSG:4326", always_xy=True).transform
    return a_utm, a_geo


def codificar_elevacion_rgb(elevacion_m: float, nodata: float = -9999.0) -> tuple[int, int, int]:
    """Codifica una cota en metros usando el esquema Mapbox Terrain-RGB (paso 0,1 m)."""
    if math.isnan(elevacion_m) or elevacion_m == nodata:
        elevacion = 0.0
    else:
        elevacion = max(-10000.0, min(1667721.5, float(elevacion_m)))
    entero = round((elevacion + 10000.0) * 10.0)
    return (entero >> 16) & 255, (entero >> 8) & 255, entero & 255


def decodificar_elevacion_rgb(r: int, g: int, b: int) -> float:
    """Decodifica una terna Mapbox Terrain-RGB a elevación en metros."""
    return -10000.0 + (r * 65536 + g * 256 + b) * 0.1


def codificar_terrain_rgb(mde_m: Any, nodata: float = -9999.0):
    """Codifica una matriz 2D de elevaciones (m) en una imagen uint8 RGB Mapbox Terrain-RGB."""
    import numpy as np

    elev = np.asarray(mde_m, dtype="float64")
    invalido = np.isnan(elev) | (elev == nodata)
    limpio = np.where(invalido, 0.0, np.clip(elev, -10000.0, 1667721.5))
    enteros = np.rint((limpio + 10000.0) * 10.0).astype("int64")
    rgb = np.empty((*limpio.shape, 3), dtype="uint8")
    rgb[..., 0] = (enteros >> 16) & 255
    rgb[..., 1] = (enteros >> 8) & 255
    rgb[..., 2] = enteros & 255
    return rgb


def decodificar_terrain_rgb(rgb: Any):
    """Decodifica una matriz uint8 (H, W, 3) Mapbox Terrain-RGB a elevaciones float64 en metros."""
    import numpy as np

    arr = np.asarray(rgb, dtype="float64")
    return -10000.0 + (arr[..., 0] * 65536.0 + arr[..., 1] * 256.0 + arr[..., 2]) * 0.1


def _lonlat_a_tile(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    n = 1 << zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return max(0, min(n - 1, x)), max(0, min(n - 1, y))


def _limites_tile_3857(z: int, x: int, y: int) -> tuple[float, float, float, float]:
    origen = 20037508.342789244
    tam_mundo = 2.0 * origen
    tam_tile = tam_mundo / (1 << z)
    minx = -origen + x * tam_tile
    maxx = minx + tam_tile
    maxy = origen - y * tam_tile
    miny = maxy - tam_tile
    return minx, miny, maxx, maxy


def generar_terrain_rgb(
    mde: Any,
    t: Any,
    carpeta_teselas: Path,
    zooms: tuple[int, ...] = (10, 11, 12),
) -> dict[str, Any]:
    """Exporta teselas PNG Mapbox Terrain-RGB (256x256, EPSG:3857) para uso 3D offline en MapLibre."""
    import numpy as np
    import rasterio.transform
    from PIL import Image
    from rasterio.warp import Resampling, reproject

    for z in zooms:
        x0, y0 = _lonlat_a_tile(OESTE, NORTE, z)
        x1, y1 = _lonlat_a_tile(ESTE, SUR, z)
        for tx in range(x0, x1 + 1):
            for ty in range(y0, y1 + 1):
                minx, miny, maxx, maxy = _limites_tile_3857(z, tx, ty)
                dst_transform = rasterio.transform.from_bounds(minx, miny, maxx, maxy, 256, 256)
                destino = np.full((256, 256), -9999.0, dtype="float32")
                reproject(
                    mde,
                    destino,
                    src_transform=t,
                    src_crs=UTM,
                    dst_transform=dst_transform,
                    dst_crs="EPSG:3857",
                    src_nodata=-9999.0,
                    dst_nodata=-9999.0,
                    resampling=Resampling.bilinear,
                )
                rgb = codificar_terrain_rgb(destino, nodata=-9999.0)
                ruta = carpeta_teselas / str(z) / str(tx) / f"{ty}.png"
                ruta.parent.mkdir(parents=True, exist_ok=True)
                Image.fromarray(rgb, mode="RGB").save(ruta, optimize=True)

    return {
        "encoding": "mapbox",
        "tiles": "/datos/terrain/{z}/{x}/{y}.png",
        "minzoom": min(zooms),
        "maxzoom": max(zooms),
        "bounds": [OESTE, SUR, ESTE, NORTE],
    }


def descargar(url: str, destino: Path) -> Path:
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        pedido = urllib.request.Request(url, headers={"User-Agent": "quebrada-alert-demo"})
        destino.write_bytes(urllib.request.urlopen(pedido, timeout=180).read())
        time.sleep(1)
    return destino


def leer_osm() -> dict:
    """RN 9, cursos de agua con nombre y localidades, en UTM."""
    import numpy as np
    from shapely.geometry import LineString
    from shapely.ops import unary_union

    a_utm, _ = _transformadores()
    nodos, vias, localidades = {}, [], {}
    i = 0
    for lon in np.arange(OESTE, ESTE, 0.1):
        for lat in np.arange(SUR, NORTE, 0.1):
            caja = f"{lon:.2f},{lat:.2f},{lon + 0.1:.2f},{lat + 0.1:.2f}"
            ruta = descargar(f"https://api.openstreetmap.org/api/0.6/map?bbox={caja}", CRUDO / f"osm_{i}.xml")
            i += 1
            raiz = ET.parse(ruta).getroot()
            for n in raiz.iter("node"):
                nodos[n.get("id")] = (float(n.get("lon")), float(n.get("lat")))
                e = {x.get("k"): x.get("v") for x in n.findall("tag")}
                if e.get("place") in ("town", "village") and e.get("name"):
                    localidades[e["name"]] = nodos[n.get("id")]
            for w in raiz.iter("way"):
                e = {x.get("k"): x.get("v") for x in w.findall("tag")}
                if e.get("ref") == "RN9" or (e.get("waterway") and e.get("name")):
                    vias.append((w.get("id"), e, [x.get("ref") for x in w.findall("nd")]))
    rn9, cursos, vistas = [], {}, set()
    for ident, e, refs in vias:
        puntos = [a_utm(*nodos[r]) for r in refs if r in nodos]
        if ident in vistas or len(puntos) < 2:
            continue
        vistas.add(ident)
        if e.get("ref") == "RN9":
            rn9.append(LineString(puntos))
        else:
            cursos.setdefault(e["name"], []).append(LineString(puntos))
    return {
        "rn9": unary_union(rn9),
        "cursos": {k: unary_union(v) for k, v in cursos.items()},
        "localidades": localidades,
    }


def mde_utm() -> Path:
    import numpy as np
    import rasterio
    from rasterio.warp import Resampling, calculate_default_transform, reproject

    destino = CRUDO / "mde_utm.tif"
    if destino.exists():
        return destino
    origen = descargar(f"https://copernicus-dem-30m.s3.amazonaws.com/{TESELA}/{TESELA}.tif", CRUDO / "mde.tif")
    with rasterio.open(origen) as src:
        ventana = rasterio.windows.from_bounds(OESTE, SUR, ESTE, NORTE, src.transform)
        datos = src.read(1, window=ventana)
        t_origen = src.window_transform(ventana)
        t, ancho, alto = calculate_default_transform(
            src.crs, UTM, datos.shape[1], datos.shape[0], OESTE, SUR, ESTE, NORTE, resolution=30
        )
        salida = np.zeros((alto, ancho), dtype="float32")
        reproject(
            datos,
            salida,
            src_transform=t_origen,
            src_crs=src.crs,
            dst_transform=t,
            dst_crs=UTM,
            resampling=Resampling.bilinear,
        )
        perfil = {
            "driver": "GTiff",
            "height": alto,
            "width": ancho,
            "count": 1,
            "dtype": "float32",
            "crs": UTM,
            "transform": t,
            "nodata": -9999,
        }
        with rasterio.open(destino, "w", **perfil) as dst:
            dst.write(salida, 1)
    return destino


def relieve(mde: Any, t: Any, ruta: Path) -> list:
    """Relieve sombreado en PNG, como fondo del mapa sin teselas externas. Devuelve sus límites."""
    import numpy as np
    import rasterio.transform
    from PIL import Image
    from rasterio.warp import Resampling, reproject

    dy, dx = np.gradient(mde, 30)
    pendiente, orientacion = np.arctan(np.hypot(dx, dy)), np.arctan2(-dx, dy)
    azimut, altura = np.radians(315), np.radians(45)
    sombra = np.sin(altura) * np.cos(pendiente) + np.cos(altura) * np.sin(pendiente) * np.cos(azimut - orientacion)
    gris = (np.clip(sombra, 0, 1) * 140 + 30).astype("uint8")
    # Se lleva a coordenadas geográficas para que el mapa lo superponga sin giro.
    ancho, alto = 900, 1080
    destino = np.zeros((alto, ancho), dtype="uint8")
    t_geo = rasterio.transform.from_bounds(OESTE, SUR, ESTE, NORTE, ancho, alto)
    reproject(
        gris,
        destino,
        src_transform=t,
        src_crs=UTM,
        dst_transform=t_geo,
        dst_crs="EPSG:4326",
        resampling=Resampling.average,
    )
    Image.fromarray(destino).save(ruta, optimize=True)
    return [[SUR, OESTE], [NORTE, ESTE]]


def geo(geometria, decimales: int = 5) -> dict:
    from shapely.geometry import mapping
    from shapely.ops import transform

    _, a_geo = _transformadores()
    g = mapping(transform(a_geo, geometria))

    def redondear(c):
        return [redondear(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(v, decimales) for v in c]

    return {"type": g["type"], "coordinates": redondear(g["coordinates"])}


def main() -> None:
    import numpy as np
    from pysheds.grid import Grid
    from rasterio.features import shapes
    from shapely.geometry import LineString, Point, shape
    from shapely.ops import nearest_points, unary_union

    a_utm, _ = _transformadores()
    SALIDA.mkdir(exist_ok=True)
    osm = leer_osm()
    ruta_mde = mde_utm()
    grid = Grid.from_raster(str(ruta_mde))
    mde = grid.read_raster(str(ruta_mde))
    acond = grid.resolve_flats(grid.fill_depressions(grid.fill_pits(mde)))
    fdir = grid.flowdir(acond)
    acc = grid.accumulation(fdir)
    t = grid.affine
    km2_celda = 30 * 30 / 1e6
    limites = relieve(np.asarray(mde), t, SALIDA / "relieve.png")
    terrain = generar_terrain_rgb(np.asarray(mde), t, SALIDA / "terrain")
    paso = np.zeros(fdir.shape, dtype="float32")
    for codigo, (df, dc) in DIRECCIONES.items():
        paso[np.asarray(fdir) == codigo] = 30 * np.hypot(df, dc)

    rio_grande = osm["cursos"]["Río Grande"]
    cuencas, cauces, puntos = [], [], []
    for c in CUENCAS:
        curso = unary_union([osm["cursos"][n] for n in c["cursos"] if n in osm["cursos"]])
        en_curso, en_ruta = nearest_points(curso, osm["rn9"])
        # Salida de la cuenca: la celda de mayor acumulación sobre el curso trazado en OSM, hasta 2,5 km
        # aguas arriba del cruce con la ruta. Se evita el abanico aluvial, donde el MDE no encauza el
        # flujo, y el río Grande, que corre junto a la ruta.
        mejor, fila, col = -1.0, 0, 0
        tramo = curso.intersection(en_curso.buffer(2500)).difference(osm["cursos"]["Río Grande"].buffer(300))
        for d in np.arange(0, tramo.length, 30):
            p = tramo.interpolate(d)
            k0, f0 = (int(v) for v in ~t * (p.x, p.y))
            for f in range(f0 - 4, f0 + 5):
                for k in range(k0 - 4, k0 + 5):
                    px, py = t * (k + 0.5, f + 0.5)
                    if acc[f, k] * km2_celda > AREA_MAX_KM2 or rio_grande.distance(Point(px, py)) < 300:
                        continue
                    if acc[f, k] > mejor:
                        mejor, fila, col = float(acc[f, k]), f, k
        x, y = t * (col + 0.5, fila + 0.5)
        mascara = np.asarray(grid.catchment(x=x, y=y, fdir=fdir, xytype="coordinate", snap="center"))
        area = float(mascara.sum() * km2_celda)
        partes = [shape(g) for g, v in shapes(mascara.astype("uint8"), mask=mascara, transform=t) if v == 1]
        poligono = max(partes, key=lambda p: p.area).simplify(60)

        dist = np.asarray(
            grid.distance_to_outlet(
                x=x,
                y=y,
                fdir=fdir,
                weights=grid.view(rasterio_a_raster(paso, grid)),
                xytype="coordinate",
                snap="center",
            ),
            dtype=float,
        )
        dist[~mascara] = -1
        dist[fila, col] = 0
        f, k = np.unravel_index(dist.argmax(), dist.shape)
        traza, largos = [], []
        while True:
            traza.append((f, k))
            largos.append(dist[f, k])
            if (f, k) == (fila, col):
                break
            df, dc = DIRECCIONES[int(fdir[f, k])]
            f, k = f + df, k + dc
        cotas = np.array([float(mde[f, k]) for f, k in traza])
        largos = np.array(largos)
        linea = LineString([t * (k + 0.5, f + 0.5) for f, k in traza]).simplify(30)
        tramo_final = Point(x, y).distance(en_curso)  # de la salida de la cuenca al cruce con la ruta
        largos = largos + tramo_final
        largo = float(largos[0])
        pendiente = float((cotas[0] - cotas[-1]) / largo)
        # Estación de cabecera: sobre el cauce principal, a mitad de recorrido.
        i_est = int(np.argmin(np.abs(largos - largo / 2)))
        f, k = traza[i_est]
        estacion = Point(t * (k + 0.5, f + 0.5))
        largo_est = float(largos[i_est])
        pend_est = float((cotas[i_est] - cotas[-1]) / largo_est)
        prop = {
            "basin_id": c["id"],
            "node_id": c["nodo"],
            "localidad": c["localidad"],
            "curso": c["cursos"][0],
            "area_km2": round(area, 1),
            "largo_cauce_m": round(largo),
            "pendiente_cauce": round(pendiente, 4),
            "cota_max_cauce_m": round(float(cotas[0])),
            "cota_impacto_m": round(float(cotas[-1])),
            "cota_estacion_m": round(float(cotas[i_est])),
            "largo_estacion_impacto_m": round(largo_est),
            "pendiente_estacion_impacto": round(pend_est, 4),
            "distancia_cruce_rn9_m": round(en_curso.distance(en_ruta)),
        }
        print(prop)
        cuencas.append({"type": "Feature", "properties": prop, "geometry": geo(poligono)})
        cauces.append({"type": "Feature", "properties": {"basin_id": c["id"]}, "geometry": geo(linea)})
        puntos.append(
            {
                "type": "Feature",
                "properties": {"tipo": "estacion", "basin_id": c["id"], "node_id": c["nodo"]},
                "geometry": geo(estacion),
            }
        )
        puntos.append(
            {
                "type": "Feature",
                "properties": {"tipo": "impacto", "basin_id": c["id"], "nombre": f"RN 9 en {c['localidad']}"},
                "geometry": geo(en_curso),
            }
        )
    for nombre, (lon, lat) in osm["localidades"].items():
        puntos.append(
            {
                "type": "Feature",
                "properties": {"tipo": "localidad", "nombre": nombre},
                "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]},
            }
        )

    caja = shape(
        {
            "type": "Polygon",
            "coordinates": [
                [a_utm(OESTE, SUR), a_utm(ESTE, SUR), a_utm(ESTE, NORTE), a_utm(OESTE, NORTE), a_utm(OESTE, SUR)]
            ],
        }
    )
    contexto = [{"type": "Feature", "properties": {"tipo": "rn9"}, "geometry": geo(osm["rn9"].simplify(20))}]
    for nombre, g in osm["cursos"].items():
        if nombre == "Río Grande":
            g = g.intersection(caja).simplify(20)
            contexto.append({"type": "Feature", "properties": {"tipo": "rio", "nombre": nombre}, "geometry": geo(g)})

    def guardar(nombre: str, elementos: list, **extra) -> None:
        contenido = {"type": "FeatureCollection", **extra, "features": elementos}
        (SALIDA / nombre).write_text(json.dumps(contenido, ensure_ascii=False, separators=(",", ":")))

    guardar("cuencas.geojson", cuencas)
    guardar("cauces.geojson", cauces)
    guardar("puntos.geojson", puntos)
    guardar("contexto.geojson", contexto, relieve_limites=limites, terrain=terrain)


def rasterio_a_raster(matriz: Any, grid: Any):
    from pysheds.sview import Raster, ViewFinder

    return Raster(matriz, ViewFinder(affine=grid.affine, shape=grid.shape, crs=grid.crs, nodata=0))


if __name__ == "__main__":
    main()
