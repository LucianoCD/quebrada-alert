---
tags: [proyecto, vision]
actualizado: 2026-11-22
---

# QuebradaAlert

Demostración de una red de estaciones hidrológicas que **sigue alertando cuando
se cae la conexión**. Caso de uso: crecidas súbitas y flujos aluvionales
("volcanes") de las microcuencas tributarias del río Grande en la Quebrada de
Humahuaca (Jujuy, Argentina).

## Propuesta

- Cada estación guarda lecturas en un **búfer SQLite local**, evalúa el
  [[glosario#semaforo|semáforo]] por su cuenta y, al volver el enlace, entrega
  lo acumulado **sin pérdidas, sin duplicados y sin alarmas tardías**.
- En corte de enlace emite paquetes de emergencia por un **enlace de respaldo**
  (emula LoRa) y activa baliza local en rojo.
- El backend (FastAPI + DuckDB) reconcilia, recalcula el semáforo y proyecta
  una **cuenta regresiva de arribo a la RN 9** (fórmula de Kirpich).
- El tablero (`apps/web`) es una consola de crisis offline con el mapa de las
  cuatro cuencas.

## Alcance

Es una **demo**: estaciones simuladas, umbrales sin calibrar, tiempo de arribo
orientativo. No emite alertas reales; las acciones del tablero son
recomendaciones para Defensa Civil, DPRH y Vialidad Nacional.

## Piezas

- [[arquitectura]] — cómo encajan nodo, backend, respaldo y tablero.
- [[decisiones]] — por qué Sparkplug B sobre HTTP, DuckDB, SQLite WAL…
- [[estado]] — avance actual.
- [[roadmap]] — qué falta.
- [[limitaciones]] — qué NO afirma el proyecto.
- [[demo-guion]] — cómo se presenta.
