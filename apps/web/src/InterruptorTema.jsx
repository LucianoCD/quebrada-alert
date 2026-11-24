import { Moon, Sun } from "lucide-react";
import { useTema } from "./tema.js";

/** Interruptor Día / Noche. */
export default function InterruptorTema({ className = "" }) {
  const { tema, alternar } = useTema();
  const dia = tema === "dia";
  const Icono = dia ? Moon : Sun;
  return (
    <button
      type="button"
      role="switch"
      aria-checked={dia}
      aria-label="Tema de día"
      title={dia ? "Cambiar a tema de noche" : "Cambiar a tema de día"}
      onClick={alternar}
      className={`flex h-8 w-8 items-center justify-center rounded-lg border border-borde-fuerte text-tinta-2 transition hover:bg-realce hover:text-tinta ${className}`}
    >
      <Icono size={16} strokeWidth={1.75} aria-hidden="true" />
    </button>
  );
}
