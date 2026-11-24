import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AlertBanner, BasinList } from "../paneles.jsx";
import Landing from "../Landing.jsx";
import corredor from "../assets/corredor.js";
import MapaCorredor, {
  acotarVista,
  ampliar,
  avanceEnTramo,
  crecidaSimulada,
  DURACION_SIMULACION,
  encuadre,
} from "../MapaCorredor.jsx";
import ParteModal from "../ParteModal.jsx";
import Monitor from "../Monitor.jsx";
import { useUI } from "../store.js";

const { CUENCAS_DEMO, ESTADO_MOCK, FUENTES_MOCK, HISTORIA_MOCK, LECTURAS_FUENTES_MOCK, SIM_MOCK, SPARK_MOCK } =
  vi.hoisted(() => {
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
          timestamp_utc: "2026-11-23T17:45:00Z",
          connectivity_state: "ISLAND_MODE",
          metrics: { rain_mm_15m: 28, water_level_cm: 95, battery_soc_pct: 88 },
        },
        ultima_emergencia: {
          timestamp_utc: "2026-11-23T18:00:00Z",
          rain_mm_15m: 31.2,
          water_level_rise_15m_cm: 45,
          edge_local_alert: "RED",
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
    LECTURAS_FUENTES_MOCK: {
      lecturas: [
        {
          fuente: "snih",
          estacion_id: "280049",
          variable: "precipitacion_mm",
          ts: "2026-11-23T18:00:00+00:00",
          valor: 14.5,
          unidad: "mm",
          origen: "observado",
        },
      ],
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
    if (url.startsWith("/api/fuentes/lecturas")) return LECTURAS_FUENTES_MOCK;
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

  it("BasinList ordena tarjetas por severidad descendente y prioriza emergencia LoRa reciente", () => {
    render(<BasinList cuencas={CUENCAS_DEMO} seleccion="CUENCA_ARROYO_MEDIO" alElegir={vi.fn()} />);
    const botones = screen.getAllByRole("button");
    expect(botones[0]).toHaveTextContent("Volcán");
    expect(botones[0]).toHaveTextContent("31.2 mm LoRa");
    expect(botones[0]).toHaveTextContent("+45 cm");
    expect(botones[1]).toHaveTextContent("Purmamarca");
    expect(botones[2]).toHaveTextContent("Tumbaya");
  });

  it("Landing muestra la emergencia LoRa más reciente cuando supera la última telemetría", () => {
    render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>,
    );
    expect(screen.getByText("31.2 mm LoRa")).toBeInTheDocument();
    expect(screen.getByText("+45 cm")).toBeInTheDocument();
  });

  it("MapaCorredor enlaza las cuatro cuencas y muestra la cuenta regresiva solo donde hay arribo pendiente", () => {
    render(
      <MemoryRouter>
        <MapaCorredor cuencas={CUENCAS_DEMO} />
      </MemoryRouter>,
    );
    const enlaces = screen.getAllByRole("link");
    expect(enlaces.map((e) => e.getAttribute("href"))).toEqual([
      "/monitor?cuenca=CUENCA_ARROYO_MEDIO",
      "/monitor?cuenca=CUENCA_TUMBAYA_GRANDE",
      "/monitor?cuenca=CUENCA_PURMAMARCA",
      "/monitor?cuenca=CUENCA_HUASAMAYO",
    ]);
    expect(enlaces[0]).toHaveTextContent("arribo en 31:30");
    expect(enlaces[1]).toHaveTextContent("ETA ~79 min");
    expect(screen.getAllByText(/arribo en/)).toHaveLength(CUENCAS_DEMO.filter((c) => c.minutos_restantes != null).length);
  });

  it("MapaCorredor se dibuja sin estado vivo con los tiempos orientativos de Kirpich", () => {
    render(
      <MemoryRouter>
        <MapaCorredor cuencas={[]} />
      </MemoryRouter>,
    );
    expect(screen.getAllByText(/ETA ~\d+ min/)).toHaveLength(4);
    expect(screen.queryByText(/arribo en/)).not.toBeInTheDocument();
  });

  it("avanceEnTramo recorta el tramo estación-cruce según la fracción recorrida", () => {
    const tramo = [
      [0, 0],
      [10, 0],
      [10, 10],
    ];
    expect(avanceEnTramo(tramo, 0).punto).toEqual([0, 0]);
    expect(avanceEnTramo(tramo, 0.25).punto).toEqual([5, 0]);
    expect(avanceEnTramo(tramo, 0.75)).toEqual({ punto: [10, 5], trazo: "M0.0,0.0L10.0,0.0L10.0,5.0" });
    expect(avanceEnTramo(tramo, 7).punto).toEqual([10, 10]);
  });

  it("MapaCorredor sigue sola la crecida real más severa y no ofrece la simulación mientras dura", () => {
    render(
      <MemoryRouter>
        <MapaCorredor cuencas={CUENCAS_DEMO} />
      </MemoryRouter>,
    );
    expect(screen.getByRole("status")).toHaveTextContent("Siguiendo la crecida en Volcán");
    expect(screen.queryByRole("button", { name: /Simular crecida/ })).not.toBeInTheDocument();
    // Vista ya acercada: se puede alejar y, al hacerlo, volver al zoom automático.
    expect(screen.getByRole("button", { name: "Volver al zoom automático" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Alejar" }));
    expect(screen.getByRole("button", { name: "Volver al zoom automático" })).toBeEnabled();
  });

  it("MapaCorredor simula una crecida rotulada como ilustrativa y permite detenerla", () => {
    render(
      <MemoryRouter>
        <MapaCorredor cuencas={[]} />
      </MemoryRouter>,
    );
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Alejar" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: /Simular crecida/ }));
    expect(screen.getByRole("status")).toHaveTextContent("Simulación ilustrativa · no es un evento real");
    expect(screen.getByRole("button", { name: "Alejar" })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: /Detener/ }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("crecidaSimulada escala de nivel, hace bajar el frente hasta la RN 9 y termina sin lluvia", () => {
    expect(crecidaSimulada(0, 52)).toMatchObject({ nivel: "YELLOW", lluvia: 0, crecida: 0, fraccion: null, restantes: null });
    expect(crecidaSimulada(3, 52)).toMatchObject({ nivel: "ORANGE", lluvia: 1 });
    const medio = crecidaSimulada(7, 52);
    expect(medio.nivel).toBe("RED");
    expect(medio.restantes).toBeCloseTo(52 * (1 - medio.fraccion));
    expect(crecidaSimulada(DURACION_SIMULACION, 52)).toMatchObject({ nivel: "RED", lluvia: 0, fraccion: 1, restantes: 0 });
  });

  it("ampliar y acotarVista no dejan ver fuera del mapa ni pasar los límites de zoom", () => {
    const general = { k: 1, tx: 0, ty: 0 };
    expect(ampliar(general, 1 / 1.5)).toEqual(general);
    const cerca = ampliar(general, 2);
    expect(cerca).toEqual({ k: 2, tx: -600, ty: -668.5 });
    expect(acotarVista({ k: 2, tx: 500, ty: -5000 })).toEqual({ k: 2, tx: 0, ty: -1337 });
    expect(ampliar(ampliar(cerca, 2), 2).k).toBe(4);
    expect(ampliar(cerca, 0.5)).toEqual(general);
  });

  it("encuadre acerca la vista a cada cuenca dejando en cuadro la estación y el cruce con la RN 9", () => {
    for (const g of corredor.cuencas) {
      const { k, tx, ty } = encuadre(g);
      expect(k, g.localidad).toBeGreaterThanOrEqual(1.2);
      for (const [x, y] of [g.estacion, g.cruce]) {
        expect(x * k + tx, g.localidad).toBeGreaterThan(0);
        expect(x * k + tx, g.localidad).toBeLessThan(1200);
        expect(y * k + ty, g.localidad).toBeGreaterThan(0);
        expect(y * k + ty, g.localidad).toBeLessThan(1337);
      }
    }
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
    expect(screen.getByText(/14\.5 mm · 18:00:00 UTC/)).toBeInTheDocument();

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
