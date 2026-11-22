import { create } from "zustand";

/** Estado de UI del Centro de Comando (spec UI/UX v2.0 §5). */
export const useUI = create((set) => ({
  modoSimulador: false,
  vista3D: false,
  panelIzquierdo: true,
  inspectorAbierto: true,
  cuencaSeleccionada: null,
  eventoResaltado: null,
  alternarSimulador: () => set((s) => ({ modoSimulador: !s.modoSimulador })),
  alternarVista: () => set((s) => ({ vista3D: !s.vista3D })),
  alternarPanelIzquierdo: () => set((s) => ({ panelIzquierdo: !s.panelIzquierdo })),
  cerrarInspector: () => set({ inspectorAbierto: false }),
  abrirInspector: () => set({ inspectorAbierto: true }),
  seleccionarCuenca: (id) => set({ cuencaSeleccionada: id, inspectorAbierto: true }),
  resaltarEvento: (ts) => set({ eventoResaltado: ts }),
}));
