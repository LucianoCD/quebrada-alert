"""Genera los datos geográficos de la demo a partir de fuentes abiertas (requiere red; se corre una vez).

- Copernicus DEM GLO-30 (AWS Open Data): microcuencas, cauce principal, longitud y pendiente.
- OpenStreetMap: traza de la RN 9, cursos de agua con nombre y localidades.

Deja en data/ los GeoJSON y el relieve sombreado que usan el backend y el tablero sin conexión.
Requiere: pip install -e ".[geo]"
"""

import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import rasterio
import rasterio.transform
from PIL import Image
from pyproj import Transformer
from pysheds.grid import Grid
from rasterio.features import shapes
from rasterio.warp import Resampling, calculate_default_transform, reproject
from shapely.geometry import LineString, Point, mapping, shape
from shapely.ops import nearest_points, transform, unary_union

RAIZ = Path(__file__).resolve().parent.parent
CRUDO = RAIZ / "data_raw"
SALIDA = RAIZ / "data"
OESTE, SUR, ESTE, NORTE = -65.75, -24.05, -65.25, -23.45
UTM = "EPSG:32719"
TESELA = "Copernicus_DSM_COG_10_S24_00_W066_00_DEM"
# Área máxima admitida al ajustar la salida: evita engancharse al río Grande, que pasa al lado.
AREA_MAX_KM2 = 1500

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

a_utm = Transformer.from_crs("EPSG:4326", UTM, always_xy=True).transform
a_geo = Transformer.from_crs(UTM, "EPSG:4326", always_xy=True).transform


def descargar(url: str, destino: Path) -> Path:
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        pedido = urllib.request.Request(url, headers={"User-Agent": "quebrada-alert-demo"})
        destino.write_bytes(urllib.request.urlopen(pedido, timeout=180).read())
        time.sleep(1)
    return destino


def leer_osm() -> dict:
    """RN 9, cursos de agua con nombre y localidades, en UTM."""
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
        reproject(datos, salida, src_transform=t_origen, src_crs=src.crs, dst_transform=t, dst_crs=UTM,
                  resampling=Resampling.bilinear)  # fmt: skip
        perfil = {"driver": "GTiff", "height": alto, "width": ancho, "count": 1, "dtype": "float32",
                  "crs": UTM, "transform": t, "nodata": -9999}  # fmt: skip
        with rasterio.open(destino, "w", **perfil) as dst:
            dst.write(salida, 1)
    return destino


# Orden de pysheds: N, NE, E, SE, S, SO, O, NO.
DIRECCIONES = {64: (-1, 0), 128: (-1, 1), 1: (0, 1), 2: (1, 1), 4: (1, 0), 8: (1, -1), 16: (0, -1), 32: (-1, -1)}


def relieve(mde: np.ndarray, t, ruta: Path) -> list:
    """Relieve sombreado en PNG, como fondo del mapa sin teselas externas. Devuelve sus límites."""
    dy, dx = np.gradient(mde, 30)
    pendiente, orientacion = np.arctan(np.hypot(dx, dy)), np.arctan2(-dx, dy)
    azimut, altura = np.radians(315), np.radians(45)
    sombra = np.sin(altura) * np.cos(pendiente) + np.cos(altura) * np.sin(pendiente) * np.cos(azimut - orientacion)
    gris = (np.clip(sombra, 0, 1) * 140 + 30).astype("uint8")
    # Se lleva a coordenadas geográficas para que el mapa lo superponga sin giro.
    ancho, alto = 900, 1080
    destino = np.zeros((alto, ancho), dtype="uint8")
    t_geo = rasterio.transform.from_bounds(OESTE, SUR, ESTE, NORTE, ancho, alto)
    reproject(gris, destino, src_transform=t, src_crs=UTM, dst_transform=t_geo, dst_crs="EPSG:4326",
              resampling=Resampling.average)  # fmt: skip
    Image.fromarray(destino).save(ruta, optimize=True)
    return [[SUR, OESTE], [NORTE, ESTE]]


def geo(geometria, decimales: int = 5) -> dict:
    g = mapping(transform(a_geo, geometria))

    def redondear(c):
        return [redondear(x) for x in c] if isinstance(c[0], (list, tuple)) else [round(v, decimales) for v in c]

    return {"type": g["type"], "coordinates": redondear(g["coordinates"])}


def main() -> None:
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

        dist = np.asarray(grid.distance_to_outlet(x=x, y=y, fdir=fdir, weights=grid.view(
            rasterio_a_raster(paso, grid)), xytype="coordinate", snap="center"), dtype=float)  # fmt: skip
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
        puntos.append({"type": "Feature", "properties": {"tipo": "estacion", "basin_id": c["id"],
                       "node_id": c["nodo"]}, "geometry": geo(estacion)})  # fmt: skip
        puntos.append({"type": "Feature", "properties": {"tipo": "impacto", "basin_id": c["id"],
                       "nombre": f"RN 9 en {c['localidad']}"}, "geometry": geo(en_curso)})  # fmt: skip
    for nombre, (lon, lat) in osm["localidades"].items():
        puntos.append({"type": "Feature", "properties": {"tipo": "localidad", "nombre": nombre},
                       "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]}})  # fmt: skip

    caja = shape({"type": "Polygon", "coordinates": [[a_utm(OESTE, SUR), a_utm(ESTE, SUR), a_utm(ESTE, NORTE),
                                                      a_utm(OESTE, NORTE), a_utm(OESTE, SUR)]]})  # fmt: skip
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
    guardar("contexto.geojson", contexto, relieve_limites=limites)


def rasterio_a_raster(matriz: np.ndarray, grid: Grid):
    from pysheds.sview import Raster, ViewFinder

    return Raster(matriz, ViewFinder(affine=grid.affine, shape=grid.shape, crs=grid.crs, nodata=0))


if __name__ == "__main__":
    main()
