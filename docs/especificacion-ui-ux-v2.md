# Especificación de Arquitectura UI/UX y Frontend: QuebradaAlert v2.0

**Rol:** Arquitectura UI/UX y Sistemas Interactivos  
**Dominio:** Sistema de Alerta Temprana (SAT) de Crecidas Repentinas y Aludes — Cuencas Tributarias del Río Grande (Quebrada de Humahuaca, Jujuy, Argentina)  
**Cuencas monitoreadas:** Volcán (Arroyo del Medio), Tumbaya (Río Tumbaya Grande), Purmamarca (Río Purmamarca) y Tilcara (Río Huasamayo)  
**Versión:** 2.0 (Refactorización Integral + Landing Page 3D)

---

## 1. Diagnóstico del Sistema Actual (Auditoría del Video)

### 1.1 Fortalezas Técnicas a Preservar
El prototipo actual resuelve problemas de ingeniería críticos que deben convertirse en protagonistas de la experiencia de usuario y no quedar ocultos en logs técnicos:
- **Resiliencia en Modo Isla (`ISLAND_MODE`):** Capacidad del nodo en campo de seguir operando y emitir alertas por respaldo **LoRa** cuando cae el enlace celular (`NDEATH`).
- **Recuperación sin Huecos (SQLite -> DuckDB):** Al restablecerse el enlace celular, el nodo vacía su búfer local (por ejemplo, de `94` a `0` lecturas) y reconstruye la serie histórica en el servidor sin disparar falsas alertas tardías.
- **Cálculo de ETA a Puntos Críticos:** Estimación de tiempo de arribo de la onda de crecida hacia la **Ruta Nacional 9 (RN 9)** y recomendación explícita de acción preventiva.
- **Trazabilidad y Transparencia Operativa:** Distinción entre datos simulados/sin calibrar y rol institucional (Defensa Civil, DPRH y Vialidad Nacional).

### 1.2 Problemas UI/UX Detectados
1. **Compresión espacial del mapa:** El layout fijo de 3 columnas relega el mapa a menos del 40% del ancho de pantalla, impidiendo evaluar rápidamente la relación topográfica entre cabeceras de cuenca, cauces y cruces de la RN 9.
2. **Contaminación entre Operación y Simulación:** La *"Consola de Crisis / Simulador"* ocupa permanentemente un bloque central en la columna derecha, compitiendo visualmente con la telemetría crítica y generando riesgo cognitivo en un entorno real.
3. **Salida de reporte sin formato:** El botón *"Parte de situación"* navega a una vista de texto plano crudo (`/api/parte/CUENCA_HUASAMAYO`), rompiendo el contexto de la aplicación y dificultando su distribución rápida.
4. **Mapa 2D pasivo:** Aunque los polígonos cambian de color (verde, amarillo, rojo), no existen animaciones de dirección de escorrentía, pulsos de alerta sobre el cruce de la RN 9, ni visualización de relieve 3D para entender la pendiente y energía de las quebradas.
5. **Gráfica hidrológica comprimida:** La serie reconstruida en DuckDB carece de bandas visuales de umbrales (Amarillo/Naranja/Rojo), tooltips interactivos y diferenciación inmediata de pendientes de ascenso ($\Delta h / \Delta t$).
6. **Ausencia de portal de entrada:** No existe una Landing Page institucional/interactiva que explique cómo ocurren las crecidas en la Quebrada ni demuestre visualmente la arquitectura de alerta temprana.

---

## 2. Referencias Modernas y Patrones Adoptados (2025–2026)

La propuesta combina cinco referentes líderes en geoespacial, gestión de crisis y visualización hidrológica web:

| Referente | Qué adoptamos en QuebradaAlert v2.0 |
| :--- | :--- |
| **Google Flood Hub** | Paneles de estaciones hidrométricas (*Gauge Panels*) con bandas horizontales de severidad, visualización clara de zonas de inundación y lenguaje de riesgo directo y accionable. |
| **Watch Duty** | Paradigma **Map-First (100% viewport)** en emergencias, paneles flotantes colapsables de mínima carga cognitiva, ordenamiento automático por severidad y transparencia total de timestamps y estado de fuente. |
| **Palantir Blueprint & Linear Dark UI** | Estética *Mission-Critical Dark Mode* de alto contraste sin fatiga visual, tipografía monoespaciada tabular (`tabular-nums`) para telemetría en vivo y separación estricta de modos operativos vs. simulación. |
| **MapLibre GL JS 3D Terrain & HazardSim** | Uso del DEM Copernicus GLO-30 codificado en **Terrain-RGB** para renderizado 3D real en GPU (100% compatible con servidor local/offline), combinado con capas animadas de propagación de onda sobre la grilla topográfica. |
| **Hydro3DJS & React Three Fiber (R3F)** | Escenas 3D interactivas en la Landing Page con simulación de lluvia convectiva, dinámica de fluidos/sedimentos mediante shaders GLSL y representación de infraestructura crítica (RN 9, puentes y nodos IoT). |

---

## 3. Arquitectura de Información y Mapa de Rutas

La aplicación se divide en una capa pública/divulgativa y un centro de comando operativo desacoplado:

```text
/                         -> Landing Page Inmersiva con Simulador 3D de Crecidas (Scrollytelling)
/monitor                  -> Centro de Comando Geoespacial (Mapa 100% viewport + Alertas en Vivo)
/monitor?cuenca=volcan    -> Deep-link con foco automático y drawer abierto en una cuenca específica
/reportes/parte/:cuencaId -> Vista formateada del Parte de Situación (Imprimir / PDF / Copiar WhatsApp)
```

> **Regla de Aislamiento de Entornos:** El simulador de tormentas y cortes de red ya no vive fijo en la interfaz operativa. Se activa exclusivamente mediante un interruptor explícito `[MODO SIMULADOR]` en la barra superior o mediante un parámetro de entorno, desplegando un borde perimetral ámbar sutil y un *Bottom Drawer* dedicado para evitar cualquier confusión con datos reales.

---

## 4. Especificación de la Landing Page con Modelos 3D Animados (`/`)

### 4.1 Dirección de Arte: *"Andean Topographic Tech"*
- **Identidad visual:** Superficies oscuras inspiradas en basalto y pizarra nocturna (`#080C14`), líneas de curvas de nivel topográficas sutiles en el fondo, acentos hidrológicos en cian (`#06B6D4`) y paleta semántica de alerta altamente reconocible.
- **Objetivo UX:** Permitir que autoridades (Defensa Civil, Vialidad, DPRH), investigadores y ciudadanos entiendan en menos de 60 segundos **cómo se forma una crecida repentina en la Quebrada** y **por qué la arquitectura edge/LoRa salva minutos críticos**.

### 4.2 Estructura por Secciones

#### Sección 1: Hero Interactivo con Maqueta 3D Animada de Cuenca
- **Lienzo 3D (65% derecha en desktop / fondo superior interactivo en mobile):**
  - **Modelo 3D del Terreno:** Malla generada a partir del DEM real de la cuenca del **Arroyo del Medio (Volcán)** o un corte representativo de la Quebrada, mostrando cabecera de alta montaña, garganta/cauce, cono de deyección, el trazado de la **RN 9** con puente/badén y la estación hidrométrica en cabecera (`EST-VOLCAN-CAB01`).
  - **Simulación Animada de Crecidas (Controlable por el usuario):**
    - **Selector interactivo de escenario (4 estados):**
      1. `Estiaje / Calma` (Agua cristalina mínima, cielo despejado, enlace celular activo en verde).
      2. `Lluvia Moderada` (Nubes volumétricas ligeras, lluvia de partículas suaves, aumento gradual del tirante de agua).
      3. `Tormenta Convectiva` (Nube densa en cabecera, lluvia intensa, saturación del suelo con cambio de rugosidad/oscurecimiento del terreno, descenso de onda rápida).
      4. `Crecida Crítica / Alud` (Flujo hiperconcentrado con textura animada de agua + sedimento/barro en shader GLSL, desborde sobre el cruce de RN 9, corte visual de torre celular y activación de pulsos de radio **LoRa** en color ámbar desde el nodo).
    - **Slider de línea de tiempo ($t = 0\text{ min}$ a $t = 30\text{ min}$):** Permite arrastrar manualmente el avance del frente de onda por el cauce y ver sincronizadamente un HUD flotante con:
      - Nivel del cauce ($\text{cm}$)
      - Precipitación acumulada ($\text{mm}/15\text{ min}$)
      - ETA estimado a RN 9 ($\text{min}$)
      - Estado del semáforo (`VERDE` -> `AMARILLO` -> `NARANJA` -> `ROJO`)
- **Columna Editorial (35% izquierda):**
  - Eyebrow: `SAT · Quebrada de Humahuaca · Jujuy`
  - Titular (H1): *"Minutos de ventaja ante crecidas repentinas en la Quebrada."*
  - Subtítulo claro explicando el monitoreo de las 4 cuencas críticas sobre la RN 9.
  - CTAs:
    - Primario: **Abrir Centro de Monitoreo** (`/monitor`)
    - Secundario: **Explorar Simulación 3D** (hace scroll suave al modo interactivo/narrativo)

#### Sección 2: Scrollytelling Hidrológico y de Resiliencia (4 Actos Sincronizados con Cámara 3D)
A medida que el usuario hace scroll, la cámara 3D realiza transiciones cinematográficas suaves (*camera splines*) sobre la misma escena WebGL sin recargar assets:
1. **Acto I — Detección en Cabecera:** Zoom a la estación de montaña. Animación de pluviómetro y sensor ultrasónico midiendo $\Delta h$.
2. **Acto II — Apagón Celular y Modo Isla:** La tormenta tumba la conectividad 4G (`NDEATH`). El modelo 3D apaga el enlace celular, enciende la baliza local en el nodo y emite anillos de radiofrecuencia **LoRa** de largo alcance mientras un contador visual muestra las lecturas acumulándose en el búfer SQLite.
3. **Acto III — Avance de Onda hacia RN 9:** Plano aéreo siguiendo el frente de agua/sedimento bajando por la pendiente con una línea proyectada de ETA hacia el cruce vial.
4. **Acto IV — Reconstrucción Sin Huecos (DuckDB):** Vuelve la señal celular; partículas de datos viajan desde el nodo hacia el servidor reconstruyendo la curva completa sin pérdida de información ni alertas duplicadas.

#### Sección 3: Monitor Vivo de las 4 Cuencas (Bridge hacia la App)
- Cuatro tarjetas en tiempo real conectadas al backend local (Volcán, Tumbaya, Purmamarca, Tilcara) mostrando el estado actual del semáforo, nivel del río y botón directo para abrir cada cuenca en el Centro de Comando.

#### Sección 4: Marco Institucional y Aviso de Calibración
- Bloque transparente sobre protocolos de coordinación con **Defensa Civil, DPRH y Vialidad Nacional**, aclarando que la herramienta provee soporte a la decisión y los umbrales pueden encontrarse en fase de calibración/demostración.

### 4.3 Arquitectura Técnica 3D y Presupuesto de Rendimiento
- **Motor:** `@react-three/fiber` (R3F) + `@react-three/drei` + `three`.
- **Geometría de Terreno:** DEM Copernicus GLO-30 procesado en Blender/QGIS a malla optimizada (`~40,000` a `80,000` triángulos) exportada en `.glb` con compresión **Draco** y texturas **KTX2**.
- **Shader de Crecida (GLSL):**
  - Plano/malla de cauce que utiliza un mapa de flujo (*flow map*) y ruido Simplex/Perlin desplazado en el tiempo para simular turbulencia y frente de avance.
  - Interpolación de color y materialidad según caudal: de azul translúcido (`VERDE`) a marrón arcilloso turbulento con espuma en los bordes (`ROJO`) para reflejar fielmente las crecidas aluvionales del NOA.
- **Lluvia:** `InstancedMesh` con hasta `1,500` gotas (una sola *draw call*).
- **Degradación Elegante (Progressive Enhancement):**
  - Nivel Alto (Desktop GPU): 3D completo + postprocesado sutil (bloom en balizas/alertas) + `dpr={[1, 1.5]}`.
  - Nivel Medio (Mobile moderno): Sin postprocesado, menor densidad de partículas, `dpr={1}`.
  - Nivel Bajo / `prefers-reduced-motion`: Vista topográfica isométrica interactiva en Canvas 2D / secuencia de frames controlable por slider.
  - Uso obligatorio de `IntersectionObserver` para pausar el bucle `useFrame` cuando el canvas 3D sale del viewport.

---

## 5. Refactorización de la Interfaz Operativa (`/monitor`)

### 5.1 Paradigma de Layout: *Tactical Map-First*
El mapa ocupa el **100% del viewport** (`100vw` $\times$ `100vh`). Todos los paneles son superficies flotantes (*floating glass panels*) con `backdrop-filter: blur(14px)`, opacidad controlada (`rgba(11, 17, 30, 0.86)`) y borde fino (`1px solid rgba(148, 163, 184, 0.16)`), colapsables mediante atajos de teclado o botones dedicados.

```text
+-----------------------------------------------------------------------------------+
| [Logo] QuebradaAlert | [V:●] [Tu:●] [P:●] [Ti:●] | [MODO: VIVO/SIM] | [🔊] [Srv]  | <- Top Bar (48px)
+-----------------------------------------------------------------------------------+
| +-------------------+  +---------------------------------------+                  |
| | [!] ALERTA ROJA: VOLCÁN · ETA RN 9: 08:42 · Corte Preventivo | [Parte] [Silenc] | <- Alert Banner
| |   CUENCAS (4)     |  +---------------------------------------+                  |    (Solo si > VERDE)
| |-------------------|                                          +----------------+ |
| | [VOLCÁN]    ROJO  |                                          | INSPECTOR      | |
| | ETA RN 9: 9 min   |           MAPA INTERACTIVO 2D/3D         | Volcán         | |
| | 41.7cm | 3.6 mm   |       (MapLibre Terrain-RGB + Deck.gl)   | [Ops][Red][Log]| |
| | [sparkline]       |                                          |                | |
| |-------------------|         * Polígonos dinámicos            | Recomendación  | |
| | [TUMBAYA]  VERDE  |         * Cauces con flujo animado       | [Emitir Parte] | |
| |-------------------|         * Radar pulsante en cruce RN 9   |                | |
| | [PURMAMARCA] VRD  |         * Nodos IoT (Celular / LoRa)     | Gráfica DuckDB | |
| |-------------------|                                          | + Bandas Umbral| |
| | [TILCARA]  VERDE  |   [2D|3D] [Capas] [Centrar] [Medir]      |                | |
| +-------------------+                                          +----------------+ |
+-----------------------------------------------------------------------------------+
| [^] CONSOLA DE CRISIS / SIMULADOR (Drawer colapsable - visible solo en MODO SIM)  |
+-----------------------------------------------------------------------------------+
```

### 5.2 Sistema de Mapa Generador y Visualizador de Alertas de Crecidas

#### Motor Cartográfico (Offline-First / Servidor Local)
- **MapLibre GL JS** renderizando teselas locales (`.pmtiles` o servidor local de tiles) de:
  - Base topográfica oscura + sombreado de relieve (*hillshade*).
  - **DEM Copernicus GLO-30 en formato Terrain-RGB** para activar el relieve 3D real (`map.setTerrain({ source: 'copernicus-dem', exaggeration: 1.5 })`).
  - Red vial destacando la **RN 9** y trazado urbano de Volcán, Tumbaya, Purmamarca y Tilcara.
- **Deck.gl** superpuesto (`MapboxOverlay`) para capas de animación de alta frecuencia a 60 fps.

#### Capas Dinámicas de Alerta en el Mapa
1. **Capa de Polígonos de Cuenca:**
   - En `VERDE`: Contorno sutil traslúcido (`12%` relleno) para no tapar el relieve.
   - En `AMARILLO` / `NARANJA` / `ROJO`: Incremento de saturación en bordes, sombreado interior térmico y etiqueta flotante con el nombre de la cuenca y tasa de lluvia.
2. **Capa de Flujo Hidrológico Animado (`TripsLayer` / Shader de Cauce):**
   - Muestra los 4 cauces tributarios desembocando en el Río Grande.
   - **Codificación dinámica:** La velocidad de las partículas animadas y el grosor del cauce escalan en tiempo real con el nivel del río ($\text{cm}$) y la tasa de ascenso ($\Delta h$).
3. **Capa de Impacto Vial y Generación de Alertas en RN 9:**
   - Cada intersección crítica de arroyo/río con la RN 9 cuenta con un **Geo-Fence / Punto de Control Vial**.
   - Cuando una cuenca supera el umbral `NARANJA` o `ROJO`, el mapa genera automáticamente:
     - Un **anillo radar pulsante** sobre el cruce de la RN 9.
     - Un **Pin de Alerta Flotante** anclado a la coordenada del puente/cruce: `CORTE PREVENTIVO RN 9 · ETA 9 min`.
     - Resaltado en rojo intermitente del segmento vial comprometido (buffer de $\pm 1.5\text{ km}$ alrededor del cruce).
4. **Capa de Estaciones / Nodos IoT:**
   - Marcador con doble anillo: el núcleo indica el nivel de alerta hidrológica y el halo exterior indica el estado de telemetría:
     - Cian continuo: `ONLINE` (Enlace celular activo).
     - Ámbar parpadeante: `ISLAND_MODE` (Sin celular, recibiendo paquetes por respaldo **LoRa**).
     - Gris tachado: `NDEATH` (Sin enlace primario ni respaldo).
5. **Controles Geoespaciales Esenciales:**
   - **Toggle `2D` / `3D`:** Permite alternar entre vista ortogonal (ideal para medir y comparar) y vista inclinada 3D (`pitch: 60`) para evaluar pendientes. Incluye indicador visible de exageración vertical (`Relieve 1.5x`).
   - **Selector de Capas:** Activar/desactivar Relieve 3D, Radar de Lluvia simulada/estimada, Cuencas, Nodos IoT y Puntos Críticos RN 9.
   - **Botón "Enfocar Crisis":** Ejecuta un `flyTo` suave hacia la cuenca de mayor severidad activa sin secuestrar la cámara si el usuario está explorando manualmente.

### 5.3 Flujo de Escalamiento de Alertas (Crisis UX)

El sistema evita la fatiga de alertas diferenciando claramente el ruido visual según severidad:

| Nivel | Disparador / Significado | Comportamiento en Mapa | Comportamiento en UI y Audio |
| :--- | :--- | :--- | :--- |
| **VERDE** | Monitoreo de rutina | Polígonos sutiles, flujo laminar lento. | Interfaz calma, sin banners. |
| **AMARILLO** | Vigilancia / Descenso controlado | Borde ámbar iluminado en cuenca y cauce. | Tarjeta de cuenca asciende al top de la lista. Toast informativo no intrusivo. |
| **NARANJA** | Pre-alerta / Crecida en desarrollo | Flujo acelerado hacia RN 9, pulso moderado en nodo y cruce vial. | Aparece **Tactical Alert Banner** superior con ETA y recomendación. Aviso sonoro breve (1 pulso). |
| **ROJO** | Emergencia / Riesgo inminente RN 9 | Radar pulsante de alta prioridad en cruce RN 9, segmento vial en rojo, enfoque sugerido. | Banner rojo de alto contraste con contador regresivo de ETA, botón directo **"Emitir Parte de Situación"** y alerta acústica repetitiva silenciable (`[Silenciar]`). |

### 5.4 Refactorización de Paneles y Componentes

#### A. Panel Izquierdo: Lista Inteligente de Cuencas (300px)
- **Ordenamiento automático:** Las cuencas en `ROJO` y `NARANJA` suben automáticamente a la primera posición con animación de reordenamiento suave.
- **Anatomía de la Tarjeta de Cuenca:**
  - *Fila 1:* Nombre de la localidad + Río + Badge de estado (con ícono geométrico redundante para accesibilidad).
  - *Fila 2 (Solo en alerta):* Pill destacada `ETA RN 9: 9 min` con cuenta regresiva en vivo.
  - *Fila 3 (KPIs tabulares):* Nivel del cauce (`41.7 cm` + flecha de tendencia $\uparrow +14.2\text{ cm}$) y Lluvia (`3.61 mm/15m`).
  - *Fila 4:* Micro-sparkline de nivel de los últimos 30 minutos con línea punteada de umbral crítico.
  - *Fila 5 (Footer técnico):* Estado de enlace (`Celular` / `LoRa Emergencia` / `Offline`), indicador de búfer pendiente si $> 0$, y batería (`91.5%`).

#### B. Panel Derecho: Inspector Contextual de Cuenca (400px–440px)
Se organiza en **3 pestañas limpias** para eliminar el scroll infinito del diseño original:

1. **Pestaña `Hidrología` (Vista por defecto):**
   - **Tarjeta de Acción Recomendada:** Lenguaje directo y sin ambigüedades (ejemplo: *"Recomendar corte preventivo de la RN 9 en Volcán y evacuación de zonas bajas"*), metadatos de distancia (`5.2 km a RN 9`) y botón prominente **"Generar Parte de Situación"**.
   - **Gráfica Serie Reconstruida (DuckDB) — Rediseño Completo:**
     - Motor: **Apache ECharts** (soporte nativo para zoom, tooltips sincronizados y streaming).
     - Eje Y izquierdo: Precipitación ($\text{mm}/15\text{ min}$) en barras; **distinción visual clara** entre barras de *telemetría en vivo* (cian sólido) y *recuperadas del búfer SQLite* (violeta con patrón rayado diagonal) para hacer evidente la integridad de datos tras un `ISLAND_MODE`.
     - Eje Y derecho: Nivel del cauce ($\text{cm}$) en línea suave con área degradada.
     - **Bandas horizontales de umbral (MarkArea):** Franjas translúcidas de fondo marcando los niveles `AMARILLO`, `NARANJA` y `ROJO` para entender de un vistazo qué tan cerca está el río del desborde.
2. **Pestaña `Nodo y Red`:**
   - Indicadores de estado de hardware: `Estado (ONLINE / ISLAND_MODE)`, `Cola SQLite (ej. 94 -> 0 con barra de progreso de sincronización)`, `Baliza local (ACTIVA / APAGADA)`, voltaje/batería.
   - **Terminal del Nodo:** Consola monoespaciada con búsqueda, filtro y botón de copiar.
3. **Pestaña `Eventos`:**
   - Bitácora cronológica filtrable por tipo (`Alertas`, `Conectividad`, `Recuperación`).
   - Hacer clic en un evento (por ejemplo, `18:54:11 ALERTA ROJA`) resalta ese instante exacto en la gráfica de DuckDB.

#### C. Visor Oficial de "Parte de Situación" (Reemplazo del texto plano)
Al presionar *"Generar Parte de Situación"*, se abre un **Modal / Vista Dedicada** (en lugar de una pestaña `text/plain` cruda) que consume el mismo endpoint `/api/parte/:cuencaId` (idealmente enriquecido en JSON) y presenta:
- Encabezado formal con sello de tiempo UTC-3 (Argentina), identificador de cuenca, nivel de alerta y bandera de advertencia si los datos son simulados.
- Resumen ejecutivo en tabla: Origen del dato, Lluvia ($15\text{ min}$, $60\text{ min}$, $72\text{ h}$), Nivel del cauce y tasa de ascenso, ETA a RN 9, Recomendación operativa.
- Últimos eventos críticos relevantes.
- **Acciones en un clic:**
  - `Copiar formato WhatsApp / Telegram` (texto limpio con emojis semánticos listo para grupos de Defensa Civil).
  - `Descargar PDF Oficial` (mediante `@media print` optimizado).
  - `Ver JSON / TXT crudo` (para interoperabilidad técnica).

#### D. Drawer Inferior: Consola de Crisis y Simulador (Aislado)
Visible solo cuando `MODO SIMULADOR` está activado. Incluye:
- **Presets de Demostración en 1 clic:**
  - *Escenario A: Tormenta Convectiva + Corte Celular* (reproduce automáticamente la demo del video: escalamiento por LoRa, `ISLAND_MODE`, llenado de SQLite y posterior reconexión con recuperación en DuckDB).
  - *Escenario B: Suelo Saturado (72h) + Lluvia Moderada*.
  - *Reset Total (Todas las cuencas a VERDE)*.
- **Controles manuales granulares:** Selector de estación objetivo (`EST-VOLCAN-CAB01`, etc.), botones de intensidad (`Sin lluvia`, `Llovizna`, `Tormenta moderada`, `Tormenta convectiva`), toggles de red (`Cortar enlace celular`, `Cortar respaldo LoRa`) y toggle de condición antecedente (`Suelo saturado 35 mm en 72h`).

---

## 6. Sistema de Diseño (Design Tokens y Accesibilidad)

### 6.1 Paleta de Colores (Dark Mode Operativo)

| Token | Valor Hex | Uso |
| :--- | :--- | :--- |
| `--bg-canvas` | `#080C14` | Fondo base de Landing y respaldo de mapa |
| `--bg-surface` | `#0F172A` (`86%` alpha) | Paneles flotantes (*glassmorphism* operativo) |
| `--bg-elevated` | `#1E293B` | Tarjetas seleccionadas, modales, tooltips |
| `--border-subtle` | `rgba(148, 163, 184, 0.16)` | Separadores y bordes de paneles |
| `--text-primary` | `#F8FAFC` | Títulos, KPIs críticos (Contraste $> 14:1$) |
| `--text-secondary` | `#94A3B8` | Etiquetas secundarias, nombres de ríos |
| `--status-green` | `#10B981` | Estado Normal (`VERDE`) |
| `--status-yellow` | `#F59E0B` | Vigilancia / Descenso (`AMARILLO`) |
| `--status-orange` | `#F97316` | Pre-alerta (`NARANJA`) |
| `--status-red` | `#EF4444` | Emergencia / Corte RN 9 (`ROJO`) |
| `--telemetry-live` | `#06B6D4` | Datos en vivo (Celular / Barras de lluvia) |
| `--telemetry-buffer` | `#8B5CF6` | Datos recuperados del búfer SQLite / DuckDB |
| `--telemetry-lora` | `#FBBF24` | Respaldo de emergencia LoRa / Modo Isla |

### 6.2 Tipografía
- **UI y Narrativa:** `Inter` o `Geist Sans` (alta legibilidad en tamaños pequeños sobre fondos oscuros).
- **Datos, Coordenadas, Timestamps y Logs:** `JetBrains Mono` con la propiedad CSS `font-variant-numeric: tabular-nums` obligatoria en todos los contadores (ETA, nivel en cm, lluvia, búfer SQLite) para evitar saltos visuales (*layout jitter*) cuando se actualizan cada segundo.

### 6.3 Accesibilidad en Situaciones de Estrés (WCAG AA/AAA)
- **Cero dependencia exclusiva del color:** Cada nivel de alerta combina color + texto explícito + forma geométrica distinta:
  - `VERDE`: Círculo con tilde.
  - `AMARILLO`: Triángulo de advertencia.
  - `NARANJA`: Rombo con exclamación.
  - `ROJO`: Octágono de detención/corte.
- **Atajos de teclado operativos:**
  - `1`–`4`: Seleccionar y enfocar Volcán, Tumbaya, Purmamarca o Tilcara.
  - `M`: Alternar vista de mapa `2D` / `3D`.
  - `S`: Abrir/cerrar Drawer de Simulador (si está habilitado).
  - `Esc`: Cerrar modales o colapsar el inspector lateral.

---

## 7. Arquitectura Técnica y Contratos de Datos (Agent-Ready)

### 7.1 Stack Tecnológico Recomendado
- **Framework:** React 19 + TypeScript + Vite (o Next.js App Router si se requiere SSR para la Landing).
- **Estilos y Primitivos UI:** Tailwind CSS v4 + Radix UI (`shadcn/ui`) + Lucide Icons.
- **Mapa Operativo:** `maplibre-gl` + `@deck.gl/core` + `@deck.gl/layers` + `@deck.gl/mapbox`.
- **Escena 3D (Landing):** `three` + `@react-three/fiber` + `@react-three/drei` + shaders GLSL personalizados.
- **Visualización de Series:** `echarts` (`echarts-for-react` o wrapper nativo).
- **Estado y Tiempo Real:** `zustand` + conexión **WebSocket / SSE** con reconexión exponencial automática hacia el servidor local (`127.0.0.1:8000`).

### 7.2 Esquema de Contratos de Datos (Frontend <-> Backend)

Para desacoplar la nueva interfaz del backend actual (DuckDB + FastAPI/Python local), se definen tres contratos principales:

#### 1. Stream de Telemetría y Estado de Cuenca (`WS /ws/telemetry`)
```json
{
  "timestamp": "2026-11-22T18:54:11-03:00",
  "mode": "SIMULATION",
  "calibrated_thresholds": false,
  "basins": [
    {
      "id": "CUENCA_ARROYO_DEL_MEDIO",
      "name": "Volcán",
      "river": "Arroyo del Medio",
      "station_id": "EST-VOLCAN-CAB01",
      "alert_level": "RED",
      "eta_rn9_minutes": 9,
      "rn9_crossing_coords": [-65.4658, -23.9162],
      "metrics": {
        "rain_15m_mm": 3.61,
        "rain_60m_mm": 25.1,
        "rain_72h_mm": 35.0,
        "water_level_cm": 41.7,
        "level_delta_15m_cm": 21.7,
        "battery_pct": 91.5
      },
      "connectivity": {
        "node_state": "ISLAND_MODE",
        "primary_link": "DOWN",
        "lora_backup": "ACTIVE",
        "data_source": "EMERGENCY_LORA",
        "sqlite_buffer_count": 91,
        "local_beacon_active": true
      },
      "recommendation": {
        "action": "Recomendar el corte preventivo de la RN 9 y la evacuación de zonas bajas.",
        "distance_to_rn9_km": 5.2
      }
    }
  ]
}
```

#### 2. Serie Histórica Reconstruida (`GET /api/basins/:id/series`)
```json
{
  "basin_id": "CUENCA_ARROYO_DEL_MEDIO",
  "thresholds_cm": {
    "yellow": 30,
    "orange": 38,
    "red": 45
  },
  "points": [
    {
      "ts": "2026-11-22T18:50:00-03:00",
      "rain_15m_mm": 12.4,
      "water_level_cm": 34.2,
      "origin": "RECOVERED_BUFFER"
    },
    {
      "ts": "2026-11-22T19:05:00-03:00",
      "rain_15m_mm": 4.3,
      "water_level_cm": 56.8,
      "origin": "LIVE_TELEMETRY"
    }
  ]
}
```

#### 3. Comandos del Simulador de Crisis (`POST /api/simulator/command`)
```json
{
  "station_id": "EST-VOLCAN-CAB01",
  "weather_profile": "CONVECTIVE_STORM",
  "cellular_cut": true,
  "lora_cut": false,
  "saturated_soil_72h": true
}
```

---

## 8. Plan de Implementación por Fases y Criterios de Aceptación

### Fase 1: Fundación Visual y Mapa Táctico con Alertas (Semanas 1–2)
- Configurar sistema de diseño (tokens oscuros, tipografía tabular, badges accesibles).
- Implementar layout *Map-First* (`100vw` $\times$ `100vh`) con MapLibre GL JS + capa Terrain-RGB del Copernicus DEM GLO-30 (toggle 2D/3D).
- Integrar capas dinámicas de polígonos de cuenca, cauces animados (Deck.gl) y marcadores pulsantes de alerta en cruces de la RN 9.

### Fase 2: Inspector Hidrológico, Simulador Aislado y Parte Oficial (Semanas 3–4)
- Refactorizar panel izquierdo de cuencas con *auto-sort* por severidad y micro-sparklines.
- Construir Inspector Derecho con pestañas (`Hidrología`, `Nodo y Red`, `Eventos`) y gráfica ECharts con bandas de umbral y patrón visual para datos recuperados de DuckDB.
- Mover la Consola de Crisis a un *Bottom Drawer* aislado bajo el interruptor `MODO SIMULADOR`.
- Implementar el modal/vista formateada de **Parte de Situación** con exportación a PDF y texto listo para WhatsApp.

### Fase 3: Landing Page Inmersiva con Modelos 3D Animados (Semanas 5–6)
- Procesar recorte del DEM de Volcán (Arroyo del Medio + RN 9) en malla 3D `.glb` optimizada.
- Desarrollar escena R3F con shader GLSL de flujo/crecida, partículas de lluvia convectiva, pulsos LoRa y slider interactivo de tiempo/escenario.
- Implementar el *scrollytelling* en 4 actos y conectar las tarjetas de estado en vivo al backend.

### Fase 4: Pruebas de Resiliencia y Validación Operativa (Semana 7)
- **Criterio QA 1 (Cero huecos visuales):** Simular corte celular -> tormenta convectiva -> escalamiento a `ROJO` por LoRa -> reconexión -> verificar que el búfer SQLite baje a `0`, la gráfica muestre las barras recuperadas en color/patrón diferenciado y **no** se disparen alertas tardías falsas.
- **Criterio QA 2 (Operación Offline):** Confirmar que el mapa 3D, las fuentes tipográficas y la app funcionan completamente en red local (`127.0.0.1`) sin dependencia de CDNs externos.
- **Criterio QA 3 (Rendimiento):** Mantener $\ge 55\text{ fps}$ en el mapa táctico con alertas activas y $\ge 30\text{ fps}$ en la Landing 3D en dispositivos de gama media, con fallback verificado para hardware sin aceleración WebGL.