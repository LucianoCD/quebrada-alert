---
tags: [riesgos, limitaciones]
actualizado: 2026-11-22
---

# Limitaciones conocidas

Lo que el proyecto **no** afirma. Fuente: `README.md` § Limitaciones + código.

## Modelo hidrológico

- **Umbrales sin calibrar**: no hay registro local de aludes con lluvia
  asociada; los valores del [[glosario#semaforo|semáforo]] son de ejemplo.
- **Kirpich**: desarrollado para cuencas agrícolas; describe escurrimiento de
  agua, no flujos de detritos. Los 50–120 min de arribo son mayores que los
  20–45 min citados para estos eventos. Ver [[decisiones#kirpich]].
- **Cuencas sin validar**: contornos automáticos sin contrastar con cartografía
  oficial/DPRH; la cuenca de Purmamarca (380 km²) no es una microcuenca.
- **Sensores simulados**: lluvia, nivel y turbidez salen de un modelo de
  reservorio lineal sin base local; sin perfiles de tormenta reales.

## Infraestructura

- **Enlace de respaldo emulado**: es un segundo canal HTTP, no LoRa real; el
  alcance en quebradas encajonadas habría que medirlo en terreno.
- **Sin autenticación**: `/api/ingesta` y `/api/respaldo` confían en la red —
  aceptable para demo local, no para producción.
- **Nodos simulados**: procesos Python con reloj acelerado (`--escala`), no
  firmware de campo.

## Presentación

- El tablero **nunca pasa a rojo**: el caso más extremo se comunica por el
  evento `RECUPERACION` del motor, no por el estado visual.
