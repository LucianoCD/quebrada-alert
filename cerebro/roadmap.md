---
tags: [planificacion, roadmap]
actualizado: 2026-11-22
---

# Roadmap

Pendientes ordenados por lo que más valor da a la demo y al proyecto real.
Ver [[limitaciones]] para el porqué de cada límite.

## Antes de presentar

- [ ] Ensayar el [[demo-guion]] completo (3 min) con cortes de enlace reales.
- [ ] Verificar que el build del tablero quede en `apps/web/dist` antes de la demo.
- [ ] Probar la variante "respaldo también caído".

## Si hay tiempo

- [ ] Perfiles de tormenta reales desde Open-Meteo (hoy son simulados).
- [ ] Medir/justificar el alcance real de LoRa en quebradas (hoy es un segundo
      canal HTTP).
- [ ] Contrastar los contornos de cuenca con cartografía DPRH.
- [ ] Registrar datos de aludes históricos para calibrar umbrales del semáforo.

## Datos e ingesta (relevamientos del 22/11/2026)

Ver [[fuentes-datos]]. Orden sugerido por los relevamientos:

- [ ] Escenario "Volcán 2017": perfil CMORPH del alud (48,6 mm, pico 25,6 mm/h)
      rotulado como estimación satelital.
- [x] Día normal y clima base desde Open-Meteo ERA5 para los cuatro puntos
      (ingesta periódica `open_meteo_archive` + forecast).
- [x] Capa de referencia con lluvia observada SNIH (Volcán 280049, Humahuaca
      10040), sin mezclarla con los nodos simulados (`/api/fuentes`).
- [ ] Comparar nuestros contornos automáticos con las cuencas FI-UGICH/UNJu–DPRH
      1:50.000 y/o IGN.
- [ ] Tabla de antecedentes: 52 fichas DesInventar + eventos de literatura.
- [ ] Ingesta WRF-DET 4 km (PP 10M/1H, SMOIS, Freezing_level) + SMAP L4 /
      IMERG Early como índices de antecedente — fase 1 del catálogo PDF.
- [ ] Solicitudes formales: DPRH telemetría (Potrero de Yala), IGN MDT 5 m,
      SEGEMAR Carta 2366-IV, INTA Hornillos, INA-SIyAH API A5.

## Validación de negocio (de `docs/modelo-negocio-quebrada-alert.md`)

Ver [[modelo-negocio]]. Antes de cobrar:

- [ ] Entrevistar DPRH y Defensa Civil (comprador, presupuesto, exigencias;
      **qué pasa si la DPRH dice que no**).
- [ ] Segundo pagador: Vialidad, turismo, aseguradoras (valor asegurable del dato).
- [ ] BOM de estación + cotización; ancla de precio en licitaciones públicas.
- [ ] Cuantificar beneficio evitado (alud 2017: RN 9 cortada, >1.000 damnificados).
- [ ] Medir enlace de respaldo en cabecera real.
- [ ] Resolver LICENSE del código, licencias de datos, figura jurídica.
- [ ] Relevar financiamiento para el piloto.

## Endurecimiento (post-hackatón)

- [ ] Autenticación en `/api/ingesta` y `/api/respaldo` (hoy la red se confía).
- [ ] Persistencia del estado del `Motor` ya cubierta por DuckDB — evaluar
      réplicas/backups del `central.duckdb`.
- [ ] Empaquetar el nodo edge para hardware real (hoy es un proceso FastAPI
      de control, no firmware).

## Reglas

- Toda tarea nueva que cambie una decisión → actualizar [[decisiones]].
- Todo pendiente nuevo → anotarlo aquí con fecha, no en chats que se pierden.
