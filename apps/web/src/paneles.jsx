import { useEffect, useMemo, useState } from "react";
import { cuenta, emergenciaReciente, ESCENARIOS, estadoEnlace, hora, NIVELES, registroLocal } from "./niveles.js";
import { json, useSparkline, useSondeo } from "./hooks.js";
import InterruptorTema from "./InterruptorTema.jsx";
import { useUI } from "./store.js";

/* ---------- Top bar (spec §5.1, 48px) ---------- */
export function TopBar({ conectado }) {
  const { modoSimulador, alternarSimulador, vista3D, alternarVista } = useUI();
  return (
    <header className="panel-crisis absolute left-3 right-3 top-3 z-20 flex h-12 items-center justify-between gap-3 px-4">
      <div className="flex items-center gap-3">
        <span className="text-sm font-bold tracking-wide">QuebradaAlert</span>
        <span className="hidden text-[10px] uppercase tracking-widest text-tinta-2 sm:inline">
          RN 9 · Quebrada de Humahuaca
        </span>
      </div>
      <div className="flex items-center gap-2 text-[11px]">
        <button
          type="button"
          onClick={alternarVista}
          className={`rounded border px-2 py-1 font-semibold transition ${
            vista3D ? "border-agua/70 bg-agua/15 text-agua" : "border-borde-fuerte text-tinta-2 hover:bg-realce"
          }`}
          title="Vista 2D / 3D (M)"
        >
          {vista3D ? "3D" : "2D"}
        </button>
        <button
          type="button"
          onClick={alternarSimulador}
          className={`rounded border px-2 py-1 font-semibold transition ${
            modoSimulador
              ? "border-amarillo/70 bg-amarillo/15 text-amarillo"
              : "border-borde-fuerte text-tinta-2 hover:bg-realce"
          }`}
          title="Consola de crisis (S)"
        >
          {modoSimulador ? "MODO: SIM" : "MODO: VIVO"}
        </button>
        <span className={`rounded border px-2 py-1 ${conectado ? "border-verde/50 text-verde" : "border-rojo/50 text-rojo"}`}>
          {conectado ? "● servidor" : "● sin servidor"}
        </span>
        <span className="hidden rounded border border-amarillo/60 px-2 py-1 font-semibold text-amarillo md:inline">
          DEMO · datos simulados
        </span>
        <InterruptorTema />
      </div>
    </header>
  );
}

/* ---------- Alert banner (spec §5.3 NARANJA/ROJO) ---------- */
export function AlertBanner({ cuencas, alVerParte }) {
  const peor = cuencas
    .filter((c) => c.nivel === "ORANGE" || c.nivel === "RED")
    .sort((a, b) => NIVELES[b.nivel].orden - NIVELES[a.nivel].orden)[0];
  if (!peor) return null;
  const nivel = NIVELES[peor.nivel];
  const critico = peor.nivel === "RED";
  const eta = cuenta(peor.minutos_restantes);
  return (
    <div
      className={`panel-crisis absolute left-1/2 top-16 z-20 flex w-[min(560px,calc(100vw-2rem))] -translate-x-1/2 items-center justify-between gap-3 border px-4 py-2.5 ${
        critico ? "border-rojo/70" : "border-naranja/60"
      }`}
      role="alert"
    >
      <div className="min-w-0">
        <div className="text-sm font-bold" style={{ color: nivel.color }}>
          {nivel.nombre === "ROJO" ? "⚠ " : ""}ALERTA {nivel.nombre}: {peor.localidad.toUpperCase()}
          {eta && eta !== "00:00" ? ` · ETA RN 9: ${eta}` : ""}
        </div>
        <div className="truncate text-[11px] text-tinta-2">{peor.accion}</div>
      </div>
      <button
        type="button"
        onClick={() => alVerParte(peor.basin_id)}
        className="shrink-0 rounded border border-borde-fuerte px-2.5 py-1 text-xs font-semibold text-tinta hover:bg-realce"
      >
        Parte
      </button>
    </div>
  );
}

/* ---------- Panel izquierdo: lista de cuencas (spec §5.4.A) ---------- */
function Sparkline({ puntos }) {
  if (puntos.length < 2) return <div className="h-6" />;
  const w = 220;
  const h = 22;
  const max = Math.max(...puntos, 1);
  const paso = w / (puntos.length - 1);
  const linea = puntos.map((v, i) => `${(i * paso).toFixed(1)},${(h - (v / max) * (h - 3) - 1).toFixed(1)}`);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-6 w-full" preserveAspectRatio="none">
      <polyline points={linea.join(" ")} fill="none" className="stroke-tinta-3" strokeWidth="1.2" />
    </svg>
  );
}

function estadoEnlaceLocal(cuenca) {
  const e = estadoEnlace(cuenca.nodo, cuenca.origen);
  return {
    online: { color: "var(--agua)", texto: "● Celular" },
    lora: { color: "var(--lora)", texto: "◉ LoRa respaldo" },
    offline: { color: "var(--tinta-3)", texto: "○ Sin enlace" },
  }[e];
}

function TarjetaCuenca({ cuenca, activa, alElegir }) {
  const nivel = NIVELES[cuenca.nivel];
  const m = cuenca.nodo.ultima?.metrics;
  const em = emergenciaReciente(cuenca.nodo);
  const restante = cuenta(cuenca.minutos_restantes);
  const puntos = useSparkline(cuenca.nodo.node_id);
  const enlace = estadoEnlaceLocal(cuenca);
  return (
    <button
      type="button"
      onClick={alElegir}
      className={`panel-crisis w-full p-3 text-left transition ${
        activa ? "ring-2 ring-agua/70" : "hover:bg-realce"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate text-sm font-semibold">{cuenca.localidad} · {cuenca.curso}</div>
        </div>
        <span
          className="flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-bold text-sobre-nivel"
          style={{ background: nivel.color }}
          title={nivel.nombre}
        >
          <span aria-hidden>{nivel.forma}</span> {nivel.nombre}
        </span>
      </div>
      {restante && (
        <div className="tabular mt-2 rounded bg-hundida px-2 py-1 text-center">
          <div className="text-[9px] uppercase tracking-wide text-tinta-2">ETA RN 9</div>
          <div className="text-lg font-bold" style={{ color: nivel.color }}>
            {restante === "00:00" ? "plazo cumplido" : restante}
          </div>
        </div>
      )}
      <div className="tabular mt-2 grid grid-cols-3 gap-1 text-[11px] text-tinta-2">
        <span>{em ? `${em.rain_mm_15m} mm LoRa` : m ? `${m.rain_mm_15m} mm` : "—"}</span>
        <span>{em ? `+${em.water_level_rise_15m_cm} cm` : m ? `${m.water_level_cm} cm` : "—"}</span>
        <span>{m ? `${m.battery_soc_pct}% bat` : "—"}</span>
      </div>
      <Sparkline puntos={puntos} />
      <div className="mt-1 flex items-center justify-between text-[10px]">
        <span style={{ color: enlace.color }}>{enlace.texto}</span>
        <span className="text-tinta-2">
          {(cuenca.nodo.huecos ?? 0) > 0 ? `buf ${cuenca.nodo.huecos}` : "en vivo"}
        </span>
      </div>
    </button>
  );
}

export function BasinList({ cuencas, seleccion, alElegir }) {
  const ordenadas = useMemo(
    () => [...cuencas].sort((a, b) => NIVELES[b.nivel].orden - NIVELES[a.nivel].orden),
    [cuencas],
  );
  return (
    <div className="absolute bottom-3 left-3 top-16 z-10 flex w-[300px] flex-col gap-2 overflow-y-auto pr-1">
      {ordenadas.map((c) => (
        <TarjetaCuenca key={c.basin_id} cuenca={c} activa={c.basin_id === seleccion} alElegir={() => alElegir(c.basin_id)} />
      ))}
    </div>
  );
}

/* ---------- Gráfica DuckDB con transiciones y evento resaltado (spec §5.4.B) ---------- */
export function Grafico({ historia, eventoResaltado }) {
  if (historia.length < 2) return <div className="py-6 text-center text-xs text-tinta-2">Sin lecturas todavía.</div>;
  const ancho = 420;
  const alto = 120;
  const t = historia.map((h) => Date.parse(h.ts));
  const [t0, t1] = [t[0], t[t.length - 1]];
  const x = (v) => ((v - t0) / (t1 - t0 || 1)) * ancho;
  const maxLluvia = Math.max(30, ...historia.map((h) => h.rain_mm_15m));
  const maxNivel = Math.max(100, ...historia.map((h) => h.water_level_cm));
  const linea = historia.map((h, i) => `${x(t[i]).toFixed(1)},${(alto - (h.water_level_cm / maxNivel) * alto).toFixed(1)}`);
  // Transiciones de nivel local (edge_local_alert cambia entre lecturas)
  const transiciones = [];
  for (let i = 1; i < historia.length; i++) {
    if (historia[i].edge_local_alert !== historia[i - 1].edge_local_alert) {
      transiciones.push({ x: x(t[i]), nivel: historia[i].edge_local_alert });
    }
  }
  const xEvento = eventoResaltado ? x(Date.parse(eventoResaltado)) : null;
  const enRango = (v) => v >= 0 && v <= ancho;
  return (
    <div>
      <svg viewBox={`0 0 ${ancho} ${alto}`} className="w-full rounded bg-hundida">
        <defs>
          <pattern id="rayado" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="4" height="4" className="fill-recuperado" fillOpacity="0.25" />
            <line x1="0" y1="0" x2="0" y2="4" className="stroke-recuperado" strokeWidth="1.4" />
          </pattern>
        </defs>
        {historia.map((h, i) => {
          const altura = (h.rain_mm_15m / maxLluvia) * alto;
          return (
            <rect
              key={h.seq}
              x={x(t[i]) - 1}
              y={alto - altura}
              width="2"
              height={altura}
              fill={h.is_historical ? "url(#rayado)" : "var(--agua)"}
              fillOpacity={h.is_historical ? 1 : 0.9}
            />
          );
        })}
        <polyline points={linea.join(" ")} fill="none" className="stroke-tinta" strokeWidth="1.5" />
        {transiciones.filter((tr) => enRango(tr.x)).map((tr, i) => (
          <g key={i}>
            <line x1={tr.x} y1="0" x2={tr.x} y2={alto} stroke={NIVELES[tr.nivel]?.color ?? "var(--tinta)"} strokeWidth="1" strokeDasharray="3 2" />
            <circle cx={tr.x} cy="4" r="2.5" fill={NIVELES[tr.nivel]?.color ?? "var(--tinta)"} />
          </g>
        ))}
        {xEvento != null && enRango(xEvento) && (
          <line x1={xEvento} y1="0" x2={xEvento} y2={alto} className="stroke-tinta" strokeWidth="1.6" />
        )}
      </svg>
      <div className="mt-1 flex flex-wrap gap-x-3 text-[10px] text-tinta-2">
        <span><b className="text-agua">▮</b> lluvia en vivo</span>
        <span><b className="text-recuperado">▮</b> recuperada del búfer</span>
        <span><b className="text-tinta-2">—</b> nivel del cauce</span>
        <span className="ml-auto">{hora(historia[0].ts)} → {hora(historia[historia.length - 1].ts)} · hora local</span>
      </div>
    </div>
  );
}

/* ---------- Inspector derecho con pestañas (spec §5.4.B) ---------- */
function PestanaHidrologia({ cuenca, alVerParte }) {
  const nodeId = cuenca.nodo.node_id;
  const historia = useSondeo(`/api/historia/${nodeId}?limite=400`, 1500, []);
  const fuentes = useSondeo("/api/fuentes", 30000, null);
  const lecturasFuentes = useSondeo("/api/fuentes/lecturas?limite=30", 30000, null);
  const ultimaLecturaPorFuente = useMemo(() => {
    const lista = lecturasFuentes?.lecturas ?? [];
    const mapa = new Map();
    for (const r of lista) {
      const prev = mapa.get(r.fuente);
      if (!prev || (r.estacion_id === nodeId && prev.estacion_id !== nodeId)) {
        mapa.set(r.fuente, r);
      }
    }
    return mapa;
  }, [lecturasFuentes, nodeId]);
  const { eventoResaltado } = useUI();
  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-borde bg-realce p-3">
        <div className="text-[10px] uppercase tracking-wide text-tinta-2">Recomendación automática</div>
        <p className="mt-1 text-sm font-medium">{cuenca.accion}</p>
        <p className="mt-1 text-[10px] text-tinta-2">
          Kirpich: {cuenca.eta_min} min estación → RN 9 · la decisión corresponde a Defensa Civil, DPRH y Vialidad
          Nacional.
        </p>
        <button
          type="button"
          onClick={() => alVerParte(cuenca.basin_id)}
          className="mt-2 w-full rounded border border-borde-fuerte bg-realce px-3 py-1.5 text-xs font-bold text-tinta-2 hover:bg-realce-fuerte"
        >
          Generar Parte de Situación
        </button>
      </div>
      <div>
        <div className="mb-1 text-[10px] uppercase tracking-wide text-tinta-2">Serie reconstruida (DuckDB)</div>
        <Grafico historia={historia} eventoResaltado={eventoResaltado} />
      </div>
      {fuentes?.fuentes?.length > 0 && (
        <div className="rounded-lg border border-borde bg-elevada p-2.5 text-[11px]">
          <div className="mb-1.5 flex items-center justify-between text-[10px] uppercase tracking-wide text-tinta-2">
            <span>Fuentes externas (referencia)</span>
            <span className="tabular font-semibold">{fuentes.lecturas_totales ?? 0} reg.</span>
          </div>
          <ul className="space-y-1">
            {fuentes.fuentes.map((f) => {
              const ult = ultimaLecturaPorFuente.get(f.id);
              return (
                <li key={f.id} className="flex items-center justify-between gap-2 text-tinta-2">
                  <div className="min-w-0">
                    <div className="truncate">{f.nombre}</div>
                    {ult && (
                      <div className="tabular font-mono text-[10px] text-tinta-2">
                        Última: {ult.valor} {ult.unidad ?? "mm"} · {hora(ult.ts)}
                      </div>
                    )}
                  </div>
                  <span
                    className={`shrink-0 font-mono text-[10px] ${
                      f.ultima?.estado === "ok"
                        ? "text-verde"
                        : f.ultima?.estado === "error"
                          ? "text-rojo"
                          : "text-tinta-3"
                    }`}
                  >
                    {f.ultima ? `${f.ultima.estado} (${f.ultima.nuevas})` : "pendiente"}
                  </span>
                </li>
              );
            })}
          </ul>
          <div className="mt-1.5 text-[10px] text-tinta-3">
            Capa de referencia (SNIH / Open-Meteo) — no dispara el semáforo táctico.
          </div>
        </div>
      )}
    </div>
  );
}

function PestañaNodo({ cuenca, simulador }) {
  const sim = simulador[cuenca.nodo.node_id];
  if (!sim) return <div className="text-xs text-tinta-2">El nodo simulado no responde.</div>;
  const m = sim.ultima?.metrics ?? {};
  return (
    <div className="space-y-2 text-xs">
      <div className="grid grid-cols-2 gap-2">
        <div className="rounded bg-hundida p-2">
          <div className="text-tinta-2">Conectividad</div>
          <div className={`font-bold ${sim.connectivity_state === "ONLINE" ? "text-verde" : "text-amarillo"}`}>
            {sim.connectivity_state}
          </div>
        </div>
        <div className="rounded bg-hundida p-2">
          <div className="text-tinta-2">Enlace celular</div>
          <div className={sim.enlace_activo ? "text-verde" : "text-rojo"}>{sim.enlace_activo ? "activo" : "cortado"}</div>
        </div>
        <div className="rounded bg-hundida p-2">
          <div className="text-tinta-2">Cola SQLite</div>
          <div className="tabular text-base">{sim.en_cola}</div>
        </div>
        <div className="rounded bg-hundida p-2">
          <div className="text-tinta-2">Baliza local</div>
          <div className={sim.baliza ? "font-bold text-rojo" : "text-tinta-2"}>{sim.baliza ? "ACTIVA" : "apagada"}</div>
        </div>
      </div>
      <div className="rounded bg-hundida p-2 text-[11px] text-tinta-2">
        Batería {m.battery_soc_pct ?? "—"}% · lluvia previa 72 h {m.antecedent_rain_72h_mm ?? "—"} mm · turbidez{" "}
        {m.turbidity_proxy_ntu ?? "—"} NTU
      </div>
      <div>
        <div className="mb-1 text-[10px] uppercase tracking-wide text-tinta-2">Registro del nodo</div>
        <pre className="tabular max-h-36 overflow-y-auto rounded bg-hundida p-2 text-[10px] leading-4 text-verde">
          {sim.registro?.length ? sim.registro.map(registroLocal).join("\n") : "Sin novedades."}
        </pre>
      </div>
    </div>
  );
}

const TIPOS_EVENTO = {
  ALERTA: "Alertas",
  DESCENSO: "Alertas",
  EN_LINEA: "Conectividad",
  ISLA: "Conectividad",
  NBIRTH: "Conectividad",
  NDEATH: "Conectividad",
  RECUPERACION: "Recuperación",
  RESPALDO: "Recuperación",
};

function PestanaEventos({ eventos, basinId, alResaltar }) {
  const [filtro, setFiltro] = useState("Todos");
  const propios = eventos.filter((e) => e.basin_id === basinId);
  const tipos = ["Todos", "Alertas", "Conectividad", "Recuperación"];
  const visibles = propios.filter((e) => filtro === "Todos" || TIPOS_EVENTO[e.tipo] === filtro);
  return (
    <div>
      <div className="mb-2 flex gap-1">
        {tipos.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setFiltro(t)}
            className={`rounded px-2 py-0.5 text-[10px] font-semibold ${
              filtro === t ? "bg-realce-fuerte text-tinta" : "bg-hundida text-tinta-2 hover:bg-realce"
            }`}
          >
            {t}
          </button>
        ))}
      </div>
      <ul className="space-y-1 text-[11px]">
        {visibles.slice(0, 25).map((e) => (
          <li key={e.id}>
            <button
              type="button"
              onClick={() => alResaltar(e.ts)}
              className="flex w-full gap-2 rounded px-1 py-0.5 text-left hover:bg-realce"
              title="Resaltar en la gráfica"
            >
              <span className="tabular shrink-0 font-mono text-tinta-2">{hora(e.ts)}</span>
              <span className={`shrink-0 font-semibold ${e.nivel ? NIVELES[e.nivel].texto : "text-tinta-2"}`}>
                {e.tipo}
                {e.nivel ? ` ${NIVELES[e.nivel].nombre}` : ""}
              </span>
              <span className="truncate text-tinta-2">{e.detalle}</span>
            </button>
          </li>
        ))}
        {!visibles.length && <li className="text-tinta-2">Sin eventos de este tipo.</li>}
      </ul>
    </div>
  );
}

export function Inspector({ cuenca, eventos, simulador, alVerParte }) {
  const [pestana, setPestana] = useState("hidro");
  const { resaltarEvento } = useUI();
  if (!cuenca) return null;
  const pestanas = [
    ["hidro", "Hidrología"],
    ["nodo", "Nodo y Red"],
    ["eventos", "Eventos"],
  ];
  return (
    <aside className="panel-crisis absolute bottom-3 right-3 top-16 z-10 flex w-[min(420px,calc(100vw-2rem))] flex-col overflow-hidden">
      <div className="border-b border-borde-fuerte px-3 py-2">
        <div className="flex items-center justify-between">
          <div className="min-w-0">
            <div className="truncate text-sm font-bold">{cuenca.localidad} · {cuenca.curso}</div>
            <div className="text-[10px] text-tinta-2">{cuenca.nodo.node_id}</div>
          </div>
          <button
            type="button"
            onClick={() => useUI.getState().cerrarInspector()}
            aria-label="Cerrar inspector"
            className="rounded px-1.5 text-tinta-2 hover:bg-realce hover:text-tinta"
            title="Cerrar (Esc)"
          >
            ✕
          </button>
        </div>
        <div role="tablist" aria-label="Vistas del inspector" className="mt-1.5 flex gap-1">
          {pestanas.map(([id, nombre]) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={pestana === id}
              onClick={() => setPestana(id)}
              className={`rounded px-2 py-0.5 text-[11px] font-semibold ${
                pestana === id ? "bg-realce-fuerte text-tinta" : "text-tinta-2 hover:bg-realce"
              }`}
            >
              {nombre}
            </button>
          ))}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {pestana === "hidro" && <PestanaHidrologia cuenca={cuenca} alVerParte={alVerParte} />}
        {pestana === "nodo" && <PestañaNodo cuenca={cuenca} simulador={simulador} />}
        {pestana === "eventos" && <PestanaEventos eventos={eventos} basinId={cuenca.basin_id} alResaltar={resaltarEvento} />}
      </div>
    </aside>
  );
}

/* ---------- Consola de crisis (spec §5.4.D) ---------- */
const PRESETS = [
  {
    nombre: "Tormenta convectiva + corte celular",
    orden: { escenario: "tormenta_convectiva", enlace_activo: false },
  },
  {
    nombre: "Suelo saturado + lluvia moderada",
    orden: { escenario: "tormenta_moderada", lluvia_previa_72h_mm: 35 },
  },
  {
    nombre: "Reset: todo a verde",
    orden: { escenario: "normal", enlace_activo: true, respaldo_activo: true, lluvia_previa_72h_mm: 0 },
  },
];

export function ConsolaSimulador({ simulador }) {
  const nodos = Object.keys(simulador ?? {});
  const [nodeId, setNodeId] = useState(nodos[0] ?? "");
  const sim = simulador?.[nodeId];
  useEffect(() => {
    if (nodos.length && !nodos.includes(nodeId)) setNodeId(nodos[0]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodos.join(",")]);
  if (!sim) return <div className="text-xs text-tinta-2">El nodo simulado no responde.</div>;
  const saturado = (sim.ultima?.metrics.antecedent_rain_72h_mm ?? 0) > 30;
  const boton = "rounded border px-2 py-1 text-xs font-medium transition";
  return (
    <div className="space-y-2 text-left">
      <div className="flex flex-wrap items-center gap-1">
        <select
          value={nodeId}
          onChange={(e) => setNodeId(e.target.value)}
          className="rounded border border-borde-fuerte bg-hundida px-2 py-1 text-xs text-tinta"
        >
          {nodos.map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        {PRESETS.map((p) => (
          <button
            key={p.nombre}
            type="button"
            onClick={() => ordenSimulador(nodeId, p.orden)}
            className={`${boton} border-recuperado/60 bg-recuperado/10 text-recuperado hover:bg-recuperado/20`}
            title="Preset de un clic"
          >
            {p.nombre}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap gap-1">
        {ESCENARIOS.map(([clave, nombre]) => (
          <button
            key={clave}
            type="button"
            onClick={() => ordenSimulador(nodeId, { escenario: clave })}
            className={`${boton} ${sim.escenario === clave ? "border-agua/70 bg-agua/15 text-agua" : "border-borde-fuerte hover:bg-realce"}`}
          >
            {nombre}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap gap-1">
        <button
          type="button"
          onClick={() => ordenSimulador(nodeId, { enlace_activo: !sim.enlace_activo })}
          className={`${boton} ${sim.enlace_activo ? "border-borde-fuerte hover:bg-realce" : "border-amarillo/70 bg-amarillo/15 text-amarillo"}`}
        >
          {sim.enlace_activo ? "Cortar enlace celular" : "Restablecer enlace"}
        </button>
        <button
          type="button"
          onClick={() => ordenSimulador(nodeId, { respaldo_activo: !sim.respaldo_activo })}
          className={`${boton} ${sim.respaldo_activo ? "border-borde-fuerte hover:bg-realce" : "border-amarillo/70 bg-amarillo/15 text-amarillo"}`}
        >
          {sim.respaldo_activo ? "Cortar respaldo LoRa" : "Restablecer LoRa"}
        </button>
        <button
          type="button"
          onClick={() => ordenSimulador(nodeId, { lluvia_previa_72h_mm: saturado ? 0 : 35 })}
          className={`${boton} border-borde-fuerte hover:bg-realce`}
        >
          {saturado ? "Suelo seco" : "Suelo saturado 72 h"}
        </button>
      </div>
      <div className="tabular grid grid-cols-3 gap-2 text-[11px]">
        <div className="rounded bg-hundida p-2">
          <div className="text-tinta-2">Estado</div>
          <div className={sim.connectivity_state === "ONLINE" ? "text-verde" : "font-bold text-amarillo"}>
            {sim.connectivity_state}
          </div>
        </div>
        <div className="rounded bg-hundida p-2">
          <div className="text-tinta-2">Búfer SQLite</div>
          <div className="text-base">{sim.en_cola}</div>
        </div>
        <div className="rounded bg-hundida p-2">
          <div className="text-tinta-2">Baliza</div>
          <div className={sim.baliza ? "font-bold text-rojo" : "text-tinta-2"}>{sim.baliza ? "ACTIVA" : "apagada"}</div>
        </div>
      </div>
      <pre className="tabular max-h-24 overflow-y-auto rounded bg-hundida p-2 text-[10px] leading-4 text-verde">
        {sim.registro?.length ? sim.registro.slice(-12).map(registroLocal).join("\n") : "Sin novedades."}
      </pre>
    </div>
  );
}

export function ordenSimulador(nodeId, orden) {
  return json(`/api/simulador/${nodeId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(orden),
  }).catch(() => {});
}
