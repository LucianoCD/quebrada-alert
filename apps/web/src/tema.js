import { create } from "zustand";

const CLAVE = "quebrada-tema";

function guardado() {
  try {
    return localStorage.getItem(CLAVE) === "dia" ? "dia" : "noche";
  } catch {
    return "noche";
  }
}

function aplicar(tema) {
  if (tema === "dia") document.documentElement.dataset.tema = "dia";
  else delete document.documentElement.dataset.tema;
}

/** Tema de la interfaz: "noche" (por defecto) o "dia". La elección se recuerda en este navegador. */
export const useTema = create((set, get) => ({
  tema: guardado(),
  alternar: () => {
    const tema = get().tema === "dia" ? "noche" : "dia";
    aplicar(tema);
    try {
      localStorage.setItem(CLAVE, tema);
    } catch {
      /* almacenamiento no disponible: el tema vale solo para esta visita */
    }
    set({ tema });
  },
}));

aplicar(useTema.getState().tema);
