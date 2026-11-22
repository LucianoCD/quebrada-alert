---
tags: [datos, fuentes, investigacion]
actualizado: 2026-11-22
---

# Fuentes de datos

Dos relevamientos en `docs/` alimentan las decisiones de datos del proyecto:

- `docs/fuentes_datos_quebrada_alert.md` — relevamiento de campo (22/11/2026):
  cada fuente marcada como **probada** en vivo o solo **leída**.
- `docs/Fuentes de Datos para QuebradaAlert.pdf` — catálogo técnico de
  producción (8 pág.): pila de 4 pilares, matriz de licencias, brechas
  institucionales y hoja de ruta en 3 fases.

## Lo esencial

- **No hay mediciones públicas de nivel, caudal ni turbidez en tributarios** →
  siguen simulados. Ver [[limitaciones]].
- **Lluvia medida**: SNIH Volcán (280049, desde jun-2026, sin tormentas aún) y
  Humahuaca (10040, máx 18,5 mm). Ninguna en cabecera; no calibran umbrales.
- **Mejor evento real**: alud de Volcán 10/1/2017 — CMORPH da 48,6 mm sobre la
  cuenca (pico 25,6 mm/h a las 13 UTC). Candidato a escenario "Volcán 2017".
- **Restricción física**: tc Kirpich de 18–54 min en subcuencas laterales vs
  latencia satelital de 2–18 h → el satélite calibra y anticipa, **no gatilla**.
  Ver [[decisiones]].
- **Motor anticipatorio**: WRF-DET 4 km del SMN en AWS Open Data
  (`s3://smn-ar-wrf`, sin credenciales): PP cada 10 min/1 h, SMOIS y
  Freezing_level, 2 ciclos/día hasta +72 h.
- **Humedad antecedente**: SMAP L4 (~2 h) + IMERG Early (~4 h) para ajustar
  umbrales por saturación previa (ventana 3–5 días).
- **Umbrales**: sin calibrar localmente; curvas de referencia Guzzetti 2008 y
  Caine 1980 + análogos semiáridos (Mendoza, Quebrada Amarilla, Macul) → regla
  condicionada por humedad del suelo e isoterma 0 °C.
- **Mapa offline**: ya resuelto con estáticos propios en `docs/data/`;
  PMTiles/Protomaps es la vía si se escala a móvil.
- **Brechas institucionales**: SMN SAT sin API oficial; DPRH sin portal público
  (6 estaciones operativas + 9 en gestión); IGN MDT 5 m/VANT y Carta SEGEMAR
  2366-IV solo por solicitud formal.

## Precauciones

- El preprint nhess-2018-207 (Esper Angillieri 2018) está **retractado** — usar
  Geografska Annaler 2020 o informes DPRH/SEGEMAR.
- Open-Meteo gratis y FABDEM son **solo no comerciales**.
- La hora de llegada de datos SNIH y su zona horaria no están confirmadas.

Ver [[arquitectura]], [[decisiones]], [[limitaciones]], [[roadmap]].
