---
tags: [decisiones, adr]
actualizado: 2026-11-22
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
