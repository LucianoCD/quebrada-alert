---
tags: [estado, living]
actualizado: 2026-11-22
---

# Estado actual

> Nota viva: el agente o integrante que termina una tarea actualiza este archivo.

## Hecho

- Backend FastAPI + DuckDB con ingesta, reconciliación, motor de alertas,
  WebSocket, parte de situación y consola de crisis (`/api/simulador`).
- Nodo edge simulado con SQLite WAL, secuencia, modo isla, cola de reenvío,
  paquete de emergencia por respaldo y baliza local.
- Tablero React+Vite+Tailwind+Leaflet offline (relieve + GeoJSON en `docs/data/`).
- Geodatos generados: 4 microcuencas, cauces, puntos y contexto.
- Tests de núcleo (`tests/test_nucleo.py`) y CI en GitHub Actions.
- Reestructuración a monorepo (`apps/`, `docs/`, `cerebro/`, `.agents/`).

## En curso

- Nada bloqueante al 2026-11-22.

## Bloqueado / riesgos

- Los umbrales del semáforo no están calibrados con datos reales → ver
  [[limitaciones]].
- La demo depende de que `apps/web` esté compilado (`npm run build`) antes de
  `python -m quebrada.demo`.

## Contexto reciente

- 2026-11-22 — Se reorganizó el repo como monorepo para trabajo en equipo con
  agentes: `quebrada/` → `apps/api/quebrada/`, `frontend/` → `apps/web/`,
  `scripts/` → `apps/api/scripts/`, `data/` → `docs/data/`; se agregaron `docs/`,
  `cerebro/` (este vault), `.agents/skills/` (skill `cerebro` instalada),
  `.devin/` y `AGENTS.md`.
- 2026-11-22 — Se incorporaron dos relevamientos de fuentes de datos en `docs/`
  (verificación de campo + catálogo técnico de producción) y se integraron al
  cerebro en [[fuentes-datos]]: sin medición pública de nivel/turbidez en
  tributarios, WRF-DET como motor anticipatorio, satélite = referencia (no
  gatilla), umbrales pendientes de calibración con curvas I–D.
