---
name: demo
description: Prepara y levanta la demo completa de QuebradaAlert (backend + nodos + tablero)
triggers:
  - user
argument-hint: "[--escala N] [--puerto N]"
allowed-tools:
  - read
  - exec
---

Levanta la demo de QuebradaAlert desde la raíz del repo:

1. Asegurar dependencias: `pip install -e ".[dev]"` si el entorno es nuevo.
2. Compilar el tablero una sola vez: `(cd apps/web && npm ci && npm run build)`
   — el backend lo sirve desde `apps/web/dist`.
3. Lanzar en segundo plano: `python -m quebrada.demo` (flags opcionales:
   `--escala 60` tiempo simulado, `--puerto 8000`).
4. Confirmar que responde: `curl -s http://127.0.0.1:8000/api/estado`.
5. Informar la URL del tablero y cómo detenerlo (Ctrl+C / matar el proceso).

Notas:
- `var/` guarda la base DuckDB y los SQLite de los nodos; se recrea en cada
  corrida salvo `--conservar`.
- Los nodos simulados exponen su control en `puerto+101+i`; el backend los
  descubre vía `QUEBRADA_NODOS` (lo arma `demo.py`).
- Si el puerto 8000 está ocupado, sugerir `--puerto` distinto.
