import { MapboxOverlay } from "@deck.gl/mapbox";
import { TripsLayer } from "@deck.gl/geo-layers";
import { ScatterplotLayer } from "@deck.gl/layers";
import { LngLatBounds, Map as MLMap, Marker, NavigationControl, setWorkerUrl } from "maplibre-gl";
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import { cuenta, estadoEnlace, NIVELES } from "./niveles.js";
import { useTema } from "./tema.js";

// MapLibre procesa fuentes en un web worker; sin URL explícita el bundle no lo encuentra.
setWorkerUrl(workerUrl);

const leer = (nombre) => fetch(`/datos/${nombre}`).then((r) => (r.ok ? r.json() : Promise.reject(r)));

// Pintura del mapa base por tema: [capa, propiedad, valor]. El relieve es gris y toma el tono del fondo.
const PINTURA = {
  noche: {
    seleccion: "#f5f0e8",
    capas: [
      ["fondo", "background-color", "#0b101b"],
      ["relieve", "raster-opacity", 0.5],
      ["relieve", "raster-brightness-max", 0.62],
      ["rio", "line-color", "#60a5fa"],
      ["rn9", "line-color", "#e0a84a"],
      ["cauce", "line-color", "#38d2ec"],
    ],
  },
  dia: {
    seleccion: "#1c1917",
    capas: [
      ["fondo", "background-color", "#f2ece2"],
      ["relieve", "raster-opacity", 0.6],
      ["relieve", "raster-brightness-max", 1.25],
      ["rio", "line-color", "#0369a1"],
      ["rn9", "line-color", "#7c5109"],
      ["cauce", "line-color", "#0284c7"],
    ],
  },
};

const CAPAS = [
  { id: "fondo", type: "background", paint: { "background-color": "#0b101b" } },
  {
    id: "relieve",
    type: "raster",
    source: "relieve",
    paint: { "raster-opacity": 0.5, "raster-saturation": -0.45, "raster-brightness-max": 0.62 },
  },
  {
    id: "rio",
    type: "line",
    source: "contexto",
    filter: ["==", ["get", "tipo"], "rio"],
    paint: { "line-color": "#60a5fa", "line-width": 2.5, "line-opacity": 0.75 },
  },
  {
    id: "rn9",
    type: "line",
    source: "contexto",
    filter: ["==", ["get", "tipo"], "rn9"],
    paint: {
      "line-color": "#e0a84a",
      "line-width": 2,
      "line-opacity": 0.9,
      "line-dasharray": [2, 1.4],
    },
  },
  {
    id: "cuenca-relleno",
    type: "fill",
    source: "cuencas",
    paint: {
      "fill-color": ["get", "color"],
      "fill-opacity": ["get", "fillOpacity"],
    },
  },
  {
    id: "cuenca-borde",
    type: "line",
    source: "cuencas",
    paint: {
      "line-color": ["get", "borde"],
      "line-width": ["case", ["==", ["get", "sel"], 1], 3, 1.4],
      "line-opacity": 0.95,
    },
  },
  {
    id: "cauce",
    type: "line",
    source: "cauces",
    paint: { "line-color": "#38d2ec", "line-width": 1.4, "line-opacity": 0.65 },
  },
];

const hexRgb = (hex) => {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255, 255];
};

const ANCHO_POR_NIVEL = { GREEN: 1.6, YELLOW: 2.6, ORANGE: 4, RED: 5.5 };
const DURACION_VIAJE_MS = 9000;

function estiloCompleto(contexto, cuencasGeo, cauces) {
  const [[s, w], [n, e]] = contexto.relieve_limites;
  const sources = {
    relieve: {
      type: "image",
      url: "/datos/relieve.png",
      coordinates: [
        [w, n],
        [e, n],
        [e, s],
        [w, s],
      ],
    },
    contexto: { type: "geojson", data: contexto },
    cuencas: { type: "geojson", data: cuencasGeo },
    cauces: { type: "geojson", data: cauces },
  };
  if (contexto.terrain?.tiles) {
    sources.terrain = {
      type: "raster-dem",
      tiles: [contexto.terrain.tiles],
      encoding: contexto.terrain.encoding || "mapbox",
      tileSize: 256,
      minzoom: contexto.terrain.minzoom ?? 10,
      maxzoom: contexto.terrain.maxzoom ?? 12,
    };
  }
  return {
    version: 8,
    sources,
    layers: CAPAS,
  };
}

export default function MapaTactico({ cuencas, seleccion, vista3D, alSeleccionar }) {
  const contenedor = useRef(null);
  const mapaRef = useRef(null);
  const overlayRef = useRef(null);
  const rafRef = useRef(0);
  const tieneTerrainRef = useRef(false);
  const datosRef = useRef({ cuencasGeo: null, cauceFeatures: [], puntos: [] });
  const marcadoresRef = useRef([]);
  const [errorGL, setErrorGL] = useState(false);
  const elegir = useRef(alSeleccionar);
  elegir.current = alSeleccionar;
  const seleccionRef = useRef(seleccion);
  seleccionRef.current = seleccion;
  const cuencasRef = useRef(cuencas);
  cuencasRef.current = cuencas;
  const vista3DRef = useRef(vista3D);
  vista3DRef.current = vista3D;
  const tema = useTema((s) => s.tema);
  const temaRef = useRef(tema);
  temaRef.current = tema;

  const pintarTema = () => {
    const mapa = mapaRef.current;
    if (!mapa?.isStyleLoaded()) return;
    for (const [capa, propiedad, valor] of PINTURA[temaRef.current].capas) mapa.setPaintProperty(capa, propiedad, valor);
  };

  const construirOverlay = () => {
    if (!mapaRef.current || overlayRef.current) return;
    overlayRef.current = new MapboxOverlay({ interleaved: false, layers: [] });
    mapaRef.current.addControl(overlayRef.current);
    const animar = () => {
      const t = performance.now() / 1000;
      overlayRef.current?.setProps({ layers: capasDeck(t) });
      rafRef.current = requestAnimationFrame(animar);
    };
    rafRef.current = requestAnimationFrame(animar);
  };

  const capasDeck = (t) => {
    const { cauceFeatures, puntos } = datosRef.current;
    const porCuenca = new Map(cuencasRef.current.map((c) => [c.basin_id, c]));
    const nivelDe = (id) => porCuenca.get(id)?.nivel ?? "GREEN";
    const trips = cauceFeatures.map((f) => {
      const path = f.geometry.coordinates;
      return {
        path,
        timestamps: path.map((_, i) => (i / Math.max(1, path.length - 1)) * DURACION_VIAJE_MS),
        color: hexRgb(NIVELES[nivelDe(f.properties.basin_id)].color),
        width: ANCHO_POR_NIVEL[nivelDe(f.properties.basin_id)],
      };
    });
    const estaciones = puntos
      .filter((f) => f.properties.tipo === "estacion")
      .map((f) => {
        const c = porCuenca.get(f.properties.basin_id);
        const enlace = estadoEnlace(c?.nodo, c?.origen);
        return {
          position: f.geometry.coordinates,
          color: NIVELES[c?.nivel ?? "GREEN"].color,
          halo: enlace === "online" ? "#06B6D4" : enlace === "lora" ? "#FBBF24" : "#64748B",
          pulso: enlace === "lora",
        };
      });
    const impactos = puntos
      .filter((f) => {
        const c = porCuenca.get(f.properties.basin_id);
        return f.properties.tipo === "impacto" && c && c.nivel !== "GREEN";
      })
      .map((f) => {
        const c = porCuenca.get(f.properties.basin_id);
        return {
          position: f.geometry.coordinates,
          color: NIVELES[c.nivel].color,
          critico: c.nivel === "ORANGE" || c.nivel === "RED",
        };
      });
    return [
      new TripsLayer({
        id: "flujo-cauces",
        data: trips,
        getPath: (d) => d.path,
        getTimestamp: (d) => d.timestamps,
        getColor: (d) => d.color,
        getWidth: (d) => d.width,
        widthMinPixels: 1.5,
        rounded: true,
        trailLength: 0.35,
        currentTime: (t % (DURACION_VIAJE_MS / 1000)) * 1000,
        fadeTrail: true,
      }),
      new ScatterplotLayer({
        id: "impactos-rn9",
        data: impactos,
        getPosition: (d) => d.position,
        getFillColor: (d) => [...hexRgb(d.color).slice(0, 3), 80],
        getRadius: (d) => (d.critico ? 2800 + Math.sin(t * 4) * 1000 : 1600),
        radiusUnits: "meters",
        stroked: true,
        getLineColor: (d) => hexRgb(d.color),
        getLineWidth: 70,
        lineWidthUnits: "meters",
        updateTriggers: { getRadius: t },
      }),
      new ScatterplotLayer({
        id: "nodos-halo",
        data: estaciones,
        getPosition: (d) => d.position,
        getFillColor: (d) => [...hexRgb(d.halo), d.pulso ? 110 + Math.sin(t * 6) * 60 : 85],
        getRadius: () => 26,
        radiusUnits: "pixels",
        stroked: false,
        updateTriggers: { getFillColor: t },
      }),
      new ScatterplotLayer({
        id: "nodos-core",
        data: estaciones,
        getPosition: (d) => d.position,
        getFillColor: (d) => [...hexRgb(d.color).slice(0, 3), 235],
        getRadius: (d) => (d.pulso ? 7 + Math.sin(t * 6) * 1.5 : 6),
        radiusUnits: "pixels",
        stroked: true,
        getLineColor: [8, 12, 20, 255],
        getLineWidth: 1.5,
        updateTriggers: { getRadius: t },
      }),
    ];
  };

  const actualizarCapas = () => {
    const fuente = mapaRef.current?.getSource("cuencas");
    const geo = datosRef.current.cuencasGeo;
    if (!fuente || !geo) return;
    fuente.setData({
      type: "FeatureCollection",
      features: geo.features.map((f) => {
        const c = cuencasRef.current.find((x) => x.basin_id === f.properties.basin_id);
        const nivel = c?.nivel ?? "GREEN";
        return {
          ...f,
          properties: {
            ...f.properties,
            // El relleno conserva el color del nivel; la selección solo cambia el borde.
            color: NIVELES[nivel].color,
            borde: c && seleccionRef.current === f.properties.basin_id ? PINTURA[temaRef.current].seleccion : NIVELES[nivel].color,
            fillOpacity: c ? NIVELES[nivel].fillOpacity : 0.12,
            sel: seleccionRef.current === f.properties.basin_id ? 1 : 0,
          },
        };
      }),
    });
  };

  // Pestañas HTML sobre cruces RN 9 con alerta NARANJA/ROJO (spec §5.2.3)
  const actualizarMarcadoresImpacto = () => {
    const mapa = mapaRef.current;
    if (!mapa) return;
    marcadoresRef.current.forEach((m) => m.remove());
    marcadoresRef.current = [];
    const { puntos } = datosRef.current;
    cuencasRef.current.forEach((c) => {
      if (c.nivel !== "ORANGE" && c.nivel !== "RED") return;
      const f = puntos.find((p) => p.properties.tipo === "impacto" && p.properties.basin_id === c.basin_id);
      if (!f) return;
      const nivel = NIVELES[c.nivel];
      const el = document.createElement("button");
      el.type = "button";
      el.className =
        "pointer-events-auto cursor-pointer rounded-md border px-2 py-1 text-[11px] font-bold shadow-lg backdrop-blur-sm";
      el.style.cssText = `background:var(--elevada);border-color:${nivel.color};color:${nivel.tinta}`;
      const eta = cuenta(c.minutos_restantes);
      el.textContent = `⚠ ${f.properties.nombre} · ETA ${eta ?? "—"}`;
      el.setAttribute("aria-label", `Seleccionar ${f.properties.nombre}, nivel ${nivel.nombre}, ETA ${eta ?? "sin definir"}`);
      el.onclick = () => elegir.current(c.basin_id);
      const marcador = new Marker({ element: el, anchor: "bottom" })
        .setLngLat(f.geometry.coordinates)
        .addTo(mapa);
      marcadoresRef.current.push(marcador);
    });
  };

  // Inicialización: geodatos primero (el estilo necesita las fuentes reales), luego el mapa.
  useEffect(() => {
    let mapa = null;
    let cancelado = false;
    (async () => {
      try {
        const [contexto, cuencasGeo, cauces, puntos] = await Promise.all(
          ["contexto.geojson", "cuencas.geojson", "cauces.geojson", "puntos.geojson"].map(leer),
        );
        if (cancelado || !contenedor.current) return;
        tieneTerrainRef.current = Boolean(contexto.terrain?.tiles);
        const [[s, w], [n, e]] = contexto.relieve_limites;
        mapa = new MLMap({
          container: contenedor.current,
          style: estiloCompleto(contexto, cuencasGeo, cauces),
          center: [(w + e) / 2, (s + n) / 2],
          zoom: 10.3,
          pitch: vista3DRef.current ? 58 : 0,
          attributionControl: { compact: true },
        });
        mapaRef.current = mapa;
        mapa.addControl(new NavigationControl({ showCompass: false }), "bottom-right");

        mapa.on("load", () => {
          datosRef.current = {
            cuencasGeo: cuencasGeo,
            cauceFeatures: cauces.features,
            puntos: puntos.features,
          };
          mapa.fitBounds(new LngLatBounds([w, s], [e, n]), { padding: 60 });
          if (vista3DRef.current && tieneTerrainRef.current) {
            mapa.setTerrain({ source: "terrain", exaggeration: 1.5 });
          }
          puntos.features
            .filter((f) => f.properties.tipo === "localidad")
            .forEach((f) => {
              const el = document.createElement("div");
              el.className =
                "pointer-events-none whitespace-nowrap text-[10px] font-semibold text-tinta";
              el.style.textShadow = "0 0 4px var(--lienzo), 0 0 4px var(--lienzo)";
              el.textContent = f.properties.nombre;
              new Marker({ element: el, anchor: "left" }).setLngLat(f.geometry.coordinates).addTo(mapa);
            });
          construirOverlay();
          pintarTema();
          actualizarCapas();
          actualizarMarcadoresImpacto();
        });

        mapa.on("click", "cuenca-relleno", (ev) => {
          const id = ev.features?.[0]?.properties?.basin_id;
          if (id) elegir.current(id);
        });
        mapa.on("mouseenter", "cuenca-relleno", () => (mapa.getCanvas().style.cursor = "pointer"));
        mapa.on("mouseleave", "cuenca-relleno", () => (mapa.getCanvas().style.cursor = ""));
        mapa.on("error", (ev) => {
          if (/webgl/i.test(String(ev.error?.message ?? ev.error ?? ""))) setErrorGL(true);
        });
      } catch {
        if (!cancelado) setErrorGL(true);
      }
    })();

    return () => {
      cancelado = true;
      cancelAnimationFrame(rafRef.current);
      marcadoresRef.current.forEach((m) => m.remove());
      marcadoresRef.current = [];
      if (overlayRef.current) {
        try {
          mapa?.removeControl(overlayRef.current);
        } catch {
          /* el mapa pudo haberse destruido antes */
        }
        overlayRef.current = null;
      }
      mapa?.remove();
      mapaRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Recolorea polígonos y actualiza pines de impacto cuando cambia el estado
  useEffect(() => {
    actualizarCapas();
    actualizarMarcadoresImpacto();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cuencas, seleccion]);

  useEffect(() => {
    pintarTema();
    actualizarCapas();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tema]);

  // Vista 2D/3D: pitch y Terrain-RGB si hay teselas locales configuradas
  useEffect(() => {
    const mapa = mapaRef.current;
    if (!mapa) return;
    if (tieneTerrainRef.current) {
      mapa.setTerrain(vista3D ? { source: "terrain", exaggeration: 1.5 } : null);
    }
    mapa.easeTo({ pitch: vista3D ? 58 : 0, duration: 700 });
  }, [vista3D]);

  if (errorGL) {
    return (
      <div className="flex h-full w-full items-center justify-center bg-hundida p-6 text-center">
        <div className="max-w-sm">
          <div className="text-lg font-bold text-tinta">Mapa no disponible</div>
          <p className="mt-2 text-sm text-tinta-2">
            Este navegador no pudo inicializar WebGL, necesario para el mapa táctico. Los datos de las cuencas
            siguen disponibles en el panel lateral.
          </p>
        </div>
      </div>
    );
  }
  return <div ref={contenedor} className="h-full w-full" />;
}
