# QuebradaAlert

Demostración de una red de estaciones hidrológicas que sigue alertando cuando se cae la conexión. Cada
estación guarda sus lecturas en un búfer local, evalúa el semáforo por su cuenta y, al volver el enlace,
entrega lo acumulado sin pérdidas, sin duplicados y sin disparar alarmas por tormentas que ya terminaron.

El caso de uso son las crecidas súbitas y flujos aluvionales ("volcanes") de las microcuencas tributarias
del río Grande en la Quebrada de Humahuaca (Jujuy).

> **Es una demo.** Las estaciones son simuladas, los umbrales del semáforo son valores de ejemplo sin
> calibrar y el tiempo de arribo es orientativo. No emite alertas reales. Las acciones que muestra el
> tablero son recomendaciones: la decisión de corte o evacuación corresponde a Defensa Civil, la DPRH y
> Vialidad Nacional.

## Cómo correrla

Requiere Python 3.10 o superior y Node.js 20 o superior (solo para compilar el tablero una vez).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
(cd frontend && npm ci && npm run build)
python -m quebrada.demo
```

Abrir <http://127.0.0.1:8000>. Después de compilar el tablero no hace falta conexión a internet: el mapa
usa un relieve y capas GeoJSON guardados en `data/`.

`python -m quebrada.demo` levanta el backend y un proceso por estación. El tiempo simulado corre 60 veces
más rápido que el real (`--escala`): una tormenta de una hora dura un minuto.

Tests y estilo: `pytest -q` y `ruff check .`

## Qué hay

| Carpeta | Contenido |
|---|---|
| `quebrada/schemas.py` | Contratos Pydantic de telemetría, nacimiento del nodo y paquete de emergencia. |
| `quebrada/hydrology.py` | Semáforo y fórmula de Kirpich, como funciones puras. |
| `quebrada/edge/` | Nodo simulado: SQLite en modo WAL, secuencia, modo isla, cola de reenvío y alerta local. |
| `quebrada/backend/` | FastAPI + DuckDB: ingesta, reconciliación, motor de alertas, WebSocket y parte de situación. |
| `frontend/` | Tablero React + Vite + Tailwind + Leaflet con la consola de crisis. |
| `scripts/preparar_geodatos.py` | Delimita las microcuencas y genera las capas de `data/`. |

### Nodo

- Mide cada 5 minutos en verde y cada 30 segundos en el resto de los niveles.
- Cada lectura se guarda en SQLite con un número de secuencia antes de intentar transmitirla.
- Si el envío falla pasa a `ISLAND_MODE` y sigue midiendo y evaluando el semáforo.
- En naranja o rojo sin enlace emite un paquete corto por el enlace de respaldo (emula LoRa) y, en rojo,
  activa la baliza local.
- Al volver el enlace envía lo pendiente en orden. Solo la lectura recién tomada viaja como telemetría en
  vivo; el resto lleva `is_historical: true`.

### Backend

- Guarda todas las lecturas en DuckDB con clave `(node_id, seq)`: un reenvío no duplica.
- Solo la telemetría en vivo y los paquetes de emergencia cambian el semáforo. Las lecturas históricas
  completan la serie y dejan un evento informativo con el nivel máximo que el nodo vio durante el corte.
- Recalcula el semáforo con las mismas reglas que el nodo.
- Al llegar a naranja fija la hora estimada de arribo a la RN 9 (hora de detección más el tiempo de
  Kirpich) y no la reinicia mientras dure el episodio.
- Si un nodo no transmite durante su tiempo de vida declarado, lo da por caído (`NDEATH`).
- Mientras el enlace principal está caído, un nivel recibido por el enlace de respaldo solo puede subir:
  baja recién cuando vuelve la telemetría en vivo.

Los mensajes usan los tópicos y el ciclo de vida de Sparkplug B (`spBv1.0/QUEBRADA/NBIRTH|NDATA/<nodo>`)
sobre HTTP y JSON. No hay broker MQTT ni codificación protobuf.

### Semáforo

| Nivel | Criterio |
|---|---|
| Verde | Ninguno de los siguientes. |
| Amarillo | 10 mm o más en 60 min, o más de 30 mm en 72 h con lluvia activa (1 mm o más en 60 min). |
| Naranja | Más de 15 mm en 15 min, o ascenso del nivel de más de 30 cm en 15 min. |
| Rojo | Más de 25 mm en 15 min y, además, ascenso de más de 30 cm en 15 min o turbidez mayor a 500 NTU. |

El contrato de telemetría agrega `water_level_rise_15m_cm` al esquema original, porque el semáforo lo necesita.

## Geografía

Las microcuencas se delimitaron con el MDE Copernicus GLO-30 (30 m, reproyectado a UTM 19S) y pysheds
(relleno de depresiones, direcciones D8, acumulación). La RN 9, los cursos de agua y las localidades salen
de OpenStreetMap. La especificación original pedía SRTM 30 m; se usó Copernicus porque se descarga sin
registro.

| Cuenca | Localidad | Área (km²) | Cauce (km) | Pendiente | Estación → RN 9 (km) | Pendiente del tramo | Kirpich tramo (min) |
|---|---|---|---|---|---|---|---|
| Arroyo del Medio | Volcán | 21 | 15,0 | 0,164 | 7,5 | 0,070 | 52 |
| Río Tumbaya Grande | Tumbaya | 157 | 28,4 | 0,085 | 14,2 | 0,087 | 79 |
| Río Purmamarca | Purmamarca | 380 | 34,6 | 0,065 | 17,3 | 0,044 | 119 |
| Río Huasamayo | Tilcara | 113 | 19,4 | 0,109 | 9,7 | 0,112 | 53 |

- **Salida de la cuenca:** la celda de mayor acumulación sobre el curso trazado en OSM, hasta 2,5 km aguas
  arriba del cruce con la RN 9 y a más de 300 m del río Grande.
- **Estación de cabecera:** ubicación hipotética, a mitad del cauce principal. No existe en el terreno.
- **Tiempo de arribo:** Kirpich, $t_c = 0{,}0195\,L^{0{,}77}\,S^{-0{,}385}$, aplicado al tramo entre la
  estación y la RN 9.

Para regenerar las capas: `pip install -e ".[geo]"` y `python scripts/preparar_geodatos.py` (descarga el
MDE y OSM en `data_raw/`).

## Limitaciones

- **Umbrales sin calibrar.** No hay un registro local de aludes con su lluvia asociada.
- **Kirpich** se desarrolló para cuencas agrícolas pequeñas y describe escurrimiento de agua, no flujos de
  detritos. Los tiempos de la tabla (50 a 120 minutos) son mayores que los 20 a 45 minutos que suelen
  citarse para estos eventos.
- **Cuencas sin validar.** Los contornos salen de un procedimiento automático y no se contrastaron con
  cartografía oficial ni con la DPRH. La cuenca de Purmamarca (380 km²) no es una microcuenca.
- **Lluvia, nivel y turbidez simulados** con un modelo de reservorio lineal sin base local.
- **Sin perfiles de tormenta reales.** No se incorporaron datos de Open-Meteo.
- **Enlace de respaldo:** se emula como un segundo canal HTTP. El alcance de LoRa en quebradas encajonadas
  habría que medirlo en el terreno.

## Guion de la demo (3 minutos)

1. **Autonomía.** Con el Wi-Fi apagado, abrir el tablero: cuatro cuencas en verde transmitiendo.
2. **Tormenta y corte.** Elegir Volcán, pulsar *Tormenta convectiva* y, unos segundos después, *Cortar
   enlace celular*. El nodo pasa a `ISLAND_MODE` y el contador del búfer SQLite sube.
3. **Decisión en el borde.** El registro del nodo muestra la alerta autónoma. El paquete de emergencia
   llega por el respaldo: la cuenca pasa a naranja y luego a rojo, con la cuenta regresiva a la RN 9.
4. **Recuperación.** Pulsar *Restablecer enlace celular*: el búfer se vacía, la serie se completa (barras
   violetas), "lecturas faltantes" queda en 0 y no aparecen alertas nuevas.

Variante: cortar también el respaldo LoRa antes de la tormenta y restablecer todo cuando ya volvió a verde.
El tablero nunca pasa a rojo, pero el evento `RECUPERACION` informa que el nodo llegó a rojo durante el corte.
