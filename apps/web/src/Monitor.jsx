import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import MapaTactico from "./MapaTactico.jsx";
import ParteModal from "./ParteModal.jsx";
import { AlertBanner, BasinList, ConsolaSimulador, Inspector, TopBar } from "./paneles.jsx";
import { useEstado, useSondeo } from "./hooks.js";
import { useUI } from "./store.js";

/** Centro de Comando `/monitor` — layout Tactical Map-First (spec §5). */
export default function Monitor() {
  const [estado, conectado] = useEstado();
  const [params] = useSearchParams();
  const {
    modoSimulador,
    vista3D,
    cuencaSeleccionada,
    seleccionarCuenca,
    inspectorAbierto,
    abrirInspector,
    panelIzquierdo,
  } = useUI();
  const [parte, setParte] = useState(null);
  const [simulador, setSimulador] = useState({});

  // Deep-link ?cuenca=ID (spec §3)
  useEffect(() => {
    const id = params.get("cuenca");
    if (id && estado.cuencas.some((c) => c.basin_id === id)) seleccionarCuenca(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params, estado.cuencas.length]);

  // Selector por defecto: la de mayor severidad
  const peor = estado.cuencas.reduce(
    (a, b) => (b.nivel !== "GREEN" && (!a || a.nivel === "GREEN") ? b : a),
    null,
  );
  const seleccionada =
    estado.cuencas.find((c) => c.basin_id === cuencaSeleccionada) ??
    estado.cuencas.find((c) => c.basin_id === peor?.basin_id) ??
    estado.cuencas[0];

  // Estado de los nodos edge: siempre disponible (alimenta la pestaña "Nodo y Red").
  const sondeoSim = useSondeo("/api/simulador", 2000, {});
  useEffect(() => setSimulador(sondeoSim ?? {}), [sondeoSim]);

  // Atajos de teclado (spec §6.3)
  useEffect(() => {
    const teclas = {
      1: "CUENCA_ARROYO_MEDIO",
      2: "CUENCA_TUMBAYA_GRANDE",
      3: "CUENCA_PURMAMARCA",
      4: "CUENCA_HUASAMAYO",
    };
    const alTecla = (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "SELECT") return;
      if (teclas[e.key] && estado.cuencas.some((c) => c.basin_id === teclas[e.key])) {
        seleccionarCuenca(teclas[e.key]);
      } else if (e.key === "m" || e.key === "M") {
        useUI.getState().alternarVista();
      } else if (e.key === "s" || e.key === "S") {
        useUI.getState().alternarSimulador();
      } else if (e.key === "Escape") {
        useUI.getState().cerrarInspector();
      }
    };
    window.addEventListener("keydown", alTecla);
    return () => window.removeEventListener("keydown", alTecla);
  }, [estado.cuencas, seleccionarCuenca]);

  return (
    <div className={`relative h-full w-full overflow-hidden ${modoSimulador ? "modo-simulador" : ""}`}>
      <MapaTactico
        cuencas={estado.cuencas}
        seleccion={seleccionada?.basin_id}
        vista3D={vista3D}
        alSeleccionar={seleccionarCuenca}
      />
      <TopBar conectado={conectado} />
      <AlertBanner cuencas={estado.cuencas} alVerParte={setParte} />
      {panelIzquierdo && (
        <BasinList cuencas={estado.cuencas} seleccion={seleccionada?.basin_id} alElegir={seleccionarCuenca} />
      )}
      {inspectorAbierto && seleccionada && (
        <Inspector cuenca={seleccionada} eventos={estado.eventos} simulador={simulador} alVerParte={setParte} />
      )}
      {!inspectorAbierto && seleccionada && (
        <button
          type="button"
          onClick={abrirInspector}
          className="panel-crisis absolute bottom-3 right-3 z-10 rounded px-3 py-1.5 text-xs text-slate-700 hover:text-white"
        >
          Inspector ⟩
        </button>
      )}
      {/* Drawer inferior: Consola de crisis (solo MODO SIMULADOR) */}
      {modoSimulador && (
        <div className="panel-crisis absolute inset-x-3 bottom-3 z-10 max-h-[38vh] overflow-y-auto p-3">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wide text-amber-700">
              Consola de crisis / simulador
            </span>
            <span className="text-[10px] text-slate-600">Entorno de demostración — no representa datos reales</span>
          </div>
          <ConsolaSimulador simulador={simulador} />
        </div>
      )}
      {parte && (
        <ParteModal
          basinId={parte}
          cuenca={estado.cuencas.find((c) => c.basin_id === parte)}
          onCerrar={() => setParte(null)}
        />
      )}
    </div>
  );
}
