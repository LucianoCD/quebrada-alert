import { useEffect, useState } from "react";

const json = (url, opciones) => fetch(url, opciones).then((r) => (r.ok ? r.json() : Promise.reject(r)));

/** Estado global por WebSocket /ws con reconexión (spec §7.1). */
export function useEstado() {
  const [estado, setEstado] = useState({ cuencas: [], eventos: [] });
  const [conectado, setConectado] = useState(false);
  useEffect(() => {
    let ws;
    let reintento;
    let vigente = true;
    const abrir = () => {
      ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`);
      ws.onopen = () => setConectado(true);
      ws.onmessage = (m) => setEstado(JSON.parse(m.data));
      ws.onclose = () => {
        setConectado(false);
        if (vigente) reintento = setTimeout(abrir, 1000);
      };
    };
    abrir();
    return () => {
      vigente = false;
      clearTimeout(reintento);
      ws.close();
    };
  }, []);
  return [estado, conectado];
}

/** Polling simple para endpoints REST. */
export function useSondeo(url, ms, inicial) {
  const [dato, setDato] = useState(inicial);
  useEffect(() => {
    if (!url) return undefined;
    let vigente = true;
    const pedir = () =>
      json(url)
        .then((d) => vigente && setDato(d))
        .catch(() => {});
    pedir();
    const reloj = setInterval(pedir, ms);
    return () => {
      vigente = false;
      clearInterval(reloj);
    };
  }, [url, ms]);
  return dato;
}

/** Micro-serie de nivel para el sparkline de cada tarjeta de cuenca. */
export function useSparkline(nodeId) {
  const [puntos, setPuntos] = useState([]);
  useEffect(() => {
    if (!nodeId) return undefined;
    let vigente = true;
    const pedir = () =>
      json(`/api/historia/${nodeId}?limite=48`)
        .then((d) => vigente && setPuntos(d.slice(-24).map((h) => h.water_level_cm)))
        .catch(() => {});
    pedir();
    const reloj = setInterval(pedir, 4000);
    return () => {
      vigente = false;
      clearInterval(reloj);
    };
  }, [nodeId]);
  return puntos;
}

export { json };
