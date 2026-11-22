import { Link } from "react-router-dom";
import { cuenta, NIVELES } from "./niveles.js";
import { useEstado } from "./hooks.js";
import EscenaCrecida from "./EscenaCrecida.jsx";

const CUENCAS_LANDING = [
  ["Volcán", "Arroyo del Medio"],
  ["Tumbaya", "Río Tumbaya Grande"],
  ["Purmamarca", "Río Purmamarca"],
  ["Tilcara", "Río Huasamayo"],
];

/** Landing pública (spec §4): portal de entrada. La escena 3D R3F queda para Fase 3. */
export default function Landing() {
  const [estado, conectado] = useEstado();
  const porId = new Map(estado.cuencas.map((c) => [c.localidad?.toUpperCase(), c]));
  return (
    <div className="min-h-full overflow-y-auto bg-[#eef2f7]">
      {/* Hero */}
      <section className="mx-auto flex min-h-[70vh] max-w-6xl flex-col justify-center gap-8 px-6 py-16 lg:flex-row lg:items-center">
        <div className="lg:w-[42%]">
          <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.25em] text-cyan-700">
            SAT · Quebrada de Humahuaca · Jujuy
          </div>
          <h1 className="text-4xl font-bold leading-tight md:text-5xl">
            Minutos de ventaja ante crecidas repentinas en la Quebrada.
          </h1>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-slate-600">
            Monitoreo de cuatro microcuencas críticas sobre la RN 9: estaciones en cabecera que siguen alertando
            aunque caiga el enlace celular, con reconstrucción completa de la serie al volver la conexión.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              to="/monitor"
              className="rounded-lg bg-cyan-500 px-6 py-3 text-sm font-bold text-slate-950 transition hover:bg-cyan-400"
            >
              Abrir Centro de Monitoreo
            </Link>
            <a
              href="#cuencas"
              className="rounded-lg border border-slate-300 px-6 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-200"
            >
              Explorar las cuencas
            </a>
          </div>
          <div className="mt-6 text-[11px] text-slate-600">
            {conectado ? "● datos en vivo del servidor local" : "○ servidor no disponible"} · demostración con datos simulados
          </div>
        </div>
        {/* Escena animada de crecida (canvas 2D; la versión 3D R3F es Fase 3 del spec) */}
        <div className="relative h-[380px] flex-1 overflow-hidden rounded-2xl border border-slate-300 bg-[#0a1424] shadow-[0_0_80px_rgba(14,165,233,0.12)] lg:h-[480px]">
          <EscenaCrecida />
          <div className="absolute bottom-3 left-3 rounded-md border border-slate-300/70 bg-slate-100 px-2.5 py-1.5 text-[10px] text-slate-600 backdrop-blur-sm">
            Crecida convectiva simulada · sección transversal del cauce
          </div>
        </div>
      </section>

      {/* Monitor vivo de las 4 cuencas (spec §4.2 Sección 3) */}
      <section id="cuencas" className="mx-auto max-w-6xl px-6 pb-16">
        <h2 className="mb-6 text-xl font-bold">Estado actual de las cuencas</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CUENCAS_LANDING.map(([nombre, rio]) => {
            const c = porId.get(nombre.toUpperCase());
            const nivel = c ? NIVELES[c.nivel] : null;
            const m = c?.nodo.ultima?.metrics;
            return (
              <Link
                key={nombre}
                to={`/monitor?cuenca=${c?.basin_id ?? ""}`}
                className="panel-crisis block p-4 transition hover:ring-1 hover:ring-cyan-400/50"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-bold">{nombre}</div>
                    <div className="text-[11px] text-slate-600">{rio}</div>
                  </div>
                  {nivel && (
                    <span
                      className="rounded px-1.5 py-0.5 text-[10px] font-bold text-slate-950"
                      style={{ background: nivel.color }}
                    >
                      {nivel.forma} {nivel.nombre}
                    </span>
                  )}
                </div>
                <div className="tabular mt-3 space-y-1 text-[11px] text-slate-600">
                  <div className="flex justify-between">
                    <span>ETA RN 9</span>
                    <span className="font-bold" style={{ color: nivel?.color }}>
                      {c?.minutos_restantes != null ? cuenta(c.minutos_restantes) : "—"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Nivel</span>
                    <span>{m ? `${m.water_level_cm} cm` : "—"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Lluvia 15 min</span>
                    <span>{m ? `${m.rain_mm_15m} mm` : "—"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Enlace</span>
                    <span style={{ color: c?.nodo.en_linea ? "#0891b2" : "#d97706" }}>
                      {c?.nodo.en_linea ? "celular" : "respaldo"}
                    </span>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      </section>

      {/* Marco institucional (spec §4.2 Sección 4) */}
      <section className="border-t border-slate-200 bg-[#f8fafc] py-12">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h2 className="text-lg font-bold">Coordinación institucional</h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-600">
            QuebradaAlert es una herramienta de <b className="text-slate-800">soporte a la decisión</b> para Defensa
            Civil, la DPRH y Vialidad Nacional. Las recomendaciones de corte o evacuación son siempre del organismo
            responsable. Los umbrales del semáforo están en fase de calibración y los datos de esta demostración son
            simulados.
          </p>
        </div>
      </section>
    </div>
  );
}
