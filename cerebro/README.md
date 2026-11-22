# Cerebro — contexto global del proyecto

Este directorio es la **memoria compartida** de QuebradaAlert: todo el equipo
(humanos y agentes) lee y escribe aquí el contexto que no vive en el código.

## Reglas de uso

1. **Al empezar a trabajar**, leer `indice.md` y las notas relevantes a la tarea.
2. **Al terminar**, actualizar `estado.md` y la nota que corresponda si cambió
   una decisión, una limitación o un pendiente.
3. Las notas se enlazan con `[[wikilinks]]` y se etiquetan con `#tags`. El
   análisis estructural (conexiones, huecos, notas huérfanas) lo hace la skill
   `cerebro` (`.agents/skills/cerebro/`).
4. Hechos verificables van en `docs/` o en el código; aquí va el **por qué** y
   el **estado**: decisiones, pendientes, contexto de dominio.
5. Una nota por tema, frases cortas, fechas en ISO (`2026-11-22`).

## Cómo analizar el vault

```bash
# Opción A — paquete instalado (comando cerebro)
pip install -e .agents/skills/cerebro
cerebro cerebro/ --gaps --report cerebro_report.md

# Opción B — shim, solo requiere PyYAML
python3 .agents/skills/cerebro/scripts/vault_parser.py cerebro/ --gaps
```

Las skills del repo se restauran con `npx skills experimental_install` (ver
`skills-lock.json`).
