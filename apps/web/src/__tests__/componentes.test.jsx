import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AlertBanner, BasinList } from "../paneles.jsx";
import ParteModal from "../ParteModal.jsx";
import Monitor from "../Monitor.jsx";
import { useUI } from "../store.js";

const { CUENCAS_DEMO, ESTADO_MOCK, FUENTES_MOCK, HISTORIA_MOCK, SIM_MOCK, SPARK_MOCK } = vi.hoisted(() => {
  const cuencas = [
    {
      basin_id: "CUENCA_TUMBAYA_GRANDE",
      localidad: "Tumbaya",
      curso: "Río Tumbaya Grande",
      nivel: "YELLOW",
      origen: "telemetría en vivo",
      accion: "Avisar a la guardia técnica.",
      eta_min: 79,
      minutos_restantes: null,
      nodo: {
        node_id: "EST-TUMBAYA-CAB01",
        en_linea: true,
        huecos: 0,
        ultima: { metrics: { rain_mm_15m: 2, water_level_cm: 25, battery_soc_pct: 90 } },
      },
    },
    {
      basin_id: "CUENCA_ARROYO_MEDIO",
      localidad: "Volcán",
      curso: "Arroyo del Medio",
      nivel: "RED",
      origen: "emergencia",
      accion: "Recomendar el corte preventivo de la RN 9.",
      eta_min: 52,
      minutos_restantes: 31.5,
      nodo: {
        node_id: "EST-VOLCAN-CAB01",
        en_linea: false,
        huecos: 4,
        ultima: {
          connectivity_state: "ISLAND_MODE",
          metrics: { rain_mm_15m: 28, water_level_cm: 95, battery_soc_pct: 88 },
        },
      },
    },
    {
      basin_id: "CUENCA_PURMAMARCA",
      localidad: "Purmamarca",
      curso: "Río Purmamarca",
      nivel: "ORANGE",
      origen: "telemetría en vivo",
      accion: "Pre-alerta a Defensa Civil.",
      eta_min: 119,
      minutos_restantes: 90,
      nodo: {
        node_id: "EST-PURMAMARCA-CAB01",
        en_linea: true,
        huecos: 0,
        ultima: { metrics: { rain_mm_15m: 16, water_level_cm: 60, battery_soc_pct: 91 } },
      },
    },
  ];
  return {
    CUENCAS_DEMO: cuencas,
    ESTADO_MOCK: [{ cuencas, eventos: [] }, true],
    FUENTES_MOCK: {
      lecturas_totales: 375,
      fuentes: [{ id: "snih", nombre: "SNIH — lluvia observada", ultima: { estado: "ok", nuevas: 12 } }],
    },
    SIM_MOCK: {},
    HISTORIA_MOCK: [],
    SPARK_MOCK: [20, 30, 50],
  };
});

vi.mock("../MapaTactico.jsx", () => ({
  default: ({ seleccion }) => <div data-testid="mapa-tactico-mock" data-seleccion={seleccion} />,
}));

vi.mock("../hooks.js", () => ({
  json: vi.fn(),
  useEstado: () => ESTADO_MOCK,
  useSondeo: (url) => {
    if (url === "/api/fuentes") return FUENTES_MOCK;
    if (url === "/api/simulador") return SIM_MOCK;
    return HISTORIA_MOCK;
  },
  useSparkline: () => SPARK_MOCK,
}));

describe("Componentes tácticos UI v2", () => {
  beforeEach(() => {
    useUI.setState({
      modoSimulador: false,
      vista3D: false,
      panelIzquierdo: true,
      inspectorAbierto: true,
      cuencaSeleccionada: null,
      eventoResaltado: null,
    });
    vi.restoreAllMocks();
  });

  it("AlertBanner prioriza la alerta RED sobre ORANGE", () => {
    const alVerParte = vi.fn();
    render(<AlertBanner cuencas={CUENCAS_DEMO} alVerParte={alVerParte} />);
    expect(screen.getByRole("alert")).toHaveTextContent("ALERTA ROJO: VOLCÁN");
    fireEvent.click(screen.getByRole("button", { name: "Parte" }));
    expect(alVerParte).toHaveBeenCalledWith("CUENCA_ARROYO_MEDIO");
  });

  it("BasinList ordena tarjetas por severidad descendente", () => {
    render(<BasinList cuencas={CUENCAS_DEMO} seleccion="CUENCA_ARROYO_MEDIO" alElegir={vi.fn()} />);
    const botones = screen.getAllByRole("button");
    expect(botones[0]).toHaveTextContent("Volcán");
    expect(botones[1]).toHaveTextContent("Purmamarca");
    expect(botones[2]).toHaveTextContent("Tumbaya");
  });

  it("ParteModal expone role=dialog, carga texto y cierra con Escape", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, text: async () => "PARTE DE SITUACIÓN DE PRUEBA" });
    const onCerrar = vi.fn();
    render(<ParteModal basinId="CUENCA_ARROYO_MEDIO" cuenca={CUENCAS_DEMO[1]} onCerrar={onCerrar} />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("PARTE DE SITUACIÓN DE PRUEBA")).toBeInTheDocument());

    fireEvent.keyDown(window, { key: "Escape" });
    expect(onCerrar).toHaveBeenCalledTimes(1);
  });

  it("Monitor selecciona la cuenca más severa (RED), oculta simulador por defecto y Escape sobre ParteModal no cierra Inspector", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({ ok: true, text: async () => "PARTE VIVO" });
    render(
      <MemoryRouter initialEntries={["/monitor"]}>
        <Monitor />
      </MemoryRouter>,
    );

    expect(screen.getByTestId("mapa-tactico-mock")).toHaveAttribute("data-seleccion", "CUENCA_ARROYO_MEDIO");
    expect(screen.queryByText(/Consola de crisis \/ simulador/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Fuentes externas \(referencia\)/i)).toBeInTheDocument();

    // Abre ParteModal y pulsa Escape: debe cerrar el modal pero conservar abierto el Inspector.
    fireEvent.click(screen.getByRole("button", { name: "Parte" }));
    await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(useUI.getState().inspectorAbierto).toBe(true);

    // Un segundo Escape sin modal abierto sí cierra el Inspector.
    fireEvent.keyDown(window, { key: "Escape" });
    expect(useUI.getState().inspectorAbierto).toBe(false);

    // Tecla S activa el drawer del simulador.
    fireEvent.keyDown(window, { key: "s" });
    expect(screen.getByText(/Consola de crisis \/ simulador/i)).toBeInTheDocument();
  });
});
