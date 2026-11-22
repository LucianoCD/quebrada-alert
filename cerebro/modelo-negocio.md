---
tags: [negocio, modelo, b2g, validacion]
actualizado: 2026-11-22
---

# Modelo de negocio

Propuesta: **alerta temprana como servicio (B2G) con núcleo abierto** — se
cobra por cuenca monitoreada y año, no por hardware ni licencia. Documento
completo con Canvas y FODA en `docs/modelo-negocio-quebrada-alert.md`.

## Puntos clave

- **Componentes de ingreso**: pago único por despliegue, contrato anual de
  operación y mantenimiento por cuenca (recurrente principal), integración vía
  API, proyectos de calibración, fondos para el piloto.
- **Etapas**: demo → piloto en una cuenca (sin alertar a población, en paralelo
  con el sistema oficial) → servicio en las 4 cuencas → réplica en otros
  corredores andinos.
- **Por qué B2G**: el valor está en el software (isla, dedup, sin alarmas
  tardías) y la decisión de cortar/evacuar es del Estado; no hay venta posible
  a vecinos ni SaaS puro sin estación propia.

## Estado de validación

Todo lo comercial es **hipótesis sin validar** (sin entrevistas, cotizaciones
ni cartas de intención). Riesgo estratégico abierto: **concentración en un
único comprador** (DPRH/Defensa Civil) con ciclo de compra largo.

## Pendientes críticos antes de cobrar

- Licencias de datos no comerciales (Open-Meteo, FABDEM) → plan pago o
  self-host; WRF-SMN ya es CC BY 2.5.
- LICENSE del código sin definir (el repo no tiene archivo de licencia).
- Ingesta sin autenticación.
- Hardware inexistente (nodo simulado; falta BOM y costo unitario).
- Figura jurídica para contratar con el Estado.
- Ancla de precios vía licitaciones públicas históricas (sin inventar montos).
- Piloto debe **alimentar la cadena de la DPRH**, no competir con ella.

Ver [[proyecto]], [[decisiones]], [[fuentes-datos]], [[roadmap]].
