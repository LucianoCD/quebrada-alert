---
name: verificar
description: Corre la misma verificación que CI — pytest, ruff y build del tablero
triggers:
  - user
  - model
allowed-tools:
  - read
  - grep
  - glob
  - exec
---

Verifica el proyecto igual que `.github/workflows/ci.yml`, desde la raíz del
repo:

1. `pytest -q` — tests del núcleo y la API.
2. `ruff check .` y `ruff format --check .` — estilo (line-length 120).
3. `(cd apps/web && npm ci && npm run build)` — build del tablero a `apps/web/dist`.

Reporta cada paso como OK/FALLA con la salida relevante. Si algo falla,
identifica el archivo y la causa probable antes de proponer el arreglo.
No marques la tarea como terminada si queda algún paso en rojo.
