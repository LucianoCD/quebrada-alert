---
tags: [dominio, glosario]
actualizado: 2026-11-22
---

# Glosario

Términos del dominio que el equipo (y los agentes) deben usar igual.

## Semáforo {#semaforo}

Clasificación del estado de riesgo de una cuenca, calculada **idéntica** en el
nodo y en el backend (`hydrology.clasificar`):

| Nivel | Criterio |
|---|---|
| Verde | Ninguno de los siguientes. |
| Amarillo | ≥10 mm en 60 min, o >30 mm en 72 h con lluvia activa (≥1 mm en 60 min). |
| Naranja | >15 mm en 15 min, o ascenso del nivel >30 cm en 15 min. |
| Rojo | >25 mm en 15 min **y** (ascenso >30 cm en 15 min **o** turbidez >500 NTU). |

## Modo isla / ISLAND_MODE

Estado del nodo cuando el enlace principal falla: sigue midiendo, evaluando el
semáforo y acumulando en el búfer SQLite. Al volver el enlace, reenvía en orden
y solo la lectura recién tomada viaja como telemetría en vivo; el resto lleva
`is_historical: true`.

## NDEATH / EN_LINEA

Eventos del motor: si un nodo no transmite durante su `keepalive_s` declarado,
se lo da por caído (`NDEATH`); al reaparecer, `EN_LINEA`. Un NBIRTH o NDATA
cuenta como señal de vida.

## Paquete de emergencia / EMERGENCIA

Mensaje corto que el nodo envía por el enlace de respaldo cuando está en
naranja/rojo sin enlace principal. Solo puede **subir** el nivel del centro de
comando; la bajada espera a la telemetría en vivo.

## Cuenta regresiva / arribo estimado

Al llegar a naranja, el motor fija `arribo_estimado` = detección +
`eta_min` (Kirpich del tramo estación→RN 9) y no la reinicia mientras dure el
episodio.

## Recuperación / RECUPERACION

Evento informativo que genera el motor al vaciarse el búfer: informa el nivel
máximo que el nodo vio durante el corte (`edge_local_alert`), aunque el centro
nunca haya recibido telemetría en vivo de ese episodio.

## Microcuenca / cuenca

Área de drenaje pequeña tributaria del río Grande. En el proyecto hay 4:
Arroyo del Medio (Volcán), Tumbaya Grande (Tumbaya), Purmamarca y Huasamayo
(Tilcara). Ver `docs/data/cuencas.geojson` y `README.md` § Geografía.

## Nodo / estación

Estación hidrológica simulada en la cabecera de cada cuenca. Node IDs:
`EST-VOLCAN-CAB01`, `EST-TUMBAYA-CAB01`, `EST-PURMAMARCA-CAB01`,
`EST-TILCARA-CAB01`.
