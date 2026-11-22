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
