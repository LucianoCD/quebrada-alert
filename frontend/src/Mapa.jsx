import L from "leaflet";
import { useEffect, useRef } from "react";
import { NIVELES } from "./niveles.js";

const leer = (nombre) => fetch(`/datos/${nombre}`).then((r) => r.json());

// Mapa sin teselas externas: relieve sombreado y capas GeoJSON servidos por el backend local.
export default function Mapa({ cuencas, seleccion, alSeleccionar }) {
  const contenedor = useRef(null);
  const capa = useRef(null);
  const elegir = useRef(alSeleccionar);
  elegir.current = alSeleccionar;

  useEffect(() => {
    const mapa = L.map(contenedor.current, { zoomSnap: 0.25, attributionControl: false });
    L.control
      .attribution({ prefix: false })
      .addAttribution("Relieve: Copernicus DEM GLO-30 · Vías y cursos: © OpenStreetMap")
      .addTo(mapa);
    let vigente = true;
    Promise.all(["contexto.geojson", "cuencas.geojson", "cauces.geojson", "puntos.geojson"].map(leer)).then(
      ([contexto, poligonos, cauces, puntos]) => {
        if (!vigente) return;
        L.imageOverlay("/datos/relieve.png", contexto.relieve_limites, { opacity: 0.9 }).addTo(mapa);
        L.geoJSON(contexto, {
          style: (f) =>
            f.properties.tipo === "rn9"
              ? { color: "#f8fafc", weight: 2.5, dashArray: "6 4" }
              : { color: "#38bdf8", weight: 2, opacity: 0.8 },
        }).addTo(mapa);
        capa.current = L.geoJSON(poligonos, {
          onEachFeature: (f, l) => l.on("click", () => elegir.current(f.properties.basin_id)),
        }).addTo(mapa);
        L.geoJSON(cauces, { style: { color: "#7dd3fc", weight: 1.5 }, interactive: false }).addTo(mapa);
        L.geoJSON(puntos, {
          pointToLayer: (f, latlng) => {
            const p = f.properties;
            if (p.tipo === "localidad") {
              return L.circleMarker(latlng, { radius: 2, color: "#e2e8f0", fillOpacity: 1 }).bindTooltip(p.nombre, {
                permanent: true,
                direction: "right",
                className: "etiqueta-mapa",
              });
            }
            const estacion = p.tipo === "estacion";
            return L.circleMarker(latlng, {
              radius: estacion ? 6 : 5,
              color: "#0f172a",
              weight: 2,
              fillColor: estacion ? "#fde047" : "#f8fafc",
              fillOpacity: 1,
            }).bindTooltip(estacion ? `Estación ${p.node_id}` : `Punto de impacto: ${p.nombre}`);
          },
        }).addTo(mapa);
        mapa.fitBounds(capa.current.getBounds().pad(0.08));
      },
    );
    return () => {
      vigente = false;
      mapa.remove();
    };
  }, []);

  useEffect(() => {
    capa.current?.setStyle((f) => {
      const id = f.properties.basin_id;
      const nivel = cuencas.find((c) => c.basin_id === id)?.nivel ?? "GREEN";
      return {
        color: id === seleccion ? "#ffffff" : NIVELES[nivel].color,
        weight: id === seleccion ? 3 : 1.5,
        fillColor: NIVELES[nivel].color,
        fillOpacity: nivel === "GREEN" ? 0.25 : 0.55,
      };
    });
  });

  return <div ref={contenedor} className="h-full w-full" />;
}
