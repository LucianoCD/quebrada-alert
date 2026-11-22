export const NIVELES = {
  GREEN: { nombre: "VERDE", color: "#22c55e", texto: "text-green-400", fondo: "bg-green-500" },
  YELLOW: { nombre: "AMARILLO", color: "#eab308", texto: "text-yellow-300", fondo: "bg-yellow-400" },
  ORANGE: { nombre: "NARANJA", color: "#f97316", texto: "text-orange-400", fondo: "bg-orange-500" },
  RED: { nombre: "ROJO", color: "#ef4444", texto: "text-red-400", fondo: "bg-red-500" },
};

export const ESCENARIOS = [
  ["normal", "Sin lluvia"],
  ["llovizna", "Llovizna"],
  ["tormenta_moderada", "Tormenta moderada"],
  ["tormenta_convectiva", "Tormenta convectiva"],
];

export const hora = (iso) => (iso ? new Date(iso).toISOString().slice(11, 19) : "--:--:--");

export function cuenta(minutos) {
  if (minutos == null) return null;
  if (minutos <= 0) return "00:00";
  const s = Math.round(minutos * 60);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
}
