---
tags: [equipo, proceso]
actualizado: 2026-11-22
---

# Cómo trabajamos en equipo

## Reglas de oro

1. **Leer antes de escribir**: `AGENTS.md` (raíz) + `cerebro/indice.md` al
   empezar; este vault se actualiza al terminar.
2. **Verificar antes de entregar**: `pytest -q`, `ruff check .`,
   `ruff format --check .` y `npm run build` en `apps/web` — lo mismo que corre
   CI (`.github/workflows/ci.yml`).
3. **Una decisión, una nota**: si se cambia una decisión técnica, se actualiza
   [[decisiones]]; si cambia el alcance, [[proyecto]] o [[roadmap]].
4. **Commits pequeños** con mensaje en español, estilo del repo (`git log`).

## Herramientas del repo

- `apps/api` — paquete Python `quebrada` (backend + edge + núcleo).
- `apps/web` — tablero React+Vite.
- `docs/data/` — GeoJSON y relieve que consume el backend/tablero.
- `apps/api/scripts/` — `preparar_geodatos.py` regenera `docs/data/` (requiere `.[geo]`).
- `tests/` — pytest del núcleo y de la API.
- `docs/` — documentación para humanos.
- `cerebro/` — memoria compartida (este vault).
- `.agents/skills/` — skills del proyecto (incluida `cerebro`); se restauran
  con `npx skills experimental_install`.
- `.devin/` — config de Devin CLI y plugins del equipo.

## Agentes

- `AGENTS.md` en la raíz es el punto de entrada para cualquier agente.
- Skill `cerebro`: analisa este vault (conexiones, huecos, notas huérfanas).
- Plugin local `quebrada-team` (`.devin/plugins/`): instalar con
  `devin plugins install --local .devin/plugins/quebrada-team`.
