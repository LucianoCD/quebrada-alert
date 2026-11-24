# QuebradaAlert — reglas para agentes

Demo de red de estaciones hidrológicas edge-first para crecidas súbitas en la
Quebrada de Humahuaca. Monorepo: una app Python (`apps/api`), un tablero
(`apps/web`), datos compartidos (`docs/data/`) y memoria de equipo (`cerebro/`).

## Estructura

| Ruta | Contenido |
|---|---|
| `apps/api/quebrada/` | Paquete Python: `schemas` (contratos), `hydrology` (semáforo + Kirpich), `cuencas`, `edge/` (nodo), `backend/` (FastAPI + DuckDB), `fuentes/` (MVC de fuentes externas), `demo.py` |
| `apps/web/` | Tablero React 19 + Vite + Tailwind 4 + Leaflet |
| `apps/api/scripts/` | `preparar_geodatos.py` regenera `docs/data/` y `preparar_ilustracion.py` el mapa del landing en `apps/web/src/assets/` (requieren `.[geo]`) |
| `tests/` | pytest — núcleo y API |
| `docs/` | Docs para humanos (`api.md` = contratos); `docs/data/` = GeoJSON + relieve que sirve el backend en `/datos` |
| `cerebro/` | Memoria compartida del equipo — leer `indice.md` al empezar, actualizar `estado.md` al terminar |
| `.agents/skills/` | Skills del proyecto (restaurar con `npx skills experimental_install`) |
| `.devin/` | Config de Devin CLI y plugins del equipo |

## Comandos

```bash
pip install -e ".[dev]"          # backend + tests
(cd apps/web && npm ci && npm run build)   # tablero → apps/web/dist
python -m quebrada.demo          # levanta backend + nodos → http://127.0.0.1:8000
pytest -q && ruff check . && ruff format --check .   # verificación (= CI)
```

## Reglas

- **Idioma**: código, docs y commits en español, estilo del repo.
- **Contratos**: `schemas.py` es la fuente de verdad de mensajes; cambios
  aditivos y compatibles. El tablero no inventa semántica: ver `docs/api.md`.
- **Rutas de datos**: `cuencas.py` y `backend/app.py` resuelven `docs/data/` y
  `apps/web/dist` desde la raíz del repo (`parents[N]`); si se mueve el
  paquete hay que ajustarlos.
- **Estilo**: ruff `line-length = 120`, `select = ["E","F","I","B","UP"]`.
- **Cerebro**: antes de cambios no triviales leer `cerebro/indice.md` y las
  notas relevantes; al terminar actualizar `cerebro/estado.md` y la nota
  correspondiente si cambió una decisión o un pendiente.
- **Skill cerebro**: para analizar el vault (conexiones, huecos) usar la skill
  `cerebro` — requiere `pip install pyyaml` y corre
  `python3 .agents/skills/cerebro/scripts/vault_parser.py cerebro/ --gaps`.
- **Plugin del equipo**: `devin plugins install --local .devin/plugins/quebrada-team`
  habilita skills compartidas (`verificar`, `demo`).
