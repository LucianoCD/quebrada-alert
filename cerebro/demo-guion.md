---
tags: [presentacion, demo]
actualizado: 2026-11-22
---

# Guion de la demo (3 minutos)

Ver `README.md` § Guion de la demo para la versión completa.

1. **Autonomía** — Wi-Fi apagado: cuatro cuencas en verde transmitiendo.
2. **Tormenta y corte** — *Tormenta convectiva* + *Cortar enlace celular* en
   Volcán: el nodo pasa a `ISLAND_MODE` y sube el contador del búfer SQLite.
3. **Decisión en el borde** — el registro muestra la alerta autónoma; el
   paquete de emergencia llega por el respaldo: la cuenca pasa a naranja y
   luego a rojo con la cuenta regresiva a la RN 9.
4. **Recuperación** — *Restablecer enlace celular*: el búfer se vacía, la
   serie se completa (barras violetas), "lecturas faltantes" queda en 0 y no
   aparecen alertas nuevas.

**Variante**: cortar también el respaldo LoRa antes de la tormenta y restablecer
todo al volver a verde. El tablero nunca pasa a rojo, pero `RECUPERACION`
informa que el nodo llegó a rojo durante el corte.

## Mensajes clave

- La estación **decide sola** (semáforo local) aunque no haya red.
- La recuperación **no genera alarmas fantasma**: histórico ≠ en vivo.
- La cuenta regresiva usa tiempo de arribo estimado (Kirpich) — con sus
  [[limitaciones#modelo-hidrologico|limitaciones declaradas]].
