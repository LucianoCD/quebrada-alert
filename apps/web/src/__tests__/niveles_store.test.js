import { describe, expect, it } from "vitest";
import { cuenta, ESCENARIOS, estadoEnlace, hora, NIVELES, registroLocal } from "../niveles.js";
import { useUI } from "../store.js";

describe("niveles.js", () => {
  it("ordena niveles de GREEN a RED e incluye escenario CMORPH 2017", () => {
    expect(NIVELES.GREEN.orden).toBe(0);
    expect(NIVELES.YELLOW.orden).toBe(1);
    expect(NIVELES.ORANGE.orden).toBe(2);
    expect(NIVELES.RED.orden).toBe(3);
    expect(ESCENARIOS.some(([clave]) => clave === "volcan_2017_cmorph")).toBe(true);
  });

  it("formatea cuenta regresiva correctamente", () => {
    expect(cuenta(null)).toBeNull();
    expect(cuenta(-1)).toBe("00:00");
    expect(cuenta(12.5)).toBe("12:30");
  });

  it("muestra la hora local de Jujuy (UTC-3), también al cruzar la medianoche", () => {
    expect(hora("2026-11-23T18:00:00Z")).toBe("15:00:00");
    expect(hora("2026-01-10T02:05:09+00:00")).toBe("23:05:09");
    expect(hora(null)).toBe("--:--:--");
    expect(hora("no es una fecha")).toBe("--:--:--");
    expect(registroLocal("04:10:16 Alerta autónoma ROJO")).toBe("01:10:16 Alerta autónoma ROJO");
    expect(registroLocal("02:05:09 Enlace restablecido")).toBe("23:05:09 Enlace restablecido");
    expect(registroLocal("Sin novedades.")).toBe("Sin novedades.");
  });

  it("distingue online, lora y offline en estadoEnlace", () => {
    expect(estadoEnlace(null, "")).toBe("offline");
    expect(estadoEnlace({ en_linea: true }, "telemetría en vivo")).toBe("online");
    expect(estadoEnlace({ en_linea: false }, "emergencia")).toBe("lora");
    expect(estadoEnlace({ en_linea: false, ultima: { connectivity_state: "ISLAND_MODE" } }, "")).toBe("lora");
    expect(estadoEnlace({ en_linea: false, ultima: { connectivity_state: "ONLINE" } }, "sin datos")).toBe("offline");
  });
});

describe("store.js (useUI)", () => {
  it("mantiene modoSimulador oculto por defecto y actualiza acciones de UI", () => {
    useUI.setState({
      modoSimulador: false,
      vista3D: false,
      panelIzquierdo: true,
      inspectorAbierto: true,
      cuencaSeleccionada: null,
      eventoResaltado: null,
    });
    expect(useUI.getState().modoSimulador).toBe(false);

    useUI.getState().alternarSimulador();
    expect(useUI.getState().modoSimulador).toBe(true);

    useUI.getState().alternarVista();
    expect(useUI.getState().vista3D).toBe(true);

    useUI.getState().cerrarInspector();
    expect(useUI.getState().inspectorAbierto).toBe(false);

    useUI.getState().seleccionarCuenca("CUENCA_ARROYO_MEDIO");
    expect(useUI.getState().cuencaSeleccionada).toBe("CUENCA_ARROYO_MEDIO");
    expect(useUI.getState().inspectorAbierto).toBe(true);

    useUI.getState().alternarPanelIzquierdo();
    expect(useUI.getState().panelIzquierdo).toBe(false);

    useUI.getState().resaltarEvento("2026-11-23T18:00:00Z");
    expect(useUI.getState().eventoResaltado).toBe("2026-11-23T18:00:00Z");
  });
});
