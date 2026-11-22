---
tags: [sistema, arquitectura]
actualizado: 2026-11-22
---

# Arquitectura

Cuatro microcuencas reales (Volcán, Tumbaya, Purmamarca, Tilcara) con una
estación de cabecera simulada cada una. Ver [[proyecto]].

## Flujo de datos

```
estación simulada (edge)                centro de comando              tablero
┌─────────────────────┐   NDATA/NBIRTH  ┌──────────────────┐   WS/REST  ┌──────────┐
│ SQLite WAL + seq    │ ──────────────► │ FastAPI + DuckDB │ ─────────► │ React/Vite│
│ semáforo local      │   /api/ingesta  │ motor de alertas │  /api/*   │ Leaflet  │
│ cola de reenvío     │                 │ reconciliación   │  /datos/* │ offline  │
│ baliza + registro   │                 └──────────────────┘           └──────────┘
└─────────┬───────────┘
          │ EMERGENCIA (paquete corto)
          ▼
   enlace de respaldo (emula LoRa) ──► /api/respaldo
```

## Componentes (`apps/api/quebrada/`)

- `schemas.py` — contratos Pydantic: telemetría, NBIRTH y paquete de emergencia.
- `hydrology.py` — semáforo y [[decisiones#kirpich|Kirpich]] como funciones puras.
- `cuencas.py` — atributos morfométricos leídos de `docs/data/cuencas.geojson`.
- `edge/` — nodo simulado: proceso FastAPI de control + lógica en `nodo.py`.
- `backend/` — `app.py` (API, WebSocket, estáticos) + `motor.py` (estado, eventos,
  DuckDB, cuenta regresiva).
- `demo.py` — orquesta backend + un proceso por nodo.

## Persistencia

- **Nodo**: SQLite en modo WAL, tabla `lecturas` con `seq` y flag `enviado`.
  La escritura local ocurre **antes** de transmitir.
- **Backend**: DuckDB con clave `(node_id, seq)` — un reenvío no duplica.
  `Motor` guarda en DuckDB el estado de alertas para sobrevivir reinicios.

## Protocolo

Tópicos y ciclo de vida de **Sparkplug B** (`spBv1.0/QUEBRADA/NBIRTH|NDATA/<nodo>`)
sobre HTTP+JSON. No hay broker MQTT ni protobuf. El respaldo usa `/api/respaldo`
con paquetes `EMERGENCIA` — solo pueden subir el nivel, nunca bajarlo.

## Tablero (`apps/web`)

React 19 + Vite + Tailwind 4 + Leaflet. Pide `/api/estado`, `/api/historia/*`,
`/ws` (resumen cada segundo) y `/datos/*` (GeoJSON + relieve PNG generados por
`apps/api/scripts/preparar_geodatos.py`). Compila una vez; después funciona sin red.

## Datos (`docs/data/`)

`cuencas.geojson`, `cauces.geojson`, `puntos.geojson`, `contexto.geojson`,
`relieve.png`. Generados una vez desde Copernicus GLO-30 + OpenStreetMap —
ver [[decisiones#fuentes-geo]].
