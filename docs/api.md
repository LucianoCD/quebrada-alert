# API y contratos

Referencia para trabajar en `apps/api` (backend) y `apps/web` (tablero) en
paralelo. La fuente de verdad es `apps/api/quebrada/schemas.py` y
`backend/app.py`; esta página es el mapa.

Base: `http://127.0.0.1:8000`. El tablero usa proxy de Vite para `/api`,
`/datos` y `/ws`.

## Ingesta (nodos → backend)

`POST /api/ingesta` — body: lista de `Mensaje` `{topic, payload}`.

| Tópico | Payload | Efecto |
|---|---|---|
| `spBv1.0/QUEBRADA/NBIRTH/<nodo>` | `Nacimiento` | Registra nodo, keepalive y escala de tiempo. |
| `spBv1.0/QUEBRADA/NDATA/<nodo>` | `Telemetria` | Guarda lectura `(node_id, seq)`; en vivo alimenta el semáforo (conservando episodios `NARANJA`/`ROJO` hasta `arribo_estimado + 5 min`); si es histórica, completa la serie y solo activa alerta si un pico `NARANJA`/`ROJO` recuperado tiene onda aún en tránsito (`ts + eta_min > ahora`). |

Respuesta: `{"nuevas": n, "repetidas": n}`. `422` si el tópico no cumple `spBv1.0/QUEBRADA/<NBIRTH|NDATA>/<nodo>`, `payload.node_id` difiere del tópico, el payload no valida o la cuenca es desconocida.

### `Nacimiento`

`node_id`, `basin_id`, `bd_seq`, `timestamp_utc` (con zona), `keepalive_s`,
`time_scale` (default 1.0).

### `Telemetria`

`node_id`, `basin_id`, `seq` (≥0), `timestamp_utc`, `is_historical` (default
false), `connectivity_state` (`ONLINE`|`ISLAND_MODE`), `metrics`, 
`edge_local_alert` (`GREEN`|`YELLOW`|`ORANGE`|`RED`, default `GREEN`).

### `Metricas`

`rain_mm_15m`, `rain_mm_60m`, `antecedent_rain_72h_mm`, `water_level_cm`,
`water_level_rise_15m_cm` (default 0), `turbidity_proxy_ntu`,
`battery_soc_pct` (0–100). Todos `ge=0` salvo `water_level_cm`.

## Respaldo (enlace secundario → backend)

`POST /api/respaldo` — body: lista de `Mensaje` con tópico `NDATA` cuyo payload es `Emergencia`.
El gateway LoRa solo reenvía paquetes de emergencia. Un nivel recibido así
**solo puede subir** el estado de la cuenca; la bajada espera telemetría en
vivo.

### `Emergencia`

`node_id`, `basin_id`, `seq`, `timestamp_utc`, `edge_local_alert` (`Nivel`),
`rain_mm_15m`, `water_level_rise_15m_cm`.

## Consulta (backend → tablero)

| Endpoint | Devuelve |
|---|---|
| `GET /api/estado` | `{"cuencas": [...], "eventos": [...]}` — una entrada por cuenca con `nivel`, `origen`, `accion`, `eta_min`, `tc_min`, `arribo_estimado`, `minutos_restantes` y `nodo` (`en_linea`, `ultima`, `hora_estimada`, `escala`, `recuperadas`, `huecos`). Más los últimos eventos. |
| `GET /api/historia/{node_id}?limite=2000` | Serie de lecturas `{seq, ts, is_historical, rain_mm_15m, rain_mm_60m, water_level_cm, turbidity_proxy_ntu, edge_local_alert}` ordenada por `seq` (`limite` validado `1..10000`, `422` si está fuera de rango). |
| `GET /api/parte/{basin_id}` | `text/plain` — parte de situación para organismos (lleva leyenda de demo). `404` si la cuenca no existe. |
| `GET /api/simulador` | Estado de los nodos simulados (solo demo; requiere `QUEBRADA_NODOS`). |
| `POST /api/simulador/{node_id}` | Reenvía `{orden}` al puerto de control del nodo simulado. |
| `GET /api/fuentes` | Catálogo de fuentes externas (SNIH, Open-Meteo forecast/archive), última sync y conteo de lecturas. |
| `POST /api/fuentes/sincronizar?fuente=` | Dispara una sync manual (`fuente` opcional: `snih` \| `open_meteo_forecast` \| `open_meteo_archive`). |
| `GET /api/fuentes/lecturas` | Lecturas persistidas (filtros `fuente`, `estacion_id`, `desde`, `hasta`, `limite`). |
| `GET /api/fuentes/{fuente}/lecturas` | Igual, acotado a una fuente. |
| `GET /api/fuentes/sincronizaciones` | Bitácora de sincronizaciones. |
| `WS /ws` | Push del mismo JSON de `/api/estado` cada ~1 s; no requiere mensajes del cliente (solo mantener abierta la conexión). |
| `GET /datos/*` | Archivos estáticos de `docs/data/` (GeoJSON + `relieve.png`). |
| `/` | Tablero compilado (`apps/web/dist`) si existe. |

### Fuentes externas (capa de referencia)

La API sincroniza periódicamente (y también a demanda) fuentes documentadas en
`docs/fuentes_datos_quebrada_alert.md`. Las lecturas viven en tablas DuckDB
`fuente_lectura` / `fuente_sincronizacion` y **no** se mezclan con la telemetría
de los nodos simulados ni disparan el semáforo. Las corridas de pronóstico
(`PRONOSTICO`) actualizan el valor ante conflicto de clave cuando cambia la
estimación horaria; el scheduler aplica backoff exponencial tras errores.

| Fuente | Qué guarda | Intervalo por defecto |
|---|---|---|
| `snih` | Lluvia horaria estaciones 280049 (Volcán) y 10040 (Humahuaca) | 3600 s |
| `open_meteo_forecast` | Precipitación horaria en las 4 cabeceras | 1800 s |
| `open_meteo_archive` | ERA5 reciente en las 4 cabeceras | 1800 s |

Variables de entorno: `QUEBRADA_FUENTES_AUTO` (`0` desactiva el scheduler),
`QUEBRADA_FUENTES_SNIH_INTERVAL_S`, `QUEBRADA_FUENTES_OPEN_METEO_INTERVAL_S`,
`QUEBRADA_FUENTES_SNIH_DIAS`, `QUEBRADA_FUENTES_ARCHIVE_DIAS`.

## Eventos del motor

`eventos` en `/api/estado` y en la tabla `eventos` de DuckDB:
`NBIRTH`, `NDATA` (no se listan), `EN_LINEA`, `NDEATH`, `ALERTA`, `DESCENSO`,
`RECUPERACION`. Campos: `id`, `ts`, `basin_id`, `node_id`, `tipo`, `nivel`,
`origen` (`nodo`|`servidor`), `detalle`.

## Reglas que el frontend debe respetar

- `is_historical: true` → la lectura completa la serie pero **no** cuenta como
  transmisión en vivo (se muestra distinto en el tablero).
- `minutos_restantes` puede ser `null` (cuenca en verde o sin arribo fijado).
- `nivel` usa los valores `GREEN|YELLOW|ORANGE|RED`; `origen` distingue
  telemetría en vivo de paquete de emergencia.
- El semáforo se define en `hydrology.clasificar` — si el tablero necesita
  anticipar color, replicar esa función, no inventar otra.
