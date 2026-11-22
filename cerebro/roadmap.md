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

## Endurecimiento (post-hackatón)

- [ ] Autenticación en `/api/ingesta` y `/api/respaldo` (hoy la red se confía).
- [ ] Persistencia del estado del `Motor` ya cubierta por DuckDB — evaluar
      réplicas/backups del `central.duckdb`.
- [ ] Empaquetar el nodo edge para hardware real (hoy es un proceso FastAPI
      de control, no firmware).

## Reglas

- Toda tarea nueva que cambie una decisión → actualizar [[decisiones]].
- Todo pendiente nuevo → anotarlo aquí con fecha, no en chats que se pierden.
