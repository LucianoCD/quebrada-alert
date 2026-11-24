import { ArrowRight, Mountain, Radio, RadioTower, Signal, SignalZero, Siren } from "lucide-react";
import { Link } from "react-router-dom";
import { cuenta, emergenciaReciente, estadoEnlace, NIVELES } from "./niveles.js";
import { useEstado } from "./hooks.js";
import InterruptorTema from "./InterruptorTema.jsx";
import MapaCorredor from "./MapaCorredor.jsx";

const CUENCAS_LANDING = [
  ["CUENCA_ARROYO_MEDIO", "Volcán", "Arroyo del Medio"],
  ["CUENCA_TUMBAYA_GRANDE", "Tumbaya", "Río Tumbaya Grande"],
  ["CUENCA_PURMAMARCA", "Purmamarca", "Río Purmamarca"],
  ["CUENCA_HUASAMAYO", "Tilcara", "Río Huasamayo"],
];

const PASOS = [
  [
    Mountain,
    "Mide en la montaña",
    "Una estación en la cabecera de cada cuenca registra la lluvia y el nivel del arroyo, justo donde empieza la crecida.",
  ],
  [
    RadioTower,
    "Resiste sin señal celular",
    "Si se corta la red, la estación guarda cada lectura, decide la alerta por su cuenta y la envía por un enlace de radio de respaldo. Cuando vuelve la señal, completa lo que faltaba.",
  ],
  [
    Siren,
    "Avisa antes de la RN 9",
    "El monitor muestra qué cuenca está en alerta y un tiempo orientativo de llegada del agua a la ruta, para decidir con minutos de ventaja.",
  ],
];

const ENLACES = {
  online: [Signal, "Red celular", "text-agua"],
  lora: [Radio, "Respaldo por radio", "text-lora"],
  offline: [SignalZero, "Sin comunicación", "text-tinta-3"],
};

function Dato({ etiqueta, children }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-tinta-2">{etiqueta}</dt>
      <dd className="tabular text-right font-semibold text-tinta">{children}</dd>
    </div>
  );
}

export function TarjetaCuenca({ basinId, nombre, rio, cuenca, conectado }) {
  const nivel = cuenca ? NIVELES[cuenca.nivel] : null;
  const m = cuenca?.nodo.ultima?.metrics;
  const em = cuenca ? emergenciaReciente(cuenca.nodo) : null;
  const arribo = cuenca?.minutos_restantes != null ? cuenta(cuenca.minutos_restantes) : null;
  // El backend arranca cada cuenca en verde antes de la primera lectura: eso no es un estado medido.
  // Una alerta restaurada tras reiniciar el backend sí lo es, aunque todavía no haya lecturas nuevas.
  const sinLecturas = cuenca && !m && !em && cuenca.nivel === "GREEN";
  const [IconoEnlace, enlace, colorEnlace] = ENLACES[estadoEnlace(cuenca?.nodo, cuenca?.origen)];
  return (
    <Link
      to={`/monitor?cuenca=${basinId}`}
      className="panel-crisis group flex flex-col p-5 transition duration-200 hover:-translate-y-0.5 hover:border-borde-fuerte"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-base font-bold">{nombre}</h3>
          <div className="text-xs text-tinta-2">{rio}</div>
        </div>
        {nivel && !sinLecturas && (
          <span
            className="shrink-0 rounded-md px-2 py-0.5 text-[11px] font-bold text-sobre-nivel"
            style={{ background: nivel.color }}
          >
            {nivel.forma} {nivel.estado}
          </span>
        )}
      </div>

      {sinLecturas ? (
        <p className="mt-4 text-xs leading-relaxed text-tinta-2">
          Sin lecturas todavía: la estación aún no envió datos.
        </p>
      ) : cuenca ? (
        <>
          <div className="mt-4 min-h-[3.25rem]">
            {arribo ? (
              <>
                <div className="tabular text-2xl font-bold leading-none" style={{ color: nivel.tinta }}>
                  {arribo}
                </div>
                <div className="mt-1 text-xs text-tinta-2">para el arribo estimado a la RN 9</div>
              </>
            ) : (
              <>
                <div className="text-lg font-bold leading-tight" style={{ color: nivel.tinta }}>
                  {nivel.frase}
                </div>
                <div className="mt-1 text-xs text-tinta-2">Sin arribo previsto a la RN 9</div>
              </>
            )}
          </div>
          <dl className="mt-3 space-y-1.5 border-t border-borde pt-3 text-xs">
            <Dato etiqueta={em ? "Lluvia (por radio)" : "Lluvia en 15 min"}>
              {em ? `${em.rain_mm_15m} mm LoRa` : m ? `${m.rain_mm_15m} mm` : "—"}
            </Dato>
            <Dato etiqueta={em ? "Subida del río en 15 min" : "Nivel del río"}>
              {em ? `+${em.water_level_rise_15m_cm} cm` : m ? `${m.water_level_cm} cm` : "—"}
            </Dato>
            <Dato etiqueta="Comunicación">
              <span className={`inline-flex items-center gap-1 font-sans ${colorEnlace}`}>
                <IconoEnlace size={13} strokeWidth={2} aria-hidden="true" />
                {enlace}
              </span>
            </Dato>
          </dl>
        </>
      ) : conectado ? (
        <div className="mt-4 space-y-2" role="status" aria-label={`Cargando datos de ${nombre}`}>
          <div className="esqueleto h-6 w-2/3" />
          <div className="esqueleto h-3 w-full" />
          <div className="esqueleto h-3 w-5/6" />
          <div className="esqueleto h-3 w-3/4" />
        </div>
      ) : (
        <p className="mt-4 text-xs leading-relaxed text-tinta-2">
          Sin datos por ahora: el servidor de la demostración no está disponible.
        </p>
      )}

      <div className="mt-auto flex items-center gap-1 pt-4 text-xs font-semibold text-agua">
        Ver en el monitor
        <ArrowRight size={14} aria-hidden="true" className="transition-transform duration-200 group-hover:translate-x-0.5" />
      </div>
    </Link>
  );
}

/** Landing pública: qué es el sistema, cómo funciona y cómo están hoy las cuatro cuencas. */
export default function Landing() {
  const [estado, conectado] = useEstado();
  const porId = new Map(estado.cuencas.map((c) => [c.basin_id, c]));
  return (
    <div className="min-h-full bg-lienzo">
      <header className="mx-auto flex max-w-6xl items-center gap-3 px-6 py-4">
        <div className="text-sm font-bold tracking-tight">
          Quebrada<span className="text-agua">Alert</span>
        </div>
        <span className="rounded-md border border-amarillo/60 px-2 py-0.5 text-[11px] font-semibold text-amarillo">
          Demostración · datos simulados
        </span>
        <div className="ml-auto flex items-center gap-2">
          <Link
            to="/monitor"
            className="hidden rounded-lg px-3 py-1.5 text-xs font-semibold text-tinta-2 transition hover:bg-realce hover:text-tinta sm:block"
          >
            Monitor
          </Link>
          <InterruptorTema />
        </div>
      </header>

      {/* 1 · Hero con el mapa del corredor */}
      <section className="mx-auto grid max-w-6xl items-center gap-10 px-6 pb-20 pt-8 lg:grid-cols-[5fr_6fr] lg:gap-14 lg:pt-12">
        <div>
          <div className="mb-4 text-[11px] font-semibold uppercase tracking-[0.25em] text-ocre">
            Alerta temprana · Quebrada de Humahuaca · Jujuy
          </div>
          <h1 className="text-4xl font-bold leading-[1.1] tracking-tight md:text-5xl">
            Minutos de ventaja ante crecidas repentinas en la Quebrada.
          </h1>
          <p className="mt-5 max-w-md text-base leading-relaxed text-tinta-2">
            Cuatro cuencas que cruzan la Ruta Nacional 9, vigiladas desde la cabecera por estaciones que siguen
            avisando aunque se caiga la señal celular.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/monitor" className="boton-primario flex items-center gap-2 rounded-lg px-6 py-3 text-sm">
              Abrir el monitor
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
            <a
              href="#cuencas"
              className="rounded-lg border border-borde-fuerte px-6 py-3 text-sm font-semibold text-tinta-2 transition hover:bg-realce hover:text-tinta"
            >
              Ver las cuencas
            </a>
          </div>
          <div className="mt-6 flex items-center gap-2 text-xs text-tinta-2" role="status">
            <span
              className={`h-2 w-2 rounded-full ${conectado ? "bg-verde" : "border border-tinta-3"}`}
              aria-hidden="true"
            />
            {conectado ? "Recibiendo datos del servidor local" : "Servidor no disponible"}
          </div>
        </div>
        {/* Ilustración del corredor: relieve real con las cuatro cuencas, coloreadas por el estado en vivo */}
        <div className="mx-auto w-full max-w-[560px]">
          <MapaCorredor cuencas={estado.cuencas} />
        </div>
      </section>

      {/* 2 · Cómo funciona, en tres pasos */}
      <section className="border-y border-borde bg-hundida" aria-labelledby="como-funciona">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <h2 id="como-funciona" className="text-2xl font-bold tracking-tight">
            Cómo funciona
          </h2>
          <ol className="mt-10 grid gap-10 md:grid-cols-3 md:gap-8">
            {PASOS.map(([Icono, titulo, texto], i) => (
              <li key={titulo}>
                <div className="flex items-center gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-xl border border-borde bg-elevada text-ocre">
                    <Icono size={22} strokeWidth={1.75} aria-hidden="true" />
                  </span>
                  <span className="tabular text-xs font-bold text-tinta-3">PASO {i + 1}</span>
                </div>
                <h3 className="mt-4 text-lg font-bold">{titulo}</h3>
                <p className="mt-2 text-sm leading-relaxed text-tinta-2">{texto}</p>
              </li>
            ))}
          </ol>
          <p className="mt-10 max-w-3xl text-xs leading-relaxed text-tinta-3">
            En esta demostración las estaciones son simuladas y su ubicación es hipotética. El tiempo de llegada se
            estima con una fórmula para escurrimiento de agua (Kirpich); no es confiable para flujos de barro y piedras.
          </p>
        </div>
      </section>

      {/* 3 · Estado de las cuatro cuencas */}
      <section id="cuencas" className="mx-auto max-w-6xl px-6 py-16" aria-labelledby="titulo-cuencas">
        <h2 id="titulo-cuencas" className="text-2xl font-bold tracking-tight">
          Cómo están ahora las cuencas
        </h2>
        <p className="mt-2 text-sm text-tinta-2">Elegí una para abrirla en el monitor.</p>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {CUENCAS_LANDING.map(([basinId, nombre, rio]) => (
            <TarjetaCuenca
              key={basinId}
              basinId={basinId}
              nombre={nombre}
              rio={rio}
              cuenca={porId.get(basinId)}
              conectado={conectado}
            />
          ))}
        </div>
      </section>

      <footer className="border-t border-borde">
        <div className="mx-auto max-w-3xl px-6 py-10 text-center text-xs leading-relaxed text-tinta-2">
          QuebradaAlert es una herramienta de <b className="text-tinta">apoyo a la decisión</b> para Defensa Civil, la
          DPRH y Vialidad Nacional: cortar la ruta o evacuar lo decide siempre el organismo responsable. Los umbrales
          del semáforo no están calibrados y los datos de esta demostración son simulados.
        </div>
      </footer>
    </div>
  );
}
