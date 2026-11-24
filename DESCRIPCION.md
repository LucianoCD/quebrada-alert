# Cuenca Alert — Red de alerta de crecidas

**El Problema:** En la Quebrada de Humahuaca (Jujuy), las tormentas de verano generan crecidas súbitas y flujos aluvionales ("volcanes") que llegan a la Ruta Nacional 9 en minutos. Los sistemas de monitoreo tradicionales fallan críticamente porque la misma tormenta que provoca la crecida suele derribar el enlace celular de las estaciones, dejando ciego al centro de operaciones.

**La Solución:** Cuenca Alert propone una arquitectura edge-first. Cada estación guarda sus lecturas localmente (SQLite), evalúa un semáforo de peligro por su cuenta y, si pierde conexión, emite alertas por un enlace de respaldo (LoRa). Al volver la señal, sincroniza los datos acumulados sin pérdidas ni duplicados. El backend calcula el tiempo de arribo del agua a la ruta usando la fórmula de Kirpich.
