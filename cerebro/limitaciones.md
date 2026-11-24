---
tags: [riesgos, limitaciones]
actualizado: 2026-11-23
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
  reservorio lineal sin base local; los escenarios operativos son sintéticos,
  salvo `volcan_2017_cmorph` rotulado como estimación satelital (su pico de
  `6,4 mm/15 min` iguala Caine 1980, pero queda en `AMARILLO` bajo los umbrales
  ilustrativos actuales por suavizado de píxel 8 km y falta de calibración).

## Infraestructura

- **Enlace de respaldo emulado**: es un segundo canal HTTP, no LoRa real; el
  alcance en quebradas encajonadas habría que medirlo en terreno.
- **Sin autenticación**: `/api/ingesta` y `/api/respaldo` confían en la red —
  aceptable para demo local, no para producción.
- **Nodos simulados**: procesos Python con reloj acelerado (`--escala`), no
  firmware de campo.

## Datos (relevamiento 22/11/2026)

- **Sin medición pública de nivel, caudal ni turbidez** en los tributarios:
  esas variables son simuladas por necesidad, no por elección.
- **Satélite no sirve para gatilla**: latencia de 2–18 h frente a tc de 18–54
  min. Sirve para antecedente (SMAP/IMERG) y calibración histórica.
- **Red terrestre escasa**: el SMN deja ~230 km de vacío entre sus estaciones
  fuera del cañón; SNIH solo tiene Volcán y Humahuaca (ninguna en cabecera, sin
  temporada de lluvias aún).
- **Acceso institucional pendiente**: SMN SAT sin API oficial; DPRH sin portal
  público de telemetría; IGN MDT 5 m y Carta SEGEMAR 2366-IV solo por solicitud.
- **Preprint retractado**: nhess-2018-207 no usar para calibrar; preferir
  Geografska Annaler 2020 / informes DPRH.
- **Licencias no comerciales**: FABDEM (CC BY-NC-SA) y Open-Meteo gratis.

## Presentación

- El tablero v2.0 ya representa los 4 niveles del semáforo incluyendo `ROJO`
  (banner crítico, tarjeta e iconos), y `MapaTactico.jsx` está listo para
  consumir teselas `Terrain-RGB` cuando `contexto.geojson` declare `terrain`;
  sin embargo, las teselas aún no están pregeneradas en `docs/data/terrain/`,
  por lo que la vista `3D` actual solo inclina la cámara (`pitch`).
- La landing muestra un mapa ilustrado del corredor (`MapaCorredor.jsx`: relieve
  sombreado del MDE más RN 9, cauces y cuencas en SVG, generados por
  `apps/api/scripts/preparar_ilustracion.py`). Es una ilustración 2D, no la
  escena 3D R3F de la Fase 3, que sigue pendiente junto con la Fase 4 (QA visual
  completo). Los contornos no tienen validación oficial y el ETA que rotula es
  el de Kirpich, orientativo.
- El tema implementado en `apps/web/src/index.css` es claro (`#eef2f7`) en
  lugar del *Dark Mode* descrito originalmente en `docs/especificacion-ui-ux-v2.md`.
- `npm audit` reporta vulnerabilidades indirectas en dependencias de Deck.gl que
  procesan formatos externos; el impacto en la demo offline es bajo porque solo
  carga archivos estáticos locales propios en `docs/data/`.
