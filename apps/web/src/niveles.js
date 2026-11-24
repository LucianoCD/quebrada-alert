/**
 * Niveles del semáforo. `estado` y `frase` son el nombre y la lectura en lenguaje llano; `color` es el relleno (igual en ambos temas, con texto `text-sobre-nivel`);
 * `texto` y `tinta` son el color legible como texto, que cambia con el tema.
 */
export const NIVELES = {
  GREEN: {
    nombre: "VERDE",
    estado: "Normal",
    frase: "Sin señales de crecida",
    orden: 0,
    color: "#10B981",
    texto: "text-verde",
    tinta: "var(--verde)",
    fondo: "bg-emerald-500",
    forma: "●",
    fillOpacity: 0.12,
  },
  YELLOW: {
    nombre: "AMARILLO",
    estado: "Atención",
    frase: "Lluvia en aumento",
    orden: 1,
    color: "#F59E0B",
    texto: "text-amarillo",
    tinta: "var(--amarillo)",
    fondo: "bg-amber-500",
    forma: "▲",
    fillOpacity: 0.28,
  },
  ORANGE: {
    nombre: "NARANJA",
    estado: "Alerta",
    frase: "Posible crecida",
    orden: 2,
    color: "#F97316",
    texto: "text-naranja",
    tinta: "var(--naranja)",
    fondo: "bg-orange-500",
    forma: "◆",
    fillOpacity: 0.4,
  },
  RED: {
    nombre: "ROJO",
    estado: "Emergencia",
    frase: "Crecida probable",
    orden: 3,
    color: "#EF4444",
    texto: "text-rojo",
    tinta: "var(--rojo)",
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

// Jujuy no tiene horario de verano: siempre UTC-3. Se fija la zona para no depender de la del navegador.
const RELOJ_LOCAL = new Intl.DateTimeFormat("es-AR", {
  timeZone: "America/Argentina/Jujuy",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});

/** Hora local de Jujuy (UTC-3) de un instante ISO. */
export function hora(iso) {
  const t = Date.parse(iso);
  return Number.isFinite(t) ? RELOJ_LOCAL.format(t) : "--:--:--";
}

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

/** Devuelve `ultima_emergencia` cuando existe y es más reciente que `ultima`. */
export function emergenciaReciente(nodo) {
  const em = nodo?.ultima_emergencia;
  if (!em) return null;
  if (!nodo?.ultima?.timestamp_utc) return em;
  const tsEm = Date.parse(em.timestamp_utc);
  const tsUlt = Date.parse(nodo.ultima.timestamp_utc);
  return Number.isFinite(tsEm) && Number.isFinite(tsUlt) ? (tsEm >= tsUlt ? em : null) : em;
}
