/** Tokens semánticos alineados a la especificación UI/UX v2.0 §6.1 */
export const NIVELES = {
  GREEN: {
    nombre: "VERDE",
    orden: 0,
    color: "#10B981",
    texto: "text-emerald-400",
    fondo: "bg-emerald-500",
    forma: "●",
    fillOpacity: 0.12,
  },
  YELLOW: {
    nombre: "AMARILLO",
    orden: 1,
    color: "#F59E0B",
    texto: "text-amber-400",
    fondo: "bg-amber-500",
    forma: "▲",
    fillOpacity: 0.28,
  },
  ORANGE: {
    nombre: "NARANJA",
    orden: 2,
    color: "#F97316",
    texto: "text-orange-400",
    fondo: "bg-orange-500",
    forma: "◆",
    fillOpacity: 0.4,
  },
  RED: {
    nombre: "ROJO",
    orden: 3,
    color: "#EF4444",
    texto: "text-red-400",
    fondo: "bg-red-500",
    forma: "⬢",
    fillOpacity: 0.5,
  },
};

export const ESCENARIOS = [
  ["normal", "Sin lluvia"],
  ["llovizna", "Llovizna"],
  ["tormenta_moderada", "Tormenta moderada"],
  ["tormenta_convectiva", "Tormenta convectiva"],
  ["volcan_2017_cmorph", "Volcán 2017 (CMORPH · satélite)"],
];

export const hora = (iso) => (iso ? new Date(iso).toISOString().slice(11, 19) : "--:--:--");

export function cuenta(minutos) {
  if (minutos == null) return null;
  if (minutos <= 0) return "00:00";
  const s = Math.round(minutos * 60);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}

/** Estado de telemetría del nodo para el halo exterior del marcador IoT. */
export function estadoEnlace(nodo, origen) {
  if (!nodo) return "offline";
  if (nodo.en_linea) return "online";
  if (String(origen || "").toLowerCase().includes("emergencia") || String(origen || "").toLowerCase().includes("lora")) {
    return "lora";
  }
  const estado = nodo.ultima?.connectivity_state;
  if (estado === "ISLAND_MODE") return "lora";
  return "offline";
}
