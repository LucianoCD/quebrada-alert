# Fuentes de datos para QuebradaAlert

Relevamiento del 22/11/2026. "Probado" significa que hice la consulta desde mi máquina y obtuve datos; "leído" significa que solo consta en la página o publicación citada. No revisé las licencias en detalle salvo donde se indica.

## 1. Conclusiones

- **No hay ninguna medición pública de nivel, caudal ni turbidez en los tributarios de la Quebrada.** Esas variables tienen que seguir siendo simuladas.
- **Hay dos pluviómetros telemétricos con datos horarios descargables**: Volcán (desde junio de 2026) y Humahuaca (desde junio de 2023). Ninguno está en una cabecera.
- **Volcán todavía no registró una tormenta**: máximo 2,2 mm en una hora y 13 mm en total. Hoy no sirve para calibrar umbrales.
- **El alud del 10/1/2017 sí se ve en satélite**: CMORPH da 48,6 mm entre las 09 y las 15 UTC sobre la cuenca, con pico de 25,6 mm/h a las 13 UTC. Es el mejor candidato para un "perfil de tormenta real".
- **No hay radar meteorológico con cobertura útil publicada para la Quebrada** (no lo comprobé producto por producto; ver 3.3).
- **No encontré una API oficial de cortes de ruta.** La página de Vialidad carga una planilla de Google con una clave propia de la página.

## 2. Lluvia y nivel medidos en tierra

| Fuente | Qué da | Estado | Acceso | Límite principal |
|---|---|---|---|---|
| SNIH, estación 280049 Volcán | Lluvia horaria | Probado: 4.100 registros, 4/6/2026 a 22/11/2026 | HTTP sin clave, sin documentación | Sin temporada de lluvias todavía; 0 horas con 8 mm o más |
| SNIH, estación 10040 Humahuaca (Esc. Agrotécnica 3) | Lluvia, cada 4 h hasta ago-2026 y horaria después | Probado: 9.047 registros, 30/6/2023 a 22/11/2026 | Igual | A unos 80 km de Volcán; máximo 18,5 mm (8/11/2023), 4 registros de 8 mm o más |
| SNIH, 111925 Hornillos (INTA IPAF NOA) | Figura en el catálogo | Probado: 0 registros | Igual | Sin datos por esta vía |
| SNIH, 10035 Sayate | Nivel cada 4 h | Probado: 448 registros recientes | Igual | Es Puna, no Quebrada |
| SNIH, datos "históricos validados" | — | Probado: vacío en todas las estaciones consultadas | Igual | — |
| Red MATTEO (pluviómetros manuales) | Lluvia diaria | Probado: servicio ArcGIS público, 111.573 registros en el país | REST sin clave | En Jujuy solo 9 pluviómetros, todos en San Salvador; ninguno en la Quebrada. Incluye nombre del operador (dato personal) |
| Nodo DPRH (mapas.dprh.jujuy.gob.ar/nodo) | Visor | Probado | Web | No tiene API propia: muestra SNIH, MATTEO, Open-Meteo y radar |
| INTA Salta-Jujuy (intasalta.github.io/emas) | Estaciones automáticas con CSV en GitHub | Probado solo el índice | CSV | En la lista vi Abra Pampa y Yuto, no la Quebrada |
| INTA SIGA | Series diarias | No pude conectar (siga.inta.gob.ar no respondió) | Paquete R `siga` | Sin verificar |
| SMN, API ws1.smn.gob.ar | — | Probado: 401 sin token | — | Requiere credencial |

Leído, sin verificar: la DPRH declaró en prensa (19/10/2026) 16 estaciones automáticas, 5 de COREBE y unos 50 pluviómetros MATTEO, y que en Volcán 8 mm disparan el primer aviso. Solo una parte de esa red aparece en el SNIH.

El SNIH no publica la hora de llegada de cada dato, y su zona horaria sigue sin confirmar.

## 3. Lluvia estimada a distancia

### 3.1 Satélite

| Producto | Resolución | Desde | Estado | Acceso |
|---|---|---|---|---|
| CMORPH (NOAA NCEI) | 8 km, 30 min | 1998 | Probado: leí 6 archivos del 10/1/2017 | HTTP directo, NetCDF |
| GOES-19 tasa de lluvia (ABI-L2-RRQPEF) | 2 km nominal, 10 min | GOES-16 desde dic-2019 | Probado: listado en AWS | S3 abierto |
| GOES-19 rayos (GLM-L2-LCFA) | 20 s | 2018 aprox. | Probado: listado | S3 abierto |
| PDIR-Now (UC Irvine) | 0,04°, 1 h | 2000 | Probado: índice | HTTP directo |
| CHIRPS v3 | 0,05°, diario | 1981 | Probado: bajó un archivo; no lo muestreé (la ruta diaria que armé después falló) | HTTP directo |
| IMERG V07 (NASA) | 0,1°, 30 min | 2000 | Probado: listado público, descarga 401 | Cuenta Earthdata gratuita |

CMORPH sobre la cuenca Los Filtros / Del Medio, 10/1/2017 (mm/h, dos medias horas por fila):

| Hora UTC | Primera media hora | Segunda media hora |
|---|---|---|
| 11 | 0,4 | 4,2 |
| 12 | 7,1 | 19,7 |
| 13 | 25,6 | 16,9 |
| 14 | 15,5 | 7,8 |

Coincide en horario con la publicación de Esper Angillieri (8 a 10 hora local). La magnitud no: el artículo cita 170 mm por comunicación verbal de la DPRH, CMORPH da 48,6 mm y ERA5 da 108 mm en tres días. Ninguno de los tres es una medición confiable de la cabecera.

### 3.2 Reanálisis y pronóstico

| Fuente | Qué da | Estado |
|---|---|---|
| Open-Meteo archivo (ERA5 / ERA5-Land) | Horario desde 1940 | Probado. Para Volcán, 9 a 11/1/2017: 108 mm, máximo 21 mm/h |
| Open-Meteo pronóstico | Horario y cada 15 min | Probado |
| Open-Meteo pronósticos históricos y ensambles | Horario | Probado |
| WRF-SMN en AWS | 4 km, horario, 4 ciclos por día | Probado: disponible desde enero de 2022, solo determinístico |

Open-Meteo es gratis para uso no comercial. Todos son grillas de varios kilómetros: no resuelven una celda convectiva sobre una cabecera.

### 3.3 Radar

- El visor de SINARAME (radares.hidricosargentina.gob.ar) responde, pero no encontré un punto de descarga de datos.
- Los radares más cercanos de la lista leída son Las Lajitas (Salta), Las Lomitas y Termas de Río Hondo. No comprobé si alguno alcanza la Quebrada; con la Cordillera Oriental en el medio, lo dudo.
- Leído: la provincia pidió un radar al SMN.

## 4. Geografía

| Fuente | Qué da | Estado |
|---|---|---|
| Copernicus DEM GLO-30 | Relieve de 30 m | Ya usado en el repositorio |
| IGN, WFS (wms.ign.gob.ar/geoserver/ows) | 192 capas: rutas nacionales, cursos de agua, localidades, puentes, ferrocarril | Probado: la capa de rutas devolvió la RN 9 y la RN 52 en la zona |
| IGN, servicio de cuencas (ANIDA/fisiconat_hidro02) | Cuencas y regiones hídricas | Probado: responde; no comparé con nuestros contornos |
| datos.transporte.gob.ar, rutas nacionales | GeoJSON y shapefile, licencia "Otra (Abierta)" | Probado: catálogo |
| OpenStreetMap | RN 9 y plantas urbanas | Ya usado |
| IDE Jujuy, SIGAM de SEGEMAR | Capas provinciales y geológicas | No respondieron desde mi máquina |

## 5. Eventos históricos

| Fuente | Qué da | Estado |
|---|---|---|
| DesInventar Argentina | Base descargable completa (XML, 21.824 fichas, hasta 2019) | Probado: extraje 52 fichas de inundación, aluvión y deslizamiento en Tumbaya, Tilcara y Humahuaca, de 1970 a 2007 |
| Esper Angillieri, Perucca y Vargas (2018, 2020) | Alud de Volcán del 10/1/2017, morfometría de Los Filtros, Coiruro y Del Medio | Leído el preprint (licencia CC BY 4.0) |
| Marcato, Pasuto y Rivelli (2009) | Huasamayo 1983, Purmamarca 1984, Volcán 1945 | Leído solo el resumen de búsqueda |
| SEGEMAR, Estudio Geológico Integrado de la Quebrada de Humahuaca y zonificación de remoción en masa | Susceptibilidad | Encontrados en el repositorio; no los abrí |
| Chalabe y otros, Facultad de Ingeniería UNJu | SIG de amenazas en Volcán | Encontrado; no lo leí |

Dos límites de DesInventar: las fichas tienen fecha y departamento, no hora ni cuenca; y en esos tres departamentos no hay fichas posteriores a 2007, así que el alud de 2017 no figura.

El preprint también da la lluvia anual de Volcán entre 1934 y 1996 (media 391 mm; enero cerca de 115 mm), con datos de INTA Salta.

## 6. Estado de rutas

- Página oficial de Vialidad Nacional: los datos salen de una planilla de Google leída con una clave incluida en la página. No la consulté por fuera de la página y no es una API documentada.
- Tráfico Ahora Argentina: servicio de terceros, pago.
- No encontré un historial público de cortes de la RN 9.

## 7. Recomendación

**Integrar ya (sin permisos):**
1. Perfil de la tormenta del 10/1/2017 desde CMORPH, como escenario "Volcán 2017" de la consola de crisis, rotulado como estimación satelital.
2. Día normal y clima base desde Open-Meteo (ERA5) para los cuatro puntos.
3. Lluvia observada de Volcán (280049) y Humahuaca (10040) como capa de referencia, sin mezclarla con los nodos simulados.
4. RN 9, cursos de agua y localidades desde el IGN, y comparación de nuestros contornos con las cuencas del IGN.
5. Tabla de antecedentes con las 52 fichas de DesInventar más los eventos de la literatura.

**Precachear para la demo:** archivos CMORPH o GOES de dos o tres eventos, y un ciclo del WRF-SMN.

**Solo para contraste, no para alertar:** GOES, PDIR-Now, IMERG, CHIRPS.

**Requiere pedirlo a la DPRH:** las estaciones automáticas que no están en el SNIH, la hora de llegada de los datos, cualquier medición de nivel en tributarios, el registro de eventos con hora, y el origen del umbral de 8 mm.

**Sigue siendo sintético:** nivel, turbidez, batería y fallas de comunicación.

## 8. Lo que no pude verificar

- SIGAM de SEGEMAR, IDE Jujuy e INTA SIGA no respondieron.
- Cobertura real de radar sobre la Quebrada.
- Calidad de GOES, PDIR-Now y CHIRPS para el evento de 2017 (GOES no lo cubre).
- Licencias de SNIH, MATTEO, IGN y DesInventar.

## 9. Complemento: catálogo técnico de producción (PDF adjunto)

`Fuentes de Datos para QuebradaAlert.pdf` (8 pág.) es un catálogo de arquitectura
para producción que complementa este relevamiento. Coincidencias y aportes:

**Coincide con este relevamiento:**

- Ningún producto satelital de observación sirve para gatillar una evacuación:
  latencias de 2 a 18 h frente a tiempos de concentración de ~18 a 54 min en las
  subcuencas laterales.
- Open-Meteo/ERA5 como referencia climática (gratis solo no comercial;
  self-host si cambia el uso).
- Copernicus GLO-30 como MDE primario y OSM para cartografía.
- IMERG/CHIRPS como contraste histórico, nunca como disparador aislado.
- La red terrestre es el punto ciego: el SMN deja un vacío de ~230 km entre
  sus tres estaciones fuera del cañón central.

**Aporta lo que este relevamiento no cubrió:**

- **WRF-DET 4 km del SMN en AWS Open Data** (`s3://smn-ar-wrf`, sin credenciales,
  CC BY 2.5): PP cada 10 min y 1 h, SMOIS y Freezing_level, 2 ciclos/día hasta
  +72 h — el motor anticipatorio 0–72 h que la tabla 3.2 solo listaba como
  "disponible".
- **SMAP L4** (humedad de suelo cada 3 h, latencia ~2 h, Earthdata gratis) para
  ajustar umbrales según saturación antecedente (ventana de 3 a 5 días).
- **FI-UGICH/UNJu–DPRH**: capas 1:50.000 de la cuenca del Río Grande
  (morfológicas, áreas hidrológicas, dominio, Pfafstetter) — alternativa
  oficial a nuestra delimitación automática de microcuencas.
- **Curvas I–D de referencia** para calibrar umbrales (Guzzetti 2008, Caine
  1980) y análogos semiáridos (Mendoza 6,5–12,9 mm/24 h; Quebrada Amarilla
  5,5 mm/24 h tras 13,2 mm en 3 días; Macul 12 mm/h): regla condicionada por
  humedad del suelo e isoterma 0 °C — responde al pendiente "umbrales sin
  calibrar" de las limitaciones.
- **Umbrales SAT del SMN** como vocabulario de contraste: amarilla 20–50 mm y
  naranja 50–70 mm acumulados (dinámicos, revisables).
- **Kirpich por subcuenca** (literatura): Huasamayo 17,9–54,2 min total y
  17,9–37,3 min por subcuenca; Chalala 25,9–29,8 min — coherente con tormentas
  disparadoras de ~40 min documentadas.
- **Restricciones de licencia**: FABDEM es CC BY-NC-SA (no comercial); Open-Meteo
  gratis solo no comercial; endpoints no documentados del SMN requieren caché y
  degradación controlada.
- **Descarta ALOS PALSAR 12,5 m** (remuestreo de SRTM, no aporta).
- **Precaución bibliográfica**: el preprint nhess-2018-207 (Esper Angillieri
  2018) está **retractado** en NHESS — usar Geografiska Annaler 2020 o informes
  DPRH/SEGEMAR para el alud de 2017.
- **Brechas institucionales**: SMN SAT sin API oficial documentada; DPRH con 6
  estaciones hidrometeorológicas operativas (mayo 2025) + 9 en gestión pero sin
  portal público de telemetría.
- **Solicitudes formales sugeridas por el PDF**: IGN MDT 5 m / VANT 0,5 m
  (asesoriatecnica@ign.gob.ar, con polígono de interés), telemetría DPRH
  (priorizar Potrero de Yala), Carta SEGEMAR 2366-IV
  (peligrosidad.geologica@segemar.gov.ar), mediciones de INTA Hornillos y API
  A5 del INA-SIyAH.
- **Mapa offline**: el PDF propone Protomaps PMTiles + Geofabrik; la demo ya lo
  resuelve con archivos estáticos propios en `docs/data/` — PMTiles es la vía si
  se escala a móvil o a todo el corredor.

## 10. Protocolo de contraste cartográfico, Terrain-RGB offline y matriz de licencias

### 10.1 Contraste de cuencas automáticas (`docs/data/cuencas.geojson`)
Los polígonos actuales delimitados automáticamente con `pysheds` sobre Copernicus GLO-30 (en particular `CUENCA_PURMAMARCA` con `379,9 km²`) deben contrastarse antes de un piloto con:
- **FI-UGICH/UNJu–DPRH (1:50.000):** áreas hidrológicas y subcuencas oficiales del Río Grande.
- **IGN WFS (`ANIDA/fisiconat_hidro02`):** cuencas y trazado oficial de rutas/cursos.

Métricas mínimas de validación por cuenca:
1. Error relativo de área $|\Delta A| / A_{\text{oficial}} \le 10\%$.
2. Índice de Jaccard (IoU) entre polígonos $\ge 0{,}80$.
3. Desplazamiento del punto de cruce con la RN 9 $\le 100\text{ m}$ respecto al puente/badén oficial de Vialidad Nacional.

### 10.2 Generación offline de Terrain-RGB
El script `apps/api/scripts/preparar_geodatos.py` incorpora codificación **Mapbox Terrain-RGB** (`codificar_terrain_rgb` / `generar_terrain_rgb`, paso vertical $0{,}1\text{ m}$, base $-10000\text{ m}$) proyectando Copernicus GLO-30 a `EPSG:3857` en teselas `256x256` PNG para zooms `10..12` bajo `docs/data/terrain/{z}/{x}/{y}.png`, registrando el descriptor `terrain` en `contexto.geojson` sin alterar los 5 archivos base de la demo.

### 10.3 Matriz de licencias para transición demo → piloto comercial B2G
| Activo / Fuente | Licencia actual | Uso permitido | Acción para piloto comercial B2G |
|---|---|---|---|
| Copernicus DEM GLO-30 | Abierta (Copernicus / AWS Open Data) | Comercial y no comercial | Conservar atribución. |
| OpenStreetMap | ODbL | Comercial con atribución y Share-Alike en derivados | Mantener atribución ODbL. |
| WRF-DET 4 km (SMN AWS) | CC BY 2.5 | Comercial con atribución | Conservar atribución SMN. |
| Open-Meteo (tier gratuito) | Solo no comercial | **Restringido en piloto pago** | Migrar a instancia self-hosted o licencia comercial. |
| FABDEM | CC BY-NC-SA | **Solo no comercial** | No incorporar en servicio comercial sin licencia específica. |
| SNIH / IGN / DPRH / SEGEMAR | Institucional sin API/licencia unificada | Pendiente de confirmación formal | Solicitar convenios y permisos explícitos antes de operación. |
| Preprint `nhess-2018-207` | **Retractado** | Prohibido para calibración | Usar *Geografska Annaler* (2020) e informes DPRH/SEGEMAR. |
