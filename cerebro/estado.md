---
tags: [estado, living]
actualizado: 2026-11-23
---

# Estado actual

> Nota viva: el agente o integrante que termina una tarea actualiza este archivo.

## Hecho

- Backend FastAPI + DuckDB con ingesta, reconciliación, motor de alertas,
  WebSocket, parte de situación y consola de crisis (`/api/simulador`).
- Nodo edge simulado con SQLite WAL, secuencia, modo isla, cola de reenvío,
  paquete de emergencia por respaldo y baliza local.
- Tablero React+Vite+Tailwind+MapLibre+Deck.gl offline (relieve + GeoJSON en `docs/data/`).
- Geodatos generados: 4 microcuencas, cauces, puntos y contexto.
- Tests de núcleo (`tests/test_nucleo.py`) y CI en GitHub Actions.
- Reestructuración a monorepo (`apps/`, `docs/`, `cerebro/`, `.agents/`).
- Refactor UI/UX v2.0 mergeado a `main` (spec en
  `docs/especificacion-ui-ux-v2.md`): landing `/`, Centro de Comando
  `/monitor` con mapa MapLibre+Deck.gl a pantalla completa, lista de cuencas
  por severidad, inspector con pestañas, parte de situación en modal y
  consola de crisis en drawer (Fases 1–2 del spec).
- Ingesta periódica de fuentes externas en MVC
  (`quebrada/fuentes`: controller–service–repository): SNIH 280049/10040 +
  Open-Meteo forecast/archive; endpoints `/api/fuentes*`; tablas
  `fuente_lectura` / `fuente_sincronizacion` (capa de referencia, sin mezclar
  con nodos), upsert de pronósticos en conflicto y backoff exponencial ante
  errores (PR #9 + endurecimiento). Ver [[fuentes-datos]] y `docs/api.md`.
- Suite de pruebas de frontend (Vitest + Testing Library) y verificación E2E
  offline (`tests/test_e2e_tablero.py`) integradas en CI (`.github/workflows/ci.yml`).

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

- 2026-11-22 — Se redactó `docs/estudio_viabilidad_foda.md`: viabilidad + FODA
  del prototipo, propuesta de valor B2G, gap vs *De Prototipo a Piloto*, y
  encaje complementario con la propuesta de TF FI-UNJu (CAFI 085/22).
- 2026-11-22 — Se reorganizó el repo como monorepo para trabajo en equipo con
  agentes: `quebrada/` → `apps/api/quebrada/`, `frontend/` → `apps/web/`,
  `scripts/` → `apps/api/scripts/`, `data/` → `docs/data/`; se agregaron `docs/`,
  `cerebro/` (este vault), `.agents/skills/` (skills `cerebro`,
  `ponytail-mvp-audit`, `quebrada-fuentes-y-geodatos`,
  `quebrada-nucleo-edge-y-motor`, `quebrada-operacion-demo-y-verificacion`,
  `quebrada-tablero-tactico-y-3d`), `.devin/` y `AGENTS.md`.
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
- 2026-11-23 — Se integró el PR #9 (Issue #4, `flopy77`), se resolvieron los
  Issues #5 (fixes StrictMode/WebGL, centro de mapa, severidad, contrastes,
  accesibilidad, backoff WS, capa `/api/fuentes` y escenario `volcan_2017_cmorph`
  en UI) y #7 (Vitest en `apps/web`, E2E offline en `tests/test_e2e_tablero.py`
  y CI), y se corrigieron hallazgos de auditoría: retención de episodios hasta
  `arribo_estimado + 5 min` (A1), activación por pico recuperado con onda en
  camino (A2), uso de `umbrales_para(basin_id)` (A3), parte coherente con
  emergencias LoRa (M1), reemisión tras volver a verde en corte (M2),
  persistencia `nodos_meta` en DuckDB (M3), actualización de pronósticos (M4)
  y backoff exponencial en `FuentesScheduler` (ver [[decisiones]]).
