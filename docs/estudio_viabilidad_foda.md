# Estudio de viabilidad y FODA — QuebradaAlert

**Fecha:** 22 de noviembre de 2026  
**Objeto:** prototipo de sistema de alerta temprana edge-first para crecidas súbitas y flujos aluvionales en microcuencas tributarias del río Grande (Quebrada de Humahuaca, Jujuy).  
**Fuentes:** implementación actual del repositorio; propuesta de valor del proyecto; estudio *De Prototipo a Piloto*; propuesta reglamentaria de Trabajo Final FI-UNJu (CAFI N.º 085/22); relevamientos de fuentes de datos en `docs/` y notas de `cerebro/`.

---

## 1. Resumen ejecutivo

QuebradaAlert es **técnicamente viable como prototipo de demostración** y **conceptualmente viable como camino hacia un piloto institucional**, siempre que se mantenga la fidelidad a la arquitectura edge-first y se cubran, en fases posteriores, tres brechas críticas: calibración hidrológica local, telemetría real (o acuerdo formal con la DPRH) y adopción operativa.

El valor del sistema no es “mostrar lluvia en un mapa”, sino **convertir telemetría (o su simulación creíble) en una ventana de maniobra accionable** —semáforo + ETA a la RN 9— que siga funcionando cuando cae la conectividad, precisamente el momento en que fallan los SAT centrados en la nube.

| Dimensión | Veredicto | Condición |
|---|---|---|
| Técnica (prototipo software) | **Viable** | Ya demostrada en el repo |
| Técnica (piloto físico) | **Condicionalmente viable** | Hardware + LoRaWAN + validación en campo |
| Datos | **Condicionalmente viable** | Acceso DPRH/SNIH/SMN y calibración con eventos |
| Operativa / institucional (B2G) | **Prometedora, no cerrada** | Complementar, no competir con DPRH/SINAME |
| Económica (cualitativa) | **Atractiva en lógica de prevención** | Requiere cuantificar costos actuales de cortes RN 9 |
| Académica (alineación TF UNJu) | **Complementaria** | QuebradaAlert cubre el borde táctico; el TF cubre GeoAI + pronóstico |

---

## 2. Problema y propuesta de valor

### 2.1 Problema

La Quebrada de Humahuaca concentra precipitación estival, fuertes pendientes y suelos poco consolidados. Los flujos densos (p. ej. Volcán, 10/1/2017: víctimas, evacuados y daño masivo al tejido urbano) pueden alcanzar asentamientos y la RN 9 en ventanas cortas. Las tormentas que disparan el riesgo suelen degradar a la vez energía y comunicaciones: un SAT que depende de nube continua falla en el minuto crítico.

En paralelo, la DPRH y Defensa Civil ya operan un centro de monitoreo (estaciones COHIFE, COREBE, Programa Matteo, visores provinciales). El umbral empírico de 8 mm en Volcán mejoró el margen de alerta, pero el ecosistema institucional sigue con huecos en: respuesta de microcuencas de cabecera, supervivencia offline, y (en la línea del TF) pronóstico probabilístico e indicadores satelitales acoplados en tiempo real.

### 2.2 Propuesta de valor (B2G)

| Beneficiario | Problema | Qué ofrece QuebradaAlert | Métrica de valor |
|---|---|---|---|
| **Vialidad Nacional** | Cortes reactivos y costosos de la RN 9 | ETA a puntos críticos; corte preventivo más preciso | Menor tiempo de cierre y costo de reparación |
| **Defensa Civil y municipios** (Volcán, Tumbaya, Tilcara, Purmamarca) | Poco tiempo para evacuación ordenada | Cuenta regresiva + semáforo + parte de situación | Mayor lead time operativo |
| **DPRH** | Falta de detalle táctico en tributarios de respuesta rápida | Serie de alta frecuencia persistida + semáforo auditable | Mejor base para calibrar y complementar visores |
| **Turismo / economía regional** | Interrupciones del corredor patrimonial UNESCO | Mayor previsibilidad del corredor | Menor percepción de riesgo no gestionado |

**Frase de valor:** no vende software; ofrece una **plataforma de decisión** que reduce incertidumbre en crisis y deja evidencia hidrológica trazable (secuencia, histórico recuperado, eventos).

### 2.3 Alcance de este estudio

- **Incluye:** viabilidad del prototipo actual y del salto a piloto territorial acotado (Humahuaca / microcuencas tipo Arroyo del Medio).
- **Excluye:** diseño de negocio con precios, fabricación de hardware, y el alcance completo del TF GeoAI/Kafka/Chronos (se trata como contexto y oportunidad de integración, no como alcance de QuebradaAlert).

---

## 3. Estado de implementación (evidencia)

Lo siguiente está **implementado y demostrable** en el monorepo:

| Capacidad del estudio de viabilidad previo | Estado en el proyecto |
|---|---|
| Nodos edge Python con SQLite WAL, `seq`, `ISLAND_MODE` | Sí — `apps/api/quebrada/edge/` |
| Semáforo local, baliza, paquete de emergencia | Sí — respaldo emulado por HTTP `/api/respaldo` |
| Sparkplug B (NBIRTH/NDATA/NDEATH) sin broker MQTT | Sí — HTTP+JSON sobre FastAPI |
| Reconciliación `is_historical` sin falsas alarmas | Sí — `motor.py` |
| DuckDB + FastAPI + WebSocket | Sí |
| Tablero React/Vite/Tailwind offline | Sí — Leaflet + relieve PNG + GeoJSON en `docs/data/` |
| Kirpich + humedad antecedente 72 h + matriz semáforo | Sí — umbrales de ejemplo |
| Consola de crisis y parte de situación | Sí — `/api/parte/{basin_id}` |
| Cuatro microcuencas (Volcán, Tumbaya, Purmamarca, Tilcara) | Sí — DEM Copernicus GLO-30 + OSM |
| Hardware ESP32 / LoRaWAN real | No — fuera del prototipo |
| MBTiles / MapLibre vectorial | No — otra vía offline (estáticos propios) |
| Perfiles Open-Meteo / lluvia histórica inyectada | No — pendiente |
| Calibración con eventos locales | No — documentado como limitación |
| Integración SINAME / visores DPRH en producción | No |

**Conclusión de gap analysis:** el estudio *De Prototipo a Piloto* se cumple como especificación del **prototipo software**; no se cumple aún como **piloto físico ni sistema calibrado en operación**.

---

## 4. Viabilidad técnica

### 4.1 Arquitectura (tres capas)

1. **Nodo de borde:** persistencia antes de transmitir; evaluación local; modo isla; enlace de respaldo para emergencias.
2. **Transporte y motor:** contratos de ciclo de vida tipo Sparkplug B; idempotencia `(node_id, seq)`; distinción vivo vs histórico.
3. **Centro de comando offline:** mapa y ETA sin depender de teselas externas en tiempo real.

Esta arquitectura es **madura en componentes open source** (SQLite, FastAPI, DuckDB, React) y **adecuada al riesgo operativo** de la Quebrada. La transición a hardware (ESP32 + LoRa 915 MHz + pluviómetro + sensor de nivel) puede preservarse sin reescribir el contrato de mensajes, si se mantiene HTTP/JSON o un gateway que hable el mismo esquema.

### 4.2 Modelo hidrológico

- **Fortaleza:** umbrales ID + humedad antecedente + Kirpich son auditables, explicables ante Defensa Civil y suficientes para una demo táctica.
- **Debilidad conocida:** Kirpich describe escurrimiento de agua en cuencas agrícolas, no debris flows; los ETA del prototipo (orden 50–120 min en tramos estación→RN 9) pueden ser **conservadores o no representativos** frente a los 20–45 min citados en terreno. Los umbrales **no están calibrados** con pares lluvia–alud locales.
- **Veredicto:** viable como *motor de decisión de primer orden*; **no viable como verdad hidrológica** sin campaña de calibración (DPRH, UNJu/GT-IHLLA, eventos 2017/2021, etc.).

### 4.3 Datos

| Necesidad | Situación |
|---|---|
| Morfometría y mapa | Resuelta con Copernicus + OSM (SRTM era la especificación original; el cambio está justificado) |
| Lluvia / nivel / turbidez en cabecera | No hay serie pública adecuada → simulación |
| Antecedente y clima | Open-Meteo/ERA5, SMAP, IMERG, WRF-DET SMN: útiles para calibrar/anticipar, **no para gatillar** con tc de decenas de minutos |
| Acceso institucional | DPRH telemetría, IGN MDT 5 m, SEGEMAR: requieren solicitud formal |

**Veredicto:** el prototipo es viable **sin** datos de campo porque declara honestamente la simulación; un piloto operativo **no** lo es hasta cerrar acceso a telemetría o desplegar sensores propios.

### 4.4 Riesgos técnicos residuales

- Robustez LoRaWAN en quebradas encajonadas (línea de vista, SF, colisiones).
- Autenticación ausente en APIs de ingesta (aceptable en demo local, no en producción).
- Escala: DuckDB embebido alcanza para piloto chico; un lakehouse provincial (Kafka/Flink/Iceberg del TF) es otra escala.

---

## 5. Viabilidad operativa e institucional

### 5.1 Encaje con el ecosistema

QuebradaAlert debe posicionarse como **complemento**:

- **DPRH:** aporta detalle táctico en microcuencas y series de alta frecuencia; no reemplaza el visor provincial.
- **Defensa Civil / municipios:** consume ETA, semáforo y parte de situación.
- **Vialidad Nacional:** consume ETA a RN 9 para cortes preventivos.
- **SINAME / AFE:** potencial alimentación futura de alertas estructuradas (JSON), hoy no implementada.
- **UNESCO / patrimonio:** argumento de protección de itinerario cultural y corredor turístico.

### 5.2 Adopción

La adopción es el riesgo no técnico dominante. Condiciones favorables:

- Demostración en vivo del guion de resiliencia (tormenta + corte + recuperación).
- Parte de situación listo para compartir.
- Lenguaje de ROI en prevención (evitar daños vs costo de sensores), alineado al orden de magnitud que cita el TF (~intervención preventiva vs daños evitados a escala provincial).

Condiciones adversas: burocracia, falta de dueño operativo, desconfianza si los umbrales “suenan a demo”, y competencia percibida con sistemas ya desplegados.

### 5.3 Relación con la propuesta de TF FI-UNJu

| | QuebradaAlert (este proyecto) | TF CAFI 085/22 |
|---|---|---|
| Foco | Borde resiliente, semáforo, ETA, offline | GeoAI (Prithvi), streaming lakehouse, TSFM probabilístico |
| Cuencas | 4 microcuencas Humahuaca | Volcán + Grande/Xibi Xibi |
| Hardware IoT | Emulado; piloto físico posible | **Fuera de alcance** explícito |
| Horizonte de alerta | Minutos–~2 h (Kirpich / semáforo) | 1–24 h por cuantiles |
| Stack | FastAPI, DuckDB, SQLite, React | Kafka, Flink, Iceberg, TerraTorch, Chronos-2 |
| Usuario | Consola de crisis táctica | Interoperar con visores DPRH |

**Síntesis:** no son excluyentes. QuebradaAlert cubre la **última milla táctica y la supervivencia sin red**; el TF cubre **anticipación probabilística y fusión satelital**. Una hoja de ruta institucional coherente usaría el TF como capa Warm/Hot Path provincial y QuebradaAlert (o su contrato) como capa edge + despacho local cuando el enlace cae.

---

## 6. Viabilidad económica (cualitativa)

Sin un modelo financiero cerrado, la lógica de negocio pública es:

1. **Costo del no-sistema:** cortes de RN 9, limpieza, reparación, turismo varado, riesgo de vidas.
2. **Costo del sistema:** nodos de bajo costo (ESP32 + sensores + solar), un gateway LoRaWAN municipal, operación de software liviano.
3. **Argumento presupuestario:** inversión en prevención con ROI medible en horas de vía abierta y eventos con lead time documentado (“libro de bitácora” del piloto de 60 días).

Modelo secundario B2B (logística, seguros, turismo) es opcional y no debe condicionar la adopción pública inicial.

---

## 7. FODA

### Fortalezas

- Arquitectura **edge-first / offline-first** alineada al fallo real de comunicaciones.
- Prototipo **ya ejecutable** con tests, contratos claros (`schemas.py` / `docs/api.md`) y guion de demo.
- Semántica industrial ligera (Sparkplug B) sin infraestructura pesada.
- Propuesta de valor **accionable** (ETA + semáforo + parte), no solo visualización.
- Stack open source, auditable y transferible a un TF o a la DPRH por etapas.
- Honestidad documental (limitaciones, umbrales de ejemplo) que reduce riesgo reputacional en presentaciones técnicas.

### Oportunidades

- Demanda institucional post Emergencia Hídrica provincial y memoria del alud 2017.
- Complementariedad con red DPRH/COHIFE/Matteo y con el TF GeoAI/TSFM de la FI-UNJu.
- Patrimonio UNESCO y presión política sobre seguridad de la RN 9 / Travesía Urbana.
- Datos abiertos crecientes (WRF-DET SMN, Sentinel, Open-Meteo no comercial) para calibración y escenarios.
- Piloto de 60 días de bajo costo en Volcán/Tilcara con un solo gateway LoRaWAN.
- Narrativa B2G de prevención con métricas simples de lead time y cortes evitados.

### Debilidades

- Estaciones, lluvia, nivel y turbidez **simulados**; sin calibración local.
- Kirpich y umbrales **orientativos**; posible desajuste con debris flows reales.
- LoRa y hardware **no validados** en quebradas.
- Mapa offline funcional pero no el diseño MBTiles/MapLibre del estudio previo.
- Sin autenticación ni endurecimiento de producción.
- Cuenca Purmamarca (~380 km²) tensiona el supuesto de “microcuenca”.
- Equipo/demo aún dependiente de build local del tablero y orquestación manual.

### Amenazas

- Adopción institucional lenta o rechazo por solapamiento percibido con visores DPRH.
- Latencia satelital mal usada como gatillo (expectativa falsa de “AI que avisa sola”).
- Fallas de radio LoRaWAN o energía en el primer piloto → pérdida de confianza.
- Cambios de gestión política / prioridades presupuestarias.
- Licencias no comerciales (p. ej. Open-Meteo gratis, FABDEM) si se escala a producto.
- Sobreingeniería (lakehouse completo) que retrase el valor táctico ya demostrable.

---

## 8. Matriz de viabilidad por escenario

| Escenario | Qué se entrega | Viabilidad | Horizonte |
|---|---|---|---|
| **A — Demo / hackatón** | Sistema actual | Alta | Ahora |
| **B — Prototipo enriquecido** | Open-Meteo/CMORPH, escenario Volcán 2017, umbrales documentados, API hacia GeoJSON DPRH | Alta–media | 1–3 meses |
| **C — Piloto físico 60 días** | 1–4 nodos ESP32+LoRa, gateway municipal, bitácora de impacto | Media (condicional a permisos y radio) | 3–6 meses |
| **D — Integración provincial** | Complemento de visores DPRH + opcional acoplamiento a capa TF (cuantiles) | Media–baja sin sponsors | 6–18 meses |

---

## 9. Recomendaciones

1. **Separar mensajes:** presentar QuebradaAlert como prototipo resiliente de borde, no como SAT provincial completo ni como el TF GeoAI.
2. **Cerrar el gap de credibilidad hidrológica:** priorizar escenario “Volcán 2017”, acceso a series DPRH/SNIH y revisión de umbrales con UNJu/DPRH antes de hardware masivo.
3. **Mantener el contrato de mensajes** al pasar a ESP32: el valor acumulado está en NBIRTH/NDATA/emergencia/histórico, no en el lenguaje del firmware.
4. **Diseñar el piloto para evidencia:** cada evento con umbral, ETA vs observación, acción tomada y lead time — ese libro de bitácora vende más que el stack.
5. **Explorar puente con el TF:** QuebradaAlert como Hot Path táctico / edge; Chronos/Prithvi como anticipación 1–24 h y covariables; API GeoJSON común hacia los visores DPRH.
6. **No gatillar con satélite** en microcuencas de tc corto; usarlo para antecedente, cicatriz de fuego y validación post-evento.
7. **Cuantificar ROI con VN/DPRH** (horas de RN 9 cerrada, costos de limpieza) antes de pedir expansión de red.

---

## 10. Conclusión

El proyecto es **viable en el plano técnico del prototipo** y **alineado con una necesidad operativa real** de la Quebrada de Humahuaca. La propuesta de valor B2G es clara y diferencial respecto de un visor solo en línea: **supervivencia de la cadena de alerta bajo corte + ETA accionable**.

La viabilidad de pasar a piloto y a adopción institucional es **condicional**: depende de datos y calibración, de un primer despliegue de radio/hardware bien dimensionado, y de una estrategia de complemento (no sustitución) frente a DPRH, Defensa Civil y —si avanza— el TF de la FI-UNJu.

En términos FODA, las **fortalezas de diseño y el prototipo existente** pesan más que las debilidades actuales **si** el siguiente paso se acota a evidencia y piloto chico; las **amenazas de adopción y expectativas tecnológicas** pesan más si se intenta vender de inmediato un sistema provincial completo o un stack que el repositorio aún no es.

---

## Referencias internas

- `README.md` — alcance, semáforo, geografía, limitaciones  
- `docs/api.md` — contratos  
- `docs/fuentes_datos_quebrada_alert.md` — fuentes verificadas  
- `cerebro/arquitectura.md`, `cerebro/limitaciones.md`, `cerebro/fuentes-datos.md`, `cerebro/roadmap.md`  
- Documento adjunto: *De Prototipo a Piloto…*  
- Documento adjunto: *Propuesta TF FI-UNJu CAFI 085/22…*
