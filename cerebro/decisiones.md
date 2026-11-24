---
tags: [decisiones, adr]
actualizado: 2026-11-23
---

# Decisiones técnicas

ADRs ligeros: qué se decidió y por qué. Si una decisión cambia, se edita la
nota y se enlaza desde [[estado]].

## Sparkplug B sobre HTTP+JSON

Se usan los tópicos y el ciclo de vida de Sparkplug B
(`spBv1.0/QUEBRADA/NBIRTH|NDATA/<nodo>`) pero **sin broker MQTT ni protobuf**:
HTTP+JSON directo a `/api/ingesta` y `/api/respaldo`. Motivo: la demo debe
correr en una máquina sin infraestructura; el valor está en el *contrato* de
tópicos, no en el transporte. Ver [[arquitectura#protocolo]].

## SQLite WAL en el borde

Cada nodo escribe cada lectura en SQLite (modo WAL) con `seq` **antes** de
transmitir. WAL permite lectura concurrente con escritura y el búfer sobrevive
reinicios — ver `test_la_cola_sobrevive_a_un_reinicio`. Alternativa descartada:
archivo plano/JSONL, sin atomicidad ni consulta.

## DuckDB en el centro

`Motor` persiste telemetría y estado en DuckDB con clave `(node_id, seq)`:
idempotencia de reenvíos y estado de alertas que sobrevive reinicios del
backend (`test_reinicio_del_backend_conserva_la_alerta`).

## Kirpich para el tiempo de arribo

$t_c = 0{,}0195\,L^{0{,}77}\,S^{-0{,}385}$ aplicado al tramo estación→RN 9.
Es la [[limitaciones#kirpich|limitación conocida]]: Kirpich describe
escurrimiento de agua en cuencas agrícolas, no flujos de detritos — los
valores (50–120 min) son mayores que los 20–45 min citados para estos eventos.

## Fuentes geográficas {#fuentes-geo}

Copernicus GLO-30 (no SRTM como pedía la especificación original) porque se
descarga sin registro; OSM para RN 9, cursos y localidades. pysheds para
D8/acuencación. Detalle y tabla de cuencas en `README.md` § Geografía.

## Telemetría extendida

El contrato original no incluía `water_level_rise_15m_cm`, pero el semáforo lo
necesita para detectar ascenso rápido del cauce → se agregó al schema
`Metricas`. Cambio aditivo, compatible.

## Enlace de respaldo = segundo canal HTTP

El "LoRa" se emula como `POST /api/respaldo`. Decisión consciente para la demo;
el alcance real en quebradas queda como [[roadmap#si-hay-tiempo|pendiente]].

## Fuentes de datos (relevamiento 22/11/2026)

Ver [[fuentes-datos]] para el detalle y `docs/` para los relevamientos.

- **El satélite no gatilla**: con tc de 18–54 min en subcuencas, ningún producto
  de observación (latencia 2–18 h) sirve para disparar evacuación. Los satélites
  calibran y anticipan; la alerta táctica depende del nodo local y del pronóstico
  numérico.
- **WRF-DET 4 km como motor anticipatorio** si se integra producción
  (`s3://smn-ar-wrf`, PP 10M/1H, SMOIS, Freezing_level).
- **Nivel, turbidez, batería y fallas siguen simulados**: no existe medición
  pública de esas variables en tributarios.
- **Umbrales pendientes de calibración local**: se parte de curvas de
  referencia (Guzzetti 2008, Caine 1980) y análogos semiáridos, con regla
  condicionada por humedad del suelo e isoterma 0 °C.
- **Copernicus GLO-30 + OSM confirmados** como base estática; FI-UGICH/UNJu–DPRH
  (1:50.000) es la alternativa oficial a nuestra delimitación automática.
- **Mapa offline con estáticos propios** (`docs/data/`); PMTiles queda como
  escalado futuro.
- **Licencias**: FABDEM y Open-Meteo gratis son solo no comerciales.

## Modelo de negocio (propuesto 22/11/2026)

Ver [[modelo-negocio]] y `docs/modelo-negocio-quebrada-alert.md`.

- **B2G "alerta como servicio" con núcleo abierto**: cobro por cuenca/año de
  operación y mantenimiento, no por hardware ni licencia.
- **Ingreso recurrente como contrato de mantenimiento**, no suscripción SaaS —
  encaja con el procurement público argentino.
- **Posicionamiento complementario a la DPRH**: el piloto alimenta su cadena
  de alerta en vez de competir con ella.
- **Todo lo comercial es hipótesis sin validar**; riesgo abierto = un solo
  comprador institucional. Pendientes: LICENSE, licencias de datos, auth en
  ingesta, BOM de estación, figura jurídica, ancla de precios por licitaciones.

## Tablero táctico UI/UX v2.0

- **MapLibre GL + Deck.gl offline**: reemplaza a Leaflet para soportar
  animaciones de escorrentía (`TripsLayer`) y transición progresiva hacia vista
  3D sin depender de CDNs externos (`setWorkerUrl(workerUrl)`).
- **`HashRouter` para despliegue estático**: el backend FastAPI sirve
  `apps/web/dist` en `/` sin reglas de rewrite SPA, por lo que las rutas
  usan hash (`/#/monitor`).
- **Gráfica SVG propia en el Inspector**: evita el peso de bundle de ECharts y
  marca cambios de alerta exclusivamente por transición de `edge_local_alert`,
  sin inventar bandas fijas en `cm` absolutos.
- **Aislamiento de `ConsolaSimulador`**: los controles de falla e inyección de
  tormentas viven ocultos tras `modoSimulador === true` (tecla `S`) para
  separar operación y demostración.
- **Tema claro (`#eef2f7`) en Fases 1–2**: prioriza legibilidad sobre relieve
  cartográfico claro; el *Dark Mode* y la escena R3F permanecen evaluables en
  Fases 3–4.
- **Contratos estrictos y Terrain-RGB offline (2026-11-23)**: `Mensaje.topic`
  valida `spBv1.0/QUEBRADA/<NBIRTH|NDATA>/<node_id>` y coincidencia con
  `payload.node_id` (`422`); `preparar_geodatos.py` incorpora codificación
  Mapbox Terrain-RGB para preparar teselas 3D locales sin alterar los activos
  GeoJSON actuales, y `escenarios.py` incorpora `volcan_2017_cmorph` rotulado
  como estimación satelital histórica.
- **Episodios, recuperación activa y persistencia operativa (2026-11-23)**:
  - `Motor._nivel()` retiene episodios `NARANJA`/`ROJO` hasta
    `arribo_estimado + 5 min` aunque cese la lluvia antes de que la onda llegue
    a la RN 9 (hallazgo A1).
  - `Motor._recuperacion()` abre o eleva alerta (`solo_subir=True`) si una
    lectura histórica recuperada alcanzó `NARANJA`/`ROJO` y `ts + eta_min > ahora`
    (hallazgo A2), manteniendo inocuas tormentas viejas ya arribadas.
  - DuckDB agrega `nodos_meta` para preservar `keepalive_s`, `escala` y
    `en_linea` ante reinicios rápidos del backend (hallazgo M3).
  - `FuentesRepository.guardar_lecturas` actualiza registros `PRONOSTICO` en
    conflicto cuando cambia el valor (hallazgo M4) y `FuentesScheduler` aplica
    backoff exponencial (`30 s` → intervalo configurado) ante fallos.
  - El tablero divide chunks de `maplibre-gl` y `@deck.gl` en `vite.config.js`,
    muestra `/api/fuentes` como capa de referencia en el Inspector y está
    cubierto por Vitest (`apps/web`) y `tests/test_e2e_tablero.py` en CI.
- **Endurecimiento operativo e integridad UI/CI (2026-11-23, N1–N7 y UI M1/M5)**:
  - **Lockfile multiplataforma (`N1`)**: `apps/web/package-lock.json` conserva las
    dependencias opcionales `@emnapi/core` y `@emnapi/runtime` (`2.0.0-beta.2`)
    requeridas por `@rolldown/binding-wasm32-wasi` para que `npm ci` no falle en CI.
  - **Compatibilidad Python 3.10 (`N2`)**: `_parse_iso` en `motor.py` y el
    arranque de `edge/nodo.py` normalizan sufijos `"Z"` antes de
    `datetime.fromisoformat`, respaldado por matriz `["3.10", "3.11"]` en CI.
  - **Pulsos múltiples, reinicio y recuperación multilote (`N3`–`N5`)**:
    `EstadoCuenca.ultimo_critico` extiende el piso de retención hasta
    `max(arribo_estimado, ultimo_critico + eta) + MARGEN_ARRIBO_MIN` sin mover
    el `arribo_estimado` del frente inicial; DuckDB persiste ambos en
    `cuencas_meta`; y `Motor._recuperacion` fusiona lotes históricos
    consecutivos de un mismo corte en un único evento `RECUPERACION`.
  - **Upsert unificado en fuentes y claridad E2E (`N6`–`N7`)**:
    `FuentesRepository.guardar_lecturas` actualiza `valor` en conflicto para
    todos los orígenes (`OBSERVADO`, `REANALISIS`, `PRONOSTICO`), y
    `tests/test_e2e_tablero.py` documenta que verifica bundle/API/WS offline sin
    navegador headless.
  - **Emergencia LoRa y precipitaciones en UI (`M1`/`M5`)**: `Motor.resumen`
    expone `nodo.ultima_emergencia` (priorizada en `TarjetaCuenca` y `Landing`
    cuando supera a `ultima`), y `PestanaHidrologia` consulta
    `/api/fuentes/lecturas?limite=30` para mostrar último valor y hora UTC.
