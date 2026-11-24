import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import corredor from "./assets/corredor.js";
import relieve from "./assets/corredor-relieve.webp";
import { cuenta, estadoEnlace, NIVELES } from "./niveles.js";

const { ancho: ANCHO, alto: ALTO } = corredor;
const NEUTRO = "#22d3ee";
const COLOR_ENLACE = { online: "#22d3ee", lora: "#fbbf24", offline: "#94a3b8" };
// Dónde se apoya la etiqueta de cada cuenca (en píxeles del relieve), hacia qué lado crece y,
// si no crece desde el cruce, dónde termina su línea guía.
const ETIQUETAS = {
  CUENCA_ARROYO_MEDIO: { x: 668, y: 1236, lado: "derecha" },
  CUENCA_TUMBAYA_GRANDE: { x: 660, y: 927, lado: "derecha" },
  CUENCA_PURMAMARCA: { x: 664, y: 716, lado: "derecha" },
  CUENCA_HUASAMAYO: { x: 1164, y: 150, lado: "izquierda", guia: [850, 185] },
};
const LEYENDA = [
  ["RN 9", <span key="i" className="h-[3px] w-4 rounded bg-amber-400" />],
  ["cauce", <span key="i" className="h-[3px] w-4 rounded bg-cyan-400" />],
  ["cuenca", <span key="i" className="h-2.5 w-3.5 rounded-sm border border-slate-300 bg-slate-300/20" />],
  ["estación de cabecera", <span key="i" className="h-2 w-2 rounded-full bg-cyan-300 ring-2 ring-cyan-300/30" />],
  ["cruce con RN 9", <span key="i" className="h-2 w-2 rotate-45 rounded-[1px] bg-slate-200" />],
];

const num = (v, decimales = 1) => v.toLocaleString("es-AR", { maximumFractionDigits: decimales });

/** Punto y recorrido de la onda de crecida a una fracción (0–1) del tramo estación → RN 9. */
export function avanceEnTramo(tramo, fraccion) {
  const largos = tramo.slice(1).map(([x, y], i) => Math.hypot(x - tramo[i][0], y - tramo[i][1]));
  let resto = Math.min(1, Math.max(0, fraccion)) * largos.reduce((a, b) => a + b, 0);
  const recorrido = [tramo[0]];
  for (let i = 0; i < largos.length; i += 1) {
    if (resto <= largos[i]) {
      const k = largos[i] ? resto / largos[i] : 0;
      recorrido.push([tramo[i][0] + (tramo[i + 1][0] - tramo[i][0]) * k, tramo[i][1] + (tramo[i + 1][1] - tramo[i][1]) * k]);
      break;
    }
    resto -= largos[i];
    recorrido.push(tramo[i + 1]);
  }
  const trazo = `M${recorrido.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join("L")}`;
  return { punto: recorrido[recorrido.length - 1], trazo };
}

/**
 * Ilustración de la landing: el corredor de la RN 9 con las cuatro cuencas sobre relieve sombreado.
 * Las geometrías vienen ya proyectadas (assets/corredor.js); el estado en vivo solo las colorea y anima.
 */
export default function MapaCorredor({ cuencas = [] }) {
  const [activa, setActiva] = useState(null);
  const porId = useMemo(() => new Map(cuencas.map((c) => [c.basin_id, c])), [cuencas]);

  const capas = corredor.cuencas.map((g) => {
    const vivo = porId.get(g.basin_id);
    const nivel = vivo ? NIVELES[vivo.nivel] : null;
    const eta = Math.round(vivo?.eta_min ?? g.eta_min);
    const restantes = vivo?.minutos_restantes;
    const onda = restantes != null && eta > 0 ? avanceEnTramo(g.tramo, 1 - restantes / eta) : null;
    return { g, vivo, nivel, eta, restantes, onda, color: nivel?.color ?? NEUTRO, orden: nivel?.orden ?? 0 };
  });

  return (
    <figure className="m-0">
      <div
        className="overflow-hidden rounded-2xl bg-[#070d18] shadow-[0_24px_70px_-20px_rgba(8,47,73,0.55)] ring-1 ring-slate-900/10"
        onMouseLeave={() => setActiva(null)}
      >
        <div className="relative w-full overflow-hidden" style={{ aspectRatio: `${ANCHO} / ${ALTO}` }}>
        <svg
          viewBox={`0 0 ${ANCHO} ${ALTO}`}
          className="absolute inset-0 h-full w-full"
          role="img"
          aria-label="Mapa del corredor de la Ruta Nacional 9 con las cuencas de Volcán, Tumbaya, Purmamarca y Tilcara"
        >
          <defs>
            <radialGradient id="corredor-vineta" cx="52%" cy="55%" r="75%">
              <stop offset="55%" stopColor="#060d1a" stopOpacity="0" />
              <stop offset="100%" stopColor="#060d1a" stopOpacity="0.7" />
            </radialGradient>
            <linearGradient id="corredor-velo" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#060d1a" stopOpacity="0.75" />
              <stop offset="0.16" stopColor="#060d1a" stopOpacity="0" />
              <stop offset="0.86" stopColor="#060d1a" stopOpacity="0" />
              <stop offset="1" stopColor="#060d1a" stopOpacity="0.8" />
            </linearGradient>
            <radialGradient id="corredor-celda">
              <stop offset="0" stopColor="currentColor" stopOpacity="0.55" />
              <stop offset="1" stopColor="currentColor" stopOpacity="0" />
            </radialGradient>
          </defs>

          <image href={relieve} width={ANCHO} height={ALTO} preserveAspectRatio="xMidYMid slice" />
          <rect width={ANCHO} height={ALTO} fill="url(#corredor-vineta)" />
          <rect width={ANCHO} height={ALTO} fill="url(#corredor-velo)" />

          {/* Cuencas: relleno según el semáforo; la activa se destaca y el resto se atenúa */}
          {capas.map(({ g, color, nivel }) => {
            const destacada = activa === g.basin_id;
            return (
              <path
                key={g.basin_id}
                d={g.contorno}
                fill={color}
                fillOpacity={(nivel ? nivel.fillOpacity : 0.08) + (destacada ? 0.12 : 0)}
                stroke={color}
                strokeOpacity={activa && !destacada ? 0.3 : destacada ? 1 : 0.65}
                strokeWidth={destacada ? 2 : 1.2}
                strokeLinejoin="round"
                vectorEffect="non-scaling-stroke"
                className={`cursor-pointer transition-[fill-opacity,stroke-opacity] duration-300 ${nivel?.orden >= 2 ? "corredor-latido" : ""}`}
                onMouseEnter={() => setActiva(g.basin_id)}
              />
            );
          })}

          {/* Río Grande y RN 9 */}
          <g fill="none" strokeLinecap="round" strokeLinejoin="round" pointerEvents="none">
            <path d={corredor.rio} stroke="#60a5fa" strokeOpacity="0.45" strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
            <path d={corredor.rn9} stroke="#070d18" strokeOpacity="0.9" strokeWidth="6" vectorEffect="non-scaling-stroke" />
            <path d={corredor.rn9} stroke="#fbbf24" strokeWidth="2.6" vectorEffect="non-scaling-stroke" />
          </g>

          {/* Cauces con flujo animado hacia la ruta; la onda de crecida avanza con la cuenta regresiva */}
          {capas.map(({ g, color, orden, onda }) => (
            <g key={g.basin_id} fill="none" strokeLinecap="round" strokeLinejoin="round" pointerEvents="none">
              {orden >= 2 && (
                <circle cx={g.tramo[0][0]} cy={g.tramo[0][1]} r="150" fill="url(#corredor-celda)" color={color} className="corredor-latido" />
              )}
              <path d={g.cauce} stroke="#22d3ee" strokeOpacity="0.14" strokeWidth="9" vectorEffect="non-scaling-stroke" />
              <path d={g.cauce} stroke="#22d3ee" strokeOpacity="0.3" strokeWidth="5" vectorEffect="non-scaling-stroke" />
              <path d={g.cauce} stroke="#67e8f9" strokeWidth="1.8" vectorEffect="non-scaling-stroke" />
              {onda && (
                <>
                  <path d={onda.trazo} stroke={color} strokeOpacity="0.35" strokeWidth="9" vectorEffect="non-scaling-stroke" />
                  <path d={onda.trazo} stroke={color} strokeWidth="3" vectorEffect="non-scaling-stroke" />
                </>
              )}
              <path
                d={g.cauce}
                stroke="#ecfeff"
                strokeWidth="1.8"
                vectorEffect="non-scaling-stroke"
                className="corredor-flujo"
                style={{ animationDuration: `${[2.6, 1.8, 1.1, 0.7][orden]}s` }}
              />
              {onda && (
                <g style={{ transform: `translate(${onda.punto[0]}px, ${onda.punto[1]}px)`, transition: "transform 1s linear" }}>
                  <circle r="26" fill={color} fillOpacity="0.25" className="corredor-pulso" />
                  <circle r="11" fill={color} stroke="#fff" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
                </g>
              )}
            </g>
          ))}

          {/* Localidades de referencia */}
          {corredor.localidades.map(({ nombre, xy: [x, y] }) => (
            <g key={nombre} pointerEvents="none">
              <circle cx={x} cy={y} r="6" fill="#e2e8f0" fillOpacity="0.9" />
              <text x={x + 16} y={y + 8} fontSize="24" fill="#e2e8f0" fillOpacity="0.85" stroke="#070d18" strokeWidth="5" paintOrder="stroke">
                {nombre}
              </text>
            </g>
          ))}

          {/* Estaciones de cabecera, cruces con la RN 9 y línea guía hacia cada etiqueta */}
          {capas.map(({ g, vivo, color, orden }) => {
            const [ex, ey] = g.estacion;
            const [cx, cy] = g.cruce;
            const et = ETIQUETAS[g.basin_id];
            const enlace = COLOR_ENLACE[vivo ? estadoEnlace(vivo.nodo, vivo.origen) : "online"];
            return (
              <g key={g.basin_id} pointerEvents="none">
                <line x1={cx} y1={cy} x2={et.guia?.[0] ?? et.x} y2={et.guia?.[1] ?? et.y} stroke="#e2e8f0" strokeOpacity="0.55" strokeWidth="1" vectorEffect="non-scaling-stroke" />
                <circle cx={ex} cy={ey} r="20" fill="none" stroke={enlace} strokeWidth="1.2" vectorEffect="non-scaling-stroke" className="corredor-pulso" />
                <circle cx={ex} cy={ey} r="9" fill={enlace} stroke="#070d18" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
                {orden >= 2 && <circle cx={cx} cy={cy} r="24" fill={color} fillOpacity="0.3" className="corredor-pulso" />}
                <rect
                  x={cx - 11}
                  y={cy - 11}
                  width="22"
                  height="22"
                  rx="3"
                  transform={`rotate(45 ${cx} ${cy})`}
                  fill={vivo ? color : "#e2e8f0"}
                  stroke="#070d18"
                  strokeWidth="1.5"
                  vectorEffect="non-scaling-stroke"
                />
              </g>
            );
          })}
        </svg>

        {/* Título */}
        <div className="pointer-events-none absolute left-3 top-3 sm:left-4 sm:top-4">
          <div className="text-[9px] font-semibold uppercase tracking-[0.28em] text-cyan-300 sm:text-[10px]">
            Corredor monitoreado
          </div>
          <div className="text-sm font-bold text-white sm:text-base">Ruta Nacional 9 · Jujuy</div>
        </div>

        {/* Etiquetas de cuenca: enlazan al monitor y amplían el detalle al pasar o enfocar */}
        {capas.map(({ g, nivel, eta, restantes, color }) => {
          const et = ETIQUETAS[g.basin_id];
          const destacada = activa === g.basin_id;
          return (
            <Link
              key={g.basin_id}
              to={`/monitor?cuenca=${g.basin_id}`}
              onMouseEnter={() => setActiva(g.basin_id)}
              onFocus={() => setActiva(g.basin_id)}
              onBlur={() => setActiva(null)}
              className={`absolute -translate-y-1/2 rounded-lg border bg-slate-950/75 px-2 py-1 text-left shadow-lg backdrop-blur-sm transition duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 sm:px-2.5 sm:py-1.5 ${
                destacada ? "z-10 border-white/40 bg-slate-950/90" : "border-white/10"
              } ${activa && !destacada ? "opacity-60" : ""}`}
              style={{
                [et.lado === "derecha" ? "left" : "right"]: `${((et.lado === "derecha" ? et.x : ANCHO - et.x) / ANCHO) * 100}%`,
                top: `${(et.y / ALTO) * 100}%`,
              }}
            >
              <div className="flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full" style={{ background: color }} />
                <span className="text-[11px] font-bold leading-tight text-white sm:text-[13px]">{g.localidad}</span>
                {nivel?.orden > 0 && (
                  <span className="rounded px-1 text-[9px] font-bold text-slate-950" style={{ background: color }}>
                    {nivel.nombre}
                  </span>
                )}
              </div>
              <div className="tabular whitespace-nowrap text-[9px] leading-snug text-slate-300 sm:text-[10.5px]">
                <span className="hidden sm:inline">{g.curso} · </span>
                {restantes != null ? (
                  <b style={{ color }}>arribo en {cuenta(restantes)}</b>
                ) : (
                  <span className="text-amber-300">ETA ~{eta} min</span>
                )}
              </div>
              {destacada && (
                <div className="tabular mt-1 hidden w-0 min-w-full border-t border-white/10 pt-1 text-[10px] leading-snug text-slate-400 sm:block">
                  {num(g.area_km2)} km² · cauce {num(g.largo_km)} km
                  <div>pendiente {num(g.pendiente_pct)} %</div>
                  <div className="text-cyan-300">Ver en el monitor →</div>
                </div>
              )}
            </Link>
          );
        })}

        {/* Norte y escala */}
        <div className="tabular pointer-events-none absolute right-3 top-3 text-[10px] font-bold text-slate-200 sm:right-4 sm:top-4">
          N ↑
        </div>
        <div
          className="tabular pointer-events-none absolute bottom-3 left-3 text-[9px] text-slate-300 sm:bottom-4 sm:left-4 sm:text-[10px]"
          style={{ width: `${(10 / corredor.km_px / ANCHO) * 100}%` }}
        >
          <div className="mb-0.5 flex justify-between">
            <span>0</span>
            <span>10 km</span>
          </div>
          <div className="h-1 rounded-sm border border-t-0 border-slate-300/80" />
        </div>
        </div>

        <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-1 border-t border-white/5 px-3 py-2 text-[10px] text-slate-300">
          {LEYENDA.map(([nombre, icono]) => (
            <span key={nombre} className="flex items-center gap-1.5">
              {icono}
              {nombre}
            </span>
          ))}
        </div>
      </div>
      <figcaption className="mt-2 text-[10px] leading-snug text-slate-500">
        Relieve: Copernicus DEM GLO-30 · RN 9 y cursos de agua: © OpenStreetMap · contornos de cuenca sin validación
        oficial · tiempos de arribo orientativos (Kirpich).
      </figcaption>
    </figure>
  );
}
