# QuebradaAlert — Modelo de negocios, Canvas y FODA

Elaborado el 22/11/2026 a partir del estado del repositorio (`README.md`, `cerebro/`, `docs/`).

**Cómo leerlo.** Lo que se apoya en el repositorio está dicho como hecho. Todo lo comercial (clientes dispuestos a
pagar, precios, fuentes de financiamiento) es **hipótesis sin validar**: no hay entrevistas, cotizaciones ni cartas de
intención en el proyecto. No se incluyen montos porque no existe todavía una lista de materiales ni un costo de
operación medidos.

## 1. Modelo de negocios propuesto

**Alerta temprana como servicio (B2G), con software de núcleo abierto.**

QuebradaAlert no vende estaciones: vende **cobertura de alerta por microcuenca**, con una disponibilidad comprometida
aun con el enlace caído. El cliente paga por cuenca monitoreada y por año; el equipo instala, opera, mantiene y
calibra.

| Componente | Qué se cobra | Quién paga (hipótesis) |
|---|---|---|
| **Piloto / despliegue** | Pago único por cuenca: estación de cabecera, enlace de respaldo, baliza local, instalación y puesta en marcha. | Proyecto financiado (fondo de innovación, cooperación, obra provincial). |
| **Servicio anual** | Contrato anual de operación y mantenimiento por cuenca: operación, mantenimiento de campo antes de la temporada de lluvias, tablero, parte de situación, soporte en temporada. | Organismo provincial de recursos hídricos / Defensa Civil; municipios. |
| **Integración** | Abono por acceso a la API de alertas y a la cuenta regresiva de arribo a la ruta. | Operador vial, empresas con logística por RN 9 / RN 52. |
| **Calibración y estudios** | Proyecto por única vez: umbrales por cuenca, delimitación validada, escenarios históricos. | Organismo técnico o universidad en convenio. |

**Por qué este modelo y no otro**

- **No venta de hardware suelto**: el valor demostrado está en el software (búfer local, reconciliación sin duplicados,
  sin alarmas tardías). Una estación vendida sin operación deja de funcionar a la primera temporada.
- **No SaaS puro**: sin estación propia en la cabecera no hay producto. El relevamiento muestra que no existe medición
  pública de nivel, caudal ni turbidez en los tributarios, y que el satélite (latencia de 2 a 18 h) no sirve para
  disparar una alerta con tiempos de concentración de 18 a 54 min.
- **No venta directa a vecinos**: la decisión de corte o evacuación es de Defensa Civil, la DPRH y Vialidad Nacional;
  el sistema recomienda, no ordena.
- **Núcleo abierto**: un organismo público compra con menos resistencia algo que puede auditar y que no lo deja
  cautivo. El ingreso viene de operar, no de la licencia. (El repositorio hoy no tiene archivo de licencia en la raíz:
  hay que definirla.)
- **El ingreso recurrente se instrumenta como contrato de mantenimiento**, no como suscripción SaaS: el procurement
  público argentino no compra "abonos" pero sí contratos de servicios de operación y mantenimiento — mismo ingreso
  recurrente, figura jurídica existente.
- **El piloto debe alimentar el sistema de la DPRH**, no correr en paralelo: si sus datos entran a su cadena de
  alerta oficial, el pitch pasa de "competidor" a "sensor adicional" y se reduce el riesgo de que la ampliación de
  su propia red nos vea como amenaza. Implica cumplir sus protocolos de telemetría (a verificar en las entrevistas).

**Etapas**

| Etapa | Objetivo | Condición para pasar a la siguiente |
|---|---|---|
| 0. Demo (hoy) | Mostrar la resiliencia ante cortes de enlace. | Un organismo acepta un piloto en una cuenca. |
| 1. Piloto en una cuenca | Una estación física en una cabecera (candidata: Arroyo del Medio, Volcán), una temporada de lluvias completa, en paralelo con el sistema oficial y sin emitir alertas a la población. | Datos de una temporada, alcance del enlace de respaldo medido en terreno, umbrales con primera calibración. |
| 2. Servicio en las cuatro cuencas | Contrato anual con el organismo provincial; integración con el operador vial. | Renovación del contrato y un segundo pagador. |
| 3. Réplica | Otras quebradas y corredores andinos con el mismo problema (conectividad pobre, crecidas súbitas). | — |

**Lo que hay que resolver antes de cobrar**

1. **Licencias de datos**: Open-Meteo gratuito y FABDEM son solo para uso no comercial. Un servicio pago necesita el
   plan comercial, alojar el modelo por cuenta propia o reemplazarlos (WRF-SMN en AWS es CC BY 2.5; Copernicus GLO-30
   ya es la base del proyecto).
2. **Responsabilidad**: definir por contrato que el sistema es apoyo a la decisión y que la alerta oficial la emite el
   organismo. Hoy los umbrales son de ejemplo y el tiempo de arribo (Kirpich) sobrestima frente a lo citado para
   flujos de detritos.
3. **Seguridad**: la ingesta no tiene autenticación.
4. **Hardware**: el nodo es un proceso Python simulado; no hay firmware, lista de materiales ni costo unitario.
5. **Figura jurídica** para contratar con el Estado (convenio vía universidad, cooperativa, SAS, etc.).

## 2. Business Model Canvas

| Bloque | Contenido |
|---|---|
| **Segmentos de clientes** | **Principal (paga y decide):** organismo provincial de recursos hídricos (DPRH) y Defensa Civil de Jujuy. **Secundarios:** Vialidad Nacional (RN 9), municipios y comisiones municipales de Volcán, Tumbaya, Purmamarca y Tilcara. **A explorar:** empresas con logística por el corredor (minería, transporte, turismo), aseguradoras. **Beneficiarios que no pagan:** vecinos, viajeros y turistas. |
| **Propuesta de valor** | Alerta de crecida súbita **que sigue funcionando sin conexión**: la estación decide el semáforo por su cuenta, avisa por un enlace de respaldo y activa una baliza local. Al volver el enlace entrega todo **sin pérdidas, sin duplicados y sin alarmas por tormentas ya terminadas**. Para el centro de comando: una cuenta regresiva de arribo a la RN 9, parte de situación listo y tablero que funciona sin internet. Medición en cabecera, donde hoy no hay ninguna pública. |
| **Canales** | Demo en vivo y hackatón; presentación directa a la DPRH y Defensa Civil; convenio con la Facultad de Ingeniería de la UNJu; piloto en paralelo con el sistema oficial; API para integrar con sistemas existentes; publicaciones técnicas y prensa local después del piloto. |
| **Relación con clientes** | Servicio gestionado con acompañamiento en temporada de lluvias; capacitación de operadores; informe de fin de temporada con eventos, fallas de enlace y ajustes de umbrales; código abierto y auditable; co-diseño de protocolos con el organismo (la decisión siempre es suya). |
| **Fuentes de ingresos** | 1) Pago único por despliegue de cada cuenca. 2) Abono anual por cuenca monitoreada (ingreso recurrente principal). 3) Abono por integración vía API. 4) Proyectos de calibración y estudios. 5) Subsidios y fondos de innovación o cooperación para la etapa piloto. |
| **Recursos clave** | Software del nodo y del backend (probado con tests); delimitación de las cuatro microcuencas y geodatos; relevamiento de fuentes de datos; equipo con conocimiento de software, hidrología y del terreno; a construir: estación física, historial de eventos propio, relación con los organismos. |
| **Actividades clave** | Diseñar y fabricar la estación de campo; instalar y mantener en cabeceras; calibrar umbrales por cuenca; operar el backend y el tablero; medir el alcance real del enlace de respaldo; gestionar convenios y acceso a datos institucionales; endurecer seguridad. |
| **Socios clave** | DPRH (telemetría, cartografía, registro de eventos); Defensa Civil; Vialidad Nacional; SMN (pronóstico WRF); UNJu / FI-UGICH (cuencas 1:50.000, validación); IGN y SEGEMAR (relieve fino, peligrosidad geológica); INTA Hornillos; comunidades y municipios (permisos de instalación, cuidado de equipos); proveedores de sensores y radio. |
| **Estructura de costos** | **Fijos:** equipo de desarrollo y operación, infraestructura del backend, licencias de datos comerciales, seguros y figura jurídica. **Por cuenca:** equipo de la estación (sensores de lluvia, nivel y turbidez, radio, energía solar, gabinete), instalación en zona de acceso difícil, mantenimiento anual y reposición por vandalismo o daño del propio evento. **Por única vez:** calibración y validación. |

## 3. FODA

| | Ayuda | Perjudica |
|---|---|---|
| **Interno** | **Fortalezas** | **Debilidades** |
| | • Diferencial técnico concreto y demostrable: opera en corte de enlace, sin pérdidas, duplicados ni alarmas tardías. | • Es una demo: estaciones y sensores simulados, sin hardware de campo. |
| | • Demo funcionando de punta a punta, con tests y CI. | • Umbrales del semáforo sin calibrar; no hay registro local de aludes con lluvia asociada. |
| | • Tablero y mapa funcionan sin internet. | • Tiempo de arribo (Kirpich) de 50 a 120 min, mayor que los 20 a 45 min citados para estos eventos. |
| | • Geografía real: cuatro microcuencas delimitadas con datos abiertos. | • Enlace de respaldo emulado; alcance de LoRa en quebradas sin medir. |
| | • Limitaciones documentadas con honestidad, lo que da credibilidad ante organismos técnicos. | • Sin autenticación en la ingesta. |
| | • Protocolo con contrato estándar (tópicos Sparkplug B), integrable. | • Contornos de cuenca sin validar con cartografía oficial. |
| | • Costos de software bajos: SQLite, DuckDB, FastAPI, sin infraestructura pesada. | • Sin validación comercial, sin costos unitarios, sin figura jurídica ni licencia definida. |
| **Externo** | **Oportunidades** | **Amenazas** |
| | • Vacío real de medición: no hay nivel, caudal ni turbidez públicos en los tributarios; solo dos pluviómetros telemétricos, ninguno en cabecera. | • Ciclo de compra pública largo y dependiente de presupuesto y de cambios de gestión. |
| | • El satélite no puede disparar la alerta (latencia de horas): la estación local es insustituible. | • La DPRH amplía su propia red (estaciones operativas y otras en gestión): puede verse como competencia y no como complemento. |
| | • Antecedentes graves y recientes (alud de Volcán, 10/1/2017) y RN 9 como corredor crítico. | • Responsabilidad legal y reputacional ante una falsa alarma o una alerta omitida. |
| | • La provincia ya invierte en red hidrometeorológica: hay interés y un interlocutor. | • Vandalismo, robo y destrucción de equipos por el mismo evento que se quiere medir. |
| | • Datos abiertos disponibles para anticipar y calibrar: WRF-SMN, CMORPH, SMAP, DesInventar. | • Dependencia de datos institucionales que hoy solo se obtienen por solicitud formal. |
| | • Convenio universitario como vía de entrada y de validación técnica. | • Licencias no comerciales de parte de las fuentes de datos usadas. |
| | • Problema repetido en otras quebradas y corredores andinos: el modelo es replicable. | • Proveedores establecidos de estaciones hidrometeorológicas con trayectoria ante el Estado. |
| | • Financiamiento de adaptación climática y gestión de riesgo como posible fuente para el piloto (a verificar). | • Costo en moneda extranjera de sensores y radios. |

**Cruces que definen la estrategia**

- **Fortaleza + oportunidad:** entrar por el punto ciego (cabeceras sin medición y sin conectividad confiable), no por
  competir con la red oficial. Presentarse como complemento que le entrega datos a la DPRH.
- **Debilidad + oportunidad:** usar el convenio con la UNJu y los datos abiertos (escenario "Volcán 2017", curvas de
  referencia) para calibrar y validar antes de cobrar.
- **Fortaleza + amenaza:** código abierto y limitaciones explícitas para reducir el riesgo de responsabilidad; el
  sistema recomienda y el organismo decide.
- **Debilidad + amenaza:** no emitir alertas a la población hasta tener una temporada medida en paralelo.

## 4. Próximos pasos de validación

1. Entrevistar a la DPRH y Defensa Civil: quién decide la compra, con qué presupuesto y qué exigirían de un piloto.
   **Pregunta clave: qué pasa si la DPRH dice que no** — hoy el modelo depende 100% de un solo comprador con ciclo
   de compra largo; la respuesta define si el plan B es convenio universitario con otro financiamiento o réplica en
   otra provincia.
2. **Segundo pagador**: entrevistar también a Vialidad Nacional, la cámara de turismo de la Quebrada y una
   aseguradora — el dato de alerta tiene valor asegurable y el corredor turístico es el beneficiario directo del
   alud de 2017. Validar si alguno pagaría por integración vía API.
3. Armar la lista de materiales de una estación y cotizarla, para tener el costo por cuenca. **Ancla de precio sin
   inventar números**: buscar en contrataciones públicas (comprar.gob.ar / boletines oficiales) adjudicaciones
   históricas de estaciones hidrometeorológicas o servicios de mantenimiento — dan orden de magnitud real.
4. **Cuantificar el beneficio evitado** aunque sea en rango: el alud de 2017 cortó la RN 9, dejó >1.000
   damnificados y afectó al corredor turístico por días. El decisor público compra por beneficio, no por tecnología.
5. Medir el enlace de respaldo en una cabecera real.
6. Resolver licencia del código, licencias de datos y figura jurídica.
7. Relevar convocatorias de financiamiento vigentes para el piloto.

## 5. Revisión crítica (22/11/2026)

Revisión externa del documento. Fortalezas confirmadas: modelo B2G correcto (valor en el software, no en el
hardware), hipótesis comerciales declaradas como tales, posicionamiento complementario a la DPRH, gates de etapa
realistas y bloqueos reales detectados (licencias, LICENSE ausente, ingesta sin auth, Kirpich que sobreestima).

Ajustes incorporados tras la revisión: ingreso recurrente reformulado como contrato de mantenimiento (compatible
con procurement público); piloto orientado a alimentar la cadena de la DPRH; agregados al plan de validación el
segundo pagador, el ancla de precio por licitaciones históricas y la cuantificación del beneficio evitado.

Riesgo estratégico que queda abierto: **concentración en un único comprador institucional**. Mitigaciones posibles
— réplica en otros corredores andinos, segundo pagador privado, financiamiento no reembolsable para el piloto —
pero ninguna está validada todavía.
