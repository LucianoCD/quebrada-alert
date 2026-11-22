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
- Refactor UI/UX v2.0 en `feat/mapa-tactico-alertas-v2` (spec en
  `docs/especificacion-ui-ux-v2.md`): landing `/`, Centro de Comando
  `/monitor` con mapa MapLibre+Deck.gl a pantalla completa, lista de cuencas
  por severidad, inspector con pestañas, parte de situación en modal y
  consola de crisis en drawer (Fases 1–2 del spec).

## En curso

- Spec UI/UX v2.0: implementadas Fases 1–2 (mapa táctico, inspector,
  simulador aislado, parte modal). Pendientes Fase 3 (landing 3D R3F) y
  Fase 4 (QA de resiliencia + fallback WebGL pulido).

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
- 2026-11-22 — Se agregó `docs/modelo-negocio-quebrada-alert.md` (modelo B2G con
  canvas y FODA, hipótesis sin validar) con revisión crítica incorporada; se
  resume en [[modelo-negocio]]. Riesgo abierto: comprador único (DPRH).
- 2026-11-22 — Se implementó la spec UI/UX v2.0 (Fases 1–2) en la rama
  `feat/mapa-tactico-alertas-v2` desde un worktree aislado (había trabajo
  paralelo sin commitear de otro agente en `main`). Decisiones: `HashRouter`
  (el backend sirve estáticos sin rewrite de URLs), gráfica propia en SVG en
  vez de ECharts (bundle más liviano, semántica suficiente), `TripsLayer` de
  `@deck.gl/geo-layers` para el flujo animado de cauces, nivel de alerta solo
  por transición de `edge_local_alert` (los umbrales son de lluvia/ascenso,
  no de cm absoluto — no se inventan bandas).
