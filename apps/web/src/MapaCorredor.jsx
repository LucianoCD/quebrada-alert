import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import corredor from "./assets/corredor.js";
import relieve from "./assets/corredor-relieve.webp";
import { cuenta, emergenciaReciente, estadoEnlace, NIVELES } from "./niveles.js";

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

const GENERAL = { k: 1, tx: 0, ty: 0 };
const ZOOM_MAX = 4;
const entre = (v, a, b) => Math.min(b, Math.max(a, v));
const rampa = (t, a, b) => entre((t - a) / (b - a), 0, 1);
const suave = (x) => x * x * (3 - 2 * x);

/** Una vista es `translate(tx, ty) scale(k)` sobre los píxeles del relieve; nunca deja ver fuera del mapa. */
export function acotarVista({ k, tx, ty }) {
  const zoom = entre(k, 1, ZOOM_MAX);
  return { k: zoom, tx: entre(tx, ANCHO * (1 - zoom), 0), ty: entre(ty, ALTO * (1 - zoom), 0) };
}

/** Amplía o reduce la vista manteniendo fijo el centro del cuadro. */
export function ampliar(vista, factor) {
  const k = entre(vista.k * factor, 1, ZOOM_MAX);
  const cx = (ANCHO / 2 - vista.tx) / vista.k;
  const cy = (ALTO / 2 - vista.ty) / vista.k;
  return acotarVista({ k, tx: ANCHO / 2 - cx * k, ty: ALTO / 2 - cy * k });
}

/** Caja [x0, y0, x1, y1] de una lista plana de coordenadas x, y, x, y… */
function caja(n) {
  const xs = n.filter((_, i) => i % 2 === 0);
  const ys = n.filter((_, i) => i % 2 === 1);
  return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
}

/**
 * Mayor acercamiento en el que entran la cuenca, su cruce con la RN 9 y su etiqueta. Si la cuenca
 * es demasiado ancha para ampliarla entera, encuadra el tramo que recorre la crecida.
 */
export function encuadre(g) {
  const et = ETIQUETAS[g.basin_id];
  for (const [x0, y0, x1, y1] of [CAJAS[g.basin_id], caja(g.tramo.flat())]) {
    for (let k = 3; k >= 1.2; k -= 0.05) {
      // La etiqueta mide lo mismo en pantalla con cualquier zoom: ocupa menos mapa cuanto más se amplía.
      const [ancho, medio] = [640 / k, 80 / k];
      const izq = Math.min(x0, g.cruce[0], et.lado === "derecha" ? et.x : et.x - ancho);
      const der = Math.max(x1, g.cruce[0], et.lado === "derecha" ? et.x + ancho : et.x);
      const arr = Math.min(y0, et.y - medio);
      const aba = Math.max(y1, et.y + medio);
      if ((der - izq) * k <= ANCHO * 0.94 && (aba - arr) * k <= ALTO * 0.78) {
        return acotarVista({ k, tx: ANCHO / 2 - ((izq + der) / 2) * k, ty: ALTO * 0.53 - ((arr + aba) / 2) * k });
      }
    }
  }
  return GENERAL;
}

const CAJAS = Object.fromEntries(
  corredor.cuencas.map((g) => [g.basin_id, caja(g.contorno.match(/-?\d+(\.\d+)?/g).map(Number))]),
);
const ENCUADRES = Object.fromEntries(corredor.cuencas.map((g) => [g.basin_id, encuadre(g)]));
const iguales = (a, b) => a && b && a.k === b.k && a.tx === b.tx && a.ty === b.ty;

export const DURACION_SIMULACION = 15;

/**
 * Crecida ilustrativa a los `t` segundos: llueve en la cabecera, el cauce crece, el frente baja hasta
 * la RN 9 y la tormenta se retira. No usa datos de ninguna estación.
 */
export function crecidaSimulada(t, eta) {
  const fraccion = t >= 2.4 ? suave(rampa(t, 2.4, 11.5)) : null;
  return {
    nivel: t < 2.4 ? "YELLOW" : t < 4.4 ? "ORANGE" : "RED",
    lluvia: rampa(t, 0.5, 3) * (1 - rampa(t, 9, 12.5)),
    crecida: suave(rampa(t, 1.4, 5)),
    fraccion,
    restantes: fraccion == null ? null : eta * (1 - fraccion),
  };
}

/** Segundos transcurridos desde que `serie` cambió a un valor no nulo, cuadro a cuadro. */
function useSegundos(serie) {
  const [t, setT] = useState(0);
  useEffect(() => {
    if (serie == null) return undefined;
    const inicio = performance.now();
    let cuadro = requestAnimationFrame(function paso(ahora) {
      setT(Math.max(0, ahora - inicio) / 1000);
      cuadro = requestAnimationFrame(paso);
    });
    return () => {
      cancelAnimationFrame(cuadro);
      setT(0);
    };
  }, [serie]);
  return serie == null ? 0 : t;
}

const BOTON =
  "pointer-events-auto flex h-7 min-w-7 items-center justify-center rounded-md border border-white/15 bg-slate-950/80 px-1.5 text-[13px] font-bold leading-none text-slate-100 shadow backdrop-blur-sm transition hover:border-cyan-300/60 hover:text-cyan-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 disabled:opacity-35 disabled:hover:border-white/15 disabled:hover:text-slate-100";

/**
 * Ilustración de la landing: el corredor de la RN 9 con las cuatro cuencas sobre relieve sombreado.
 * Las geometrías vienen ya proyectadas (assets/corredor.js); el estado en vivo las colorea y anima
 * (lluvia en la cabecera, cauce crecido, frente que baja a la ruta) y la vista se acerca sola a la
 * cuenca con crecida. Sin crecida real, la misma animación puede verse como simulación ilustrativa.
 */
export default function MapaCorredor({ cuencas = [] }) {
  const [activa, setActiva] = useState(null);
  const [manual, setManual] = useState(null);
  const [arrastrando, setArrastrando] = useState(false);
  const [simulacion, setSimulacion] = useState(null);
  const marco = useRef(null);
  const arrastre = useRef(null);
  const sinAutoinicio = useRef(false);
  const turno = useRef(0);
  const porId = useMemo(() => new Map(cuencas.map((c) => [c.basin_id, c])), [cuencas]);

  // Cuenca con crecida real en curso: la más severa y, a igual nivel, la de arribo más próximo.
  const real = corredor.cuencas
    .map((g) => ({ id: g.basin_id, vivo: porId.get(g.basin_id) }))
    .filter(({ vivo }) => vivo && (vivo.minutos_restantes != null || NIVELES[vivo.nivel]?.orden >= 2))
    .sort(
      (a, b) =>
        NIVELES[b.vivo.nivel].orden - NIVELES[a.vivo.nivel].orden ||
        (a.vivo.minutos_restantes ?? Infinity) - (b.vivo.minutos_restantes ?? Infinity),
    )[0]?.id;
  const simulada = real ? null : simulacion;
  const t = useSegundos(simulada?.serie ?? null);
  const foco = real ?? simulada?.id ?? null;
  const vista = manual ?? (foco ? ENCUADRES[foco] : GENERAL);
  const marca = vista.k ** -0.6; // los símbolos crecen menos que el mapa al ampliar

  useEffect(() => {
    if (foco) setManual(null);
  }, [foco]);
  useEffect(() => {
    if (simulada && t >= DURACION_SIMULACION) setSimulacion(null);
  }, [simulada, t]);
  // La simulación se muestra sola una vez, cuando el mapa entra en pantalla y no hay nada real que mostrar.
  useEffect(() => {
    if (real || sinAutoinicio.current || typeof IntersectionObserver === "undefined") return undefined;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return undefined;
    let espera;
    const observador = new IntersectionObserver(
      ([entrada]) => {
        clearTimeout(espera);
        if (!entrada.isIntersecting) return;
        espera = setTimeout(() => {
          if (!sinAutoinicio.current) simular();
        }, 1800);
      },
      { threshold: 0.6 },
    );
    observador.observe(marco.current);
    return () => {
      clearTimeout(espera);
      observador.disconnect();
    };
  }, [real]);

  const mover = (nueva) => {
    sinAutoinicio.current = true;
    setManual(nueva);
  };
  const enfocar = (id) => mover(iguales(vista, ENCUADRES[id]) ? null : ENCUADRES[id]);
  // Cada simulación recorre la cuenca siguiente, empezando por Volcán.
  function simular() {
    sinAutoinicio.current = true;
    setManual(null);
    if (simulada) return setSimulacion(null);
    turno.current += 1;
    return setSimulacion({ id: corredor.cuencas[(turno.current - 1) % corredor.cuencas.length].basin_id, serie: turno.current });
  }
  const alPresionar = (e) => {
    if (vista.k <= 1 || e.button !== 0 || e.target.closest("a, button")) return;
    arrastre.current = { x: e.clientX, y: e.clientY, vista, escala: ANCHO / e.currentTarget.getBoundingClientRect().width };
  };
  const alArrastrar = (e) => {
    const a = arrastre.current;
    if (!a) return;
    const [dx, dy] = [e.clientX - a.x, e.clientY - a.y];
    if (!a.movido && Math.hypot(dx, dy) < 5) return;
    if (!a.movido) e.currentTarget.setPointerCapture?.(e.pointerId);
    a.movido = true;
    setArrastrando(true);
    mover(acotarVista({ k: a.vista.k, tx: a.vista.tx + dx * a.escala, ty: a.vista.ty + dy * a.escala }));
  };
  const alSoltar = () => {
    arrastre.current = null;
    setArrastrando(false);
  };

  const capas = corredor.cuencas.map((g) => {
    const vivo = porId.get(g.basin_id);
    const eta = Math.round(vivo?.eta_min ?? g.eta_min);
    const sim = simulada?.id === g.basin_id ? crecidaSimulada(t, eta) : null;
    const nivel = sim ? NIVELES[sim.nivel] : vivo ? NIVELES[vivo.nivel] : null;
    const orden = nivel?.orden ?? 0;
    const restantes = sim ? sim.restantes : vivo?.minutos_restantes;
    const fraccion = sim ? sim.fraccion : restantes != null && eta > 0 ? 1 - restantes / eta : null;
    // Con el enlace principal caído, la lluvia vigente es la del último paquete de respaldo.
    const mm = emergenciaReciente(vivo?.nodo)?.rain_mm_15m ?? vivo?.nodo?.ultima?.metrics?.rain_mm_15m ?? 0;
    const lluvia = sim ? sim.lluvia : entre(mm / 20, 0, 1);
    return {
      g,
      vivo,
      nivel,
      orden,
      eta,
      restantes,
      lluvia: lluvia < 0.02 ? 0 : lluvia,
      crecida: sim ? sim.crecida : fraccion != null ? 1 : [0, 0.35, 0.7, 1][orden],
      onda: fraccion != null ? avanceEnTramo(g.tramo, fraccion) : null,
      llegada: fraccion != null && fraccion >= 1,
      simulada: Boolean(sim),
      color: nivel?.color ?? NEUTRO,
    };
  });
  const km = [10, 5, 2, 1].find((d) => (d / corredor.km_px / ANCHO) * vista.k <= 0.26) ?? 1;
  const enFoco = capas.find(({ g }) => g.basin_id === foco);

  return (
    <figure className="m-0">
      <div
        className="overflow-hidden rounded-2xl bg-[#070d18] shadow-[0_24px_70px_-20px_rgba(8,47,73,0.55)] ring-1 ring-slate-900/10"
        onMouseLeave={() => setActiva(null)}
      >
        <div
          ref={marco}
          className={`relative w-full select-none overflow-clip ${arrastrando ? "corredor-arrastre cursor-grabbing" : vista.k > 1 ? "cursor-grab" : ""}`}
          style={{ aspectRatio: `${ANCHO} / ${ALTO}`, touchAction: vista.k > 1 ? "none" : "pan-y" }}
          onPointerDown={alPresionar}
          onPointerMove={alArrastrar}
          onPointerUp={alSoltar}
          onPointerCancel={alSoltar}
        >
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
            <pattern id="corredor-lluvia" width="34" height="72" patternUnits="userSpaceOnUse" patternTransform="rotate(18)">
              <path d="M9,2v24M26,38v24" stroke="#e0f2fe" strokeWidth="2.4" strokeLinecap="round" />
            </pattern>
            {corredor.cuencas.map((g) => (
              <clipPath key={g.basin_id} id={`corredor-corte-${g.basin_id}`}>
                <path d={g.contorno} />
              </clipPath>
            ))}
          </defs>

          <g className="corredor-vista" style={{ transform: `translate(${vista.tx}px, ${vista.ty}px) scale(${vista.k})` }}>
          <image href={relieve} width={ANCHO} height={ALTO} preserveAspectRatio="xMidYMid slice" />

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
                onClick={() => enfocar(g.basin_id)}
              />
            );
          })}

          {/* Lluvia sobre la cuenca, recortada a su contorno */}
          {capas.map(({ g, lluvia }) => {
            if (!lluvia) return null;
            const [x0, y0, x1, y1] = CAJAS[g.basin_id];
            return (
              <g key={g.basin_id} data-lluvia={g.basin_id} clipPath={`url(#corredor-corte-${g.basin_id})`} opacity={lluvia} pointerEvents="none">
                <path d={g.contorno} fill="#020617" fillOpacity="0.4" />
                <rect
                  x={x0 - 80}
                  y={y0 - 80}
                  width={x1 - x0 + 160}
                  height={y1 - y0 + 160}
                  fill="url(#corredor-lluvia)"
                  fillOpacity="0.75"
                  className="corredor-llueve"
                />
              </g>
            );
          })}

          {/* Río Grande y RN 9 */}
          <g fill="none" strokeLinecap="round" strokeLinejoin="round" pointerEvents="none">
            <path d={corredor.rio} stroke="#60a5fa" strokeOpacity="0.45" strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
            <path d={corredor.rn9} stroke="#070d18" strokeOpacity="0.9" strokeWidth="6" vectorEffect="non-scaling-stroke" />
            <path d={corredor.rn9} stroke="#fbbf24" strokeWidth="2.6" vectorEffect="non-scaling-stroke" />
          </g>

          {/* Cauces con flujo animado hacia la ruta; la onda de crecida avanza con la cuenta regresiva */}
          {capas.map(({ g, color, orden, onda, crecida, simulada }) => {
            // Tramo crecido: de la naciente a la estación y, desde ahí, hasta donde llegó el frente.
            const crecido = crecida > 0 ? `${g.cabecera}${onda ? `L${onda.trazo.slice(1)}` : ""}` : null;
            return (
            <g key={g.basin_id} fill="none" strokeLinecap="round" strokeLinejoin="round" pointerEvents="none">
              {orden >= 2 && (
                <circle cx={g.tramo[0][0]} cy={g.tramo[0][1]} r="150" fill="url(#corredor-celda)" color={color} className="corredor-latido" />
              )}
              <path d={g.cauce} stroke="#22d3ee" strokeOpacity="0.14" strokeWidth="9" vectorEffect="non-scaling-stroke" />
              <path d={g.cauce} stroke="#22d3ee" strokeOpacity="0.3" strokeWidth="5" vectorEffect="non-scaling-stroke" />
              <path d={g.cauce} stroke="#67e8f9" strokeWidth="1.8" vectorEffect="non-scaling-stroke" />
              {crecido && (
                <g className={simulada ? "" : "corredor-crece"}>
                  <path d={crecido} stroke={color} strokeOpacity="0.3" strokeWidth={5 + 13 * crecida} vectorEffect="non-scaling-stroke" className="corredor-latido" />
                  <path d={crecido} stroke={color} strokeWidth={1.8 + 4.4 * crecida} vectorEffect="non-scaling-stroke" />
                  <path d={crecido} stroke="#fff" strokeOpacity="0.85" strokeWidth={0.8 + 1.2 * crecida} vectorEffect="non-scaling-stroke" className="corredor-flujo" style={{ animationDuration: "0.45s" }} />
                </g>
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
                <g style={{ transform: `translate(${onda.punto[0]}px, ${onda.punto[1]}px)`, transition: simulada ? "none" : "transform 1s linear" }}>
                  <g className="corredor-marca" style={{ transform: `scale(${marca})` }}>
                    <circle r="26" fill={color} fillOpacity="0.25" className="corredor-pulso" />
                    <circle r="11" fill={color} stroke="#fff" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
                  </g>
                </g>
              )}
            </g>
            );
          })}

          {/* Localidades de referencia */}
          {corredor.localidades.map(({ nombre, xy: [x, y] }) => (
            <g key={nombre} pointerEvents="none" className="corredor-marca" style={{ transform: `scale(${marca})`, transformOrigin: `${x}px ${y}px` }}>
              <circle cx={x} cy={y} r="6" fill="#e2e8f0" fillOpacity="0.9" />
              <text x={x + 16} y={y + 8} fontSize="24" fill="#e2e8f0" fillOpacity="0.85" stroke="#070d18" strokeWidth="5" paintOrder="stroke">
                {nombre}
              </text>
            </g>
          ))}

          {/* Estaciones de cabecera, cruces con la RN 9 y línea guía hacia cada etiqueta */}
          {capas.map(({ g, vivo, color, orden, llegada, simulada }) => {
            const [ex, ey] = g.estacion;
            const [cx, cy] = g.cruce;
            const et = ETIQUETAS[g.basin_id];
            const enlace = COLOR_ENLACE[vivo ? estadoEnlace(vivo.nodo, vivo.origen) : "online"];
            return (
              <g key={g.basin_id} pointerEvents="none">
                <line x1={cx} y1={cy} x2={et.guia?.[0] ?? et.x} y2={et.guia?.[1] ?? et.y} stroke="#e2e8f0" strokeOpacity="0.55" strokeWidth="1" vectorEffect="non-scaling-stroke" />
                <g className="corredor-marca" style={{ transform: `scale(${marca})`, transformOrigin: `${ex}px ${ey}px` }}>
                  <circle cx={ex} cy={ey} r="20" fill="none" stroke={enlace} strokeWidth="1.2" vectorEffect="non-scaling-stroke" className="corredor-pulso" />
                  <circle cx={ex} cy={ey} r="9" fill={enlace} stroke="#070d18" strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
                </g>
                <g className="corredor-marca" style={{ transform: `scale(${marca})`, transformOrigin: `${cx}px ${cy}px` }}>
                {orden >= 2 && <circle cx={cx} cy={cy} r="24" fill={color} fillOpacity="0.3" className="corredor-pulso" />}
                {llegada && (
                  <>
                    <circle cx={cx} cy={cy} r="46" fill="none" stroke={color} strokeWidth="2" vectorEffect="non-scaling-stroke" className="corredor-pulso" />
                    <circle cx={cx} cy={cy} r="46" fill={color} fillOpacity="0.35" className="corredor-pulso" style={{ animationDelay: "-1.2s" }} />
                  </>
                )}
                <rect
                  x={cx - 11}
                  y={cy - 11}
                  width="22"
                  height="22"
                  rx="3"
                  transform={`rotate(45 ${cx} ${cy})`}
                  fill={vivo || simulada ? color : "#e2e8f0"}
                  stroke="#070d18"
                  strokeWidth="1.5"
                  vectorEffect="non-scaling-stroke"
                />
                </g>
              </g>
            );
          })}
          </g>
          <rect width={ANCHO} height={ALTO} fill="url(#corredor-vineta)" pointerEvents="none" />
          <rect width={ANCHO} height={ALTO} fill="url(#corredor-velo)" pointerEvents="none" />
        </svg>

        {/* Título */}
        <div className="pointer-events-none absolute left-3 top-3 z-20 sm:left-4 sm:top-4">
          <div className="text-[9px] font-semibold uppercase tracking-[0.28em] text-cyan-300 sm:text-[10px]">
            Corredor monitoreado
          </div>
          <div className="text-sm font-bold text-white sm:text-base">Ruta Nacional 9 · Jujuy</div>
          {enFoco && (
            <div
              role="status"
              className={`mt-1.5 inline-block rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider sm:text-[10px] ${
                simulada ? "bg-amber-300 text-slate-950" : "bg-slate-950/80 text-cyan-200 ring-1 ring-cyan-300/40"
              }`}
            >
              {simulada ? "Simulación ilustrativa · no es un evento real" : `Siguiendo la crecida en ${enFoco.g.localidad}`}
            </div>
          )}
          {!real && (
            <button type="button" className={`${BOTON} mt-1.5 px-2 text-[10px] sm:text-[11px]`} aria-pressed={Boolean(simulada)} onClick={simular}>
              {simulada ? "■ Detener" : "▶ Simular crecida"}
            </button>
          )}
        </div>

        {/* Etiquetas de cuenca: enlazan al monitor y amplían el detalle al pasar o enfocar */}
        {capas.map(({ g, nivel, eta, restantes, color, llegada, simulada: esSimulada }) => {
          const et = ETIQUETAS[g.basin_id];
          const destacada = activa === g.basin_id;
          const [ex, ey] = [et.x * vista.k + vista.tx, et.y * vista.k + vista.ty];
          // Fuera del cuadro no se ve ni recibe foco: si no, el teclado llevaría a un enlace recortado.
          const fuera = ex < 0 || ex > ANCHO || ey < 0 || ey > ALTO;
          return (
            <Link
              key={g.basin_id}
              to={`/monitor?cuenca=${g.basin_id}`}
              onMouseEnter={() => setActiva(g.basin_id)}
              onFocus={() => setActiva(g.basin_id)}
              onBlur={() => setActiva(null)}
              draggable={false}
              className={`corredor-etiqueta absolute -translate-y-1/2 rounded-lg border bg-slate-950/75 px-2 py-1 text-left shadow-lg backdrop-blur-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300 sm:px-2.5 sm:py-1.5 ${
                destacada ? "z-10 border-white/40 bg-slate-950/90" : "border-white/10"
              } ${activa && !destacada ? "opacity-60" : ""} ${fuera ? "invisible" : ""}`}
              style={{
                [et.lado === "derecha" ? "left" : "right"]: `${((et.lado === "derecha" ? ex : ANCHO - ex) / ANCHO) * 100}%`,
                top: `${(ey / ALTO) * 100}%`,
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
                  <b style={{ color }}>
                    {llegada ? "arribo a la RN 9" : `arribo en ${cuenta(restantes)}`}
                    {esSimulada && " · simulado"}
                  </b>
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

        {/* Norte, zoom, simulación y escala */}
        <div className="pointer-events-none absolute right-3 top-3 z-20 flex flex-col items-end gap-1 sm:right-4 sm:top-4">
          <div className="tabular mb-1 text-[10px] font-bold text-slate-200">N ↑</div>
          <button type="button" className={BOTON} aria-label="Acercar" title="Acercar" disabled={vista.k >= ZOOM_MAX} onClick={() => mover(ampliar(vista, 1.5))}>
            +
          </button>
          <button type="button" className={BOTON} aria-label="Alejar" title="Alejar" disabled={vista.k <= 1} onClick={() => mover(ampliar(vista, 1 / 1.5))}>
            −
          </button>
          <button
            type="button"
            className={BOTON}
            aria-label={foco ? "Volver al zoom automático" : "Ver todo el corredor"}
            title={foco ? "Volver al zoom automático" : "Ver todo el corredor"}
            disabled={!manual}
            onClick={() => mover(null)}
          >
            ⤢
          </button>
        </div>
        <div
          className="corredor-escala tabular pointer-events-none absolute bottom-3 left-3 text-[9px] text-slate-300 sm:bottom-4 sm:left-4 sm:text-[10px]"
          style={{ width: `${(km / corredor.km_px / ANCHO) * vista.k * 100}%` }}
        >
          <div className="mb-0.5 flex justify-between">
            <span>0</span>
            <span>{km} km</span>
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
