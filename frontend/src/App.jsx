import { useEffect, useRef, useState } from "react";
import Mapa from "./Mapa.jsx";
import { ESCENARIOS, NIVELES, cuenta, hora } from "./niveles.js";

const json = (url, opciones) => fetch(url, opciones).then((r) => (r.ok ? r.json() : Promise.reject(r)));

function useEstado() {
  const [estado, setEstado] = useState({ cuencas: [], eventos: [] });
  const [conectado, setConectado] = useState(false);
  useEffect(() => {
    let ws;
    let reintento;
    let vigente = true;
    const abrir = () => {
      ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
      ws.onopen = () => setConectado(true);
      ws.onmessage = (m) => setEstado(JSON.parse(m.data));
      ws.onclose = () => {
        setConectado(false);
        if (vigente) reintento = setTimeout(abrir, 1000);
      };
    };
    abrir();
    return () => {
      vigente = false;
      clearTimeout(reintento);
      ws.close();
    };
  }, []);
  return [estado, conectado];
}

function useSondeo(url, ms, inicial) {
  const [dato, setDato] = useState(inicial);
  useEffect(() => {
    if (!url) return undefined;
    let vigente = true;
    const pedir = () =>
      json(url)
        .then((d) => vigente && setDato(d))
        .catch(() => {});
    pedir();
    const reloj = setInterval(pedir, ms);
    return () => {
      vigente = false;
      clearInterval(reloj);
    };
  }, [url, ms]);
  return dato;
}

function Tarjeta({ cuenca, activa, alElegir }) {
  const nivel = NIVELES[cuenca.nivel];
  const { nodo } = cuenca;
  const m = nodo.ultima?.metrics;
  const restante = cuenta(cuenca.minutos_restantes);
  return (
    <button
      type="button"
      onClick={alElegir}
      className={`w-full rounded-lg border p-3 text-left transition ${
        activa ? "border-slate-200 bg-slate-800" : "border-slate-700 bg-slate-900 hover:border-slate-500"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div>
          <div className="text-sm font-semibold">{cuenca.localidad}</div>
          <div className="text-xs text-slate-400">{cuenca.curso}</div>
        </div>
        <span className={`rounded px-2 py-0.5 text-xs font-bold text-slate-950 ${nivel.fondo}`}>{nivel.nombre}</span>
      </div>
      {restante && (
        <div className="mt-2 rounded bg-slate-950 px-2 py-1">
          <div className="text-[10px] uppercase tracking-wide text-slate-400">Arribo estimado a la RN 9</div>
          <div className={`font-mono text-2xl font-bold ${nivel.texto}`}>
            {restante === "00:00" ? "plazo cumplido" : restante}
          </div>
        </div>
      )}
      <div className="mt-2 grid grid-cols-3 gap-1 text-xs text-slate-300">
        <span>{m ? `${m.rain_mm_15m} mm/15 min` : "sin datos"}</span>
        <span>{m ? `nivel ${m.water_level_cm} cm` : ""}</span>
        <span>{m ? `batería ${m.battery_soc_pct} %` : ""}</span>
      </div>
      <div className="mt-1 flex items-center justify-between text-xs">
        <span className={nodo.en_linea ? "text-emerald-400" : "text-rose-400"}>
          {nodo.en_linea ? "● enlace activo" : "● sin enlace principal"}
        </span>
        <span className="text-slate-500">dato: {cuenca.origen}</span>
      </div>
    </button>
  );
}

function Grafico({ historia }) {
  if (historia.length < 2) return <div className="text-xs text-slate-500">Sin lecturas todavía.</div>;
  const ancho = 420;
  const alto = 110;
  const t = historia.map((h) => Date.parse(h.ts));
  const [t0, t1] = [t[0], t[t.length - 1]];
  const x = (v) => ((v - t0) / (t1 - t0 || 1)) * ancho;
  const maxLluvia = Math.max(30, ...historia.map((h) => h.rain_mm_15m));
  const maxNivel = Math.max(100, ...historia.map((h) => h.water_level_cm));
  const linea = historia.map((h, i) => `${x(t[i]).toFixed(1)},${(alto - (h.water_level_cm / maxNivel) * alto).toFixed(1)}`);
  return (
    <div>
      <svg viewBox={`0 0 ${ancho} ${alto}`} className="w-full rounded bg-slate-950">
        {historia.map((h, i) => {
          const altura = (h.rain_mm_15m / maxLluvia) * alto;
          return (
            <rect
              key={h.seq}
              x={x(t[i]) - 1}
              y={alto - altura}
              width="2"
              height={altura}
              fill={h.is_historical ? "#a78bfa" : "#38bdf8"}
            />
          );
        })}
        <polyline points={linea.join(" ")} fill="none" stroke="#f8fafc" strokeWidth="1.5" />
      </svg>
      <div className="mt-1 flex flex-wrap gap-x-3 text-[11px] text-slate-400">
        <span>
          <b className="text-sky-400">▮</b> lluvia 15 min, en vivo
        </span>
        <span>
          <b className="text-violet-400">▮</b> lluvia 15 min, recuperada del búfer
        </span>
        <span>
          <b className="text-slate-100">—</b> nivel del cauce
        </span>
        <span>
          {hora(historia[0].ts)} a {hora(historia[historia.length - 1].ts)} UTC
        </span>
      </div>
    </div>
  );
}

function Consola({ nodeId, sim }) {
  const [error, setError] = useState(null);
  const ordenar = (orden) =>
    json(`/api/simulador/${nodeId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(orden),
    })
      .then(() => setError(null))
      .catch(() => setError("El nodo simulado no responde."));
  const boton = "rounded border px-2 py-1 text-xs font-medium transition";
  if (!sim) return <div className="text-xs text-slate-500">El nodo simulado no responde.</div>;
  const saturado = (sim.ultima?.metrics.antecedent_rain_72h_mm ?? 0) > 30;
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1">
        {ESCENARIOS.map(([clave, nombre]) => (
          <button
            key={clave}
            type="button"
            onClick={() => ordenar({ escenario: clave })}
            className={`${boton} ${
              sim.escenario === clave ? "border-sky-400 bg-sky-500/20 text-sky-200" : "border-slate-600 hover:bg-slate-800"
            }`}
          >
            {nombre}
          </button>
        ))}
      </div>
      <div className="flex flex-wrap gap-1">
        <button
          type="button"
          onClick={() => ordenar({ enlace_activo: !sim.enlace_activo })}
          className={`${boton} ${sim.enlace_activo ? "border-slate-600 hover:bg-slate-800" : "border-rose-400 bg-rose-500/20 text-rose-200"}`}
        >
          {sim.enlace_activo ? "Cortar enlace celular" : "Restablecer enlace celular"}
        </button>
        <button
          type="button"
          onClick={() => ordenar({ respaldo_activo: !sim.respaldo_activo })}
          className={`${boton} ${sim.respaldo_activo ? "border-slate-600 hover:bg-slate-800" : "border-rose-400 bg-rose-500/20 text-rose-200"}`}
        >
          {sim.respaldo_activo ? "Cortar respaldo LoRa" : "Restablecer respaldo LoRa"}
        </button>
        <button
          type="button"
          onClick={() => ordenar({ lluvia_previa_72h_mm: saturado ? 0 : 35 })}
          className={`${boton} border-slate-600 hover:bg-slate-800`}
        >
          {saturado ? "Suelo seco" : "Suelo saturado (35 mm en 72 h)"}
        </button>
      </div>
      {error && <div className="text-xs text-rose-400">{error}</div>}
      <div className="grid grid-cols-3 gap-2 text-xs">
        <div className="rounded bg-slate-950 p-2">
          <div className="text-slate-400">Estado del nodo</div>
          <div className={sim.connectivity_state === "ONLINE" ? "text-emerald-400" : "font-bold text-amber-300"}>
            {sim.connectivity_state}
          </div>
        </div>
        <div className="rounded bg-slate-950 p-2">
          <div className="text-slate-400">En el búfer SQLite</div>
          <div className="font-mono text-base">{sim.en_cola}</div>
        </div>
        <div className="rounded bg-slate-950 p-2">
          <div className="text-slate-400">Baliza local</div>
          <div className={sim.baliza ? "font-bold text-red-400" : "text-slate-300"}>{sim.baliza ? "ACTIVA" : "apagada"}</div>
        </div>
      </div>
      <div>
        <div className="mb-1 text-[11px] uppercase tracking-wide text-slate-400">Registro del nodo (reloj {hora(sim.reloj)} UTC)</div>
        <pre className="max-h-28 overflow-y-auto rounded bg-black p-2 text-[11px] leading-4 text-emerald-300">
          {sim.registro.length ? sim.registro.join("\n") : "Sin novedades."}
        </pre>
      </div>
    </div>
  );
}

const Seccion = ({ titulo, children }) => (
  <section className="rounded-lg border border-slate-700 bg-slate-900 p-3">
    <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">{titulo}</h2>
    {children}
  </section>
);

export default function App() {
  const [estado, conectado] = useEstado();
  const [seleccion, setSeleccion] = useState(null);
  const cuenca = estado.cuencas.find((c) => c.basin_id === seleccion) ?? estado.cuencas[0];
  const nodeId = cuenca?.nodo.node_id;
  const simulador = useSondeo("/api/simulador", 1000, {});
  const historia = useSondeo(nodeId ? `/api/historia/${nodeId}?limite=400` : null, 1500, []);
  const anterior = useRef(nodeId);
  const historiaVigente = anterior.current === nodeId ? historia : [];
  anterior.current = nodeId;
  const nivel = cuenca ? NIVELES[cuenca.nivel] : null;

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b border-slate-700 px-4 py-2">
        <div>
          <h1 className="text-lg font-bold">QuebradaAlert</h1>
          <p className="text-xs text-slate-400">Microcuencas tributarias del río Grande · Quebrada de Humahuaca</p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="rounded border border-amber-400 px-2 py-1 font-semibold text-amber-300">
            DEMOSTRACIÓN · datos simulados · umbrales sin calibrar
          </span>
          <span className={conectado ? "text-emerald-400" : "text-rose-400"}>
            {conectado ? "● servidor local" : "● sin servidor"}
          </span>
        </div>
      </header>
      <main className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_300px_460px]">
        <Mapa cuencas={estado.cuencas} seleccion={cuenca?.basin_id} alSeleccionar={setSeleccion} />
        <div className="space-y-2 overflow-y-auto border-l border-slate-700 p-2">
          {estado.cuencas.map((c) => (
            <Tarjeta key={c.basin_id} cuenca={c} activa={c === cuenca} alElegir={() => setSeleccion(c.basin_id)} />
          ))}
        </div>
        <div className="space-y-2 overflow-y-auto border-l border-slate-700 p-2">
          {cuenca && (
            <>
              <Seccion titulo={`${cuenca.localidad} · ${cuenca.curso}`}>
                <div className={`text-sm font-bold ${nivel.texto}`}>
                  {nivel.nombre}
                  {cuenca.desde && <span className="font-normal text-slate-400"> desde {hora(cuenca.desde)} UTC</span>}
                </div>
                <p className="mt-1 text-sm">{cuenca.accion}</p>
                <p className="mt-1 text-[11px] text-slate-400">
                  Recomendación automática. La decisión corresponde a Defensa Civil, la DPRH y Vialidad Nacional.
                </p>
                <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
                  <span>
                    Kirpich: {cuenca.eta_min} min de la estación a la RN 9 · lecturas faltantes: {cuenca.nodo.huecos} ·
                    recuperadas: {cuenca.nodo.recuperadas}
                  </span>
                  <a
                    href={`/api/parte/${cuenca.basin_id}`}
                    target="_blank"
                    rel="noreferrer"
                    className="shrink-0 rounded border border-slate-500 px-2 py-1 text-slate-200 hover:bg-slate-800"
                  >
                    Parte de situación
                  </a>
                </div>
              </Seccion>
              <Seccion titulo="Serie reconstruida en el servidor (DuckDB)">
                <Grafico historia={historiaVigente} />
              </Seccion>
              <Seccion titulo={`Consola de crisis · simulador de ${nodeId}`}>
                <Consola nodeId={nodeId} sim={simulador[nodeId]} />
              </Seccion>
            </>
          )}
          <Seccion titulo="Eventos">
            <ul className="space-y-1 text-xs">
              {estado.eventos.slice(0, 15).map((e) => (
                <li key={e.id} className="flex gap-2">
                  <span className="shrink-0 font-mono text-slate-500">{hora(e.ts)}</span>
                  <span className={`shrink-0 font-semibold ${e.nivel ? NIVELES[e.nivel].texto : "text-slate-300"}`}>
                    {e.tipo}
                    {e.nivel ? ` ${NIVELES[e.nivel].nombre}` : ""}
                  </span>
                  <span className="text-slate-400">
                    {e.node_id.split("-")[1]} · {e.detalle}
                  </span>
                </li>
              ))}
            </ul>
          </Seccion>
        </div>
      </main>
    </div>
  );
}
