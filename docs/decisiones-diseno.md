
# Decisiones de Diseño - AquaSense CR

**Proyecto:** XS0131 - Gestión de Bases de Datos y Análisis de Información  
**Caso:** 3 - AquaSense CR (Wide-Column)  
**Grupo:** 5  
**Tecnología:** Apache Cassandra 5.0.9  
**Autores:** Jeferson Salazar, Sandy Ruiz, Jimena Díaz, Estefanía Núñez, Keylor Gómez

---

## 1. Objetivo del documento

Este documento registra las decisiones técnicas tomadas durante el diseño de la solución, las alternativas consideradas y las razones por las que se descartaron. Sirve como evidencia del proceso de diseño y como guía para futuras modificaciones.

Los nombres de tablas y columnas son los del schema vigente (`database/schema/schema.cql`): `lecturas_por_sensor`, `lecturas_por_zona`, `ultima_lectura_sensor`, `fecha_hora`, `zona`, etc. Donde una decisión se probó con datos, se cita la medición de `performance/resultados/tablas_metricas.md`.

---

## 2. Decisión 1: Elección de Apache Cassandra

### Contexto
El caso requiere absorber grandes volúmenes de escritura (telemetría de 1 000 sensores), consultar series de tiempo por sensor y por zona, y escalar horizontalmente.

### Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| ScyllaDB | Compatible con CQL, pero con menos documentación y una comunidad más pequeña. |
| Apache HBase | Requiere Hadoop y Zookeeper; mayor complejidad operativa. |
| Google Cloud Bigtable | Depende de la nube y de credenciales; el proyecto debe ser reproducible localmente. |
| Apache Cassandra | Elegida: código abierto, bien documentada, fácil de levantar con Docker y con escalabilidad horizontal comprobada. |

### Decisión
Usar **Apache Cassandra 5.0.9** por su madurez, su soporte de CQL y la facilidad de reproducirla con Docker (`docker-compose.yml`).

### Consecuencias
- Se aprovecha el modelo wide-column para series de tiempo.
- Se acepta la desnormalización como parte del diseño.
- Se depende de un contenedor Docker para el entorno local.

---

## 3. Decisión 2: Particionado por `(sensor_id, bucket)`

### Contexto
Un sensor puede generar lecturas durante meses o años. Si se usa solo `sensor_id` como partition key, la partición crece indefinidamente y se vuelve inmanejable.

### Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| Solo `sensor_id` | Partición gigante; riesgo de falta de memoria y degradación. |
| `sensor_id` + marca de tiempo | Cada lectura sería una partición distinta; se pierde el beneficio del clustering. |
| `(sensor_id, bucket)` con bucket diario | Elegida: tamaño predecible y consultas por rango temporal eficientes. |
| `(sensor_id, bucket)` con bucket horario | Particiones más pequeñas, pero más consultas para rangos largos. Se reserva para producción con mayor frecuencia de ingesta. |

### Decisión
Particionar `lecturas_por_sensor` por `(sensor_id, bucket)`, con `bucket` de tipo `date` (un día).

### Consecuencias
- Cada partición corresponde a un sensor en un día. Con lecturas cada 15 minutos son unas 96 filas por partición.
- **Medido:** 10 494 particiones sensor-día, de 88 a 96 filas, con un tamaño máximo de 6 866 bytes (muy por debajo de la referencia de 100 MB).
- Los rangos que cruzan días requieren consultar varios buckets (`bucket IN ...` o iterar en la aplicación). `tests/test_consultas.py` incluye una prueba de rango de siete días.
- Se evita el crecimiento ilimitado de particiones.

---

## 4. Decisión 3: Clustering por `fecha_hora DESC`

### Contexto
Las consultas más frecuentes piden las últimas lecturas de un sensor o un rango temporal reciente.

### Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| `fecha_hora ASC` | Las últimas lecturas quedarían al final; habría que invertir el orden en cada consulta. |
| Sin clustering por tiempo | No se podrían hacer consultas por rango temporal de forma eficiente. |
| `fecha_hora DESC` | Elegida: las últimas lecturas se devuelven primero sin costo extra. |

### Decisión
Clustering por `fecha_hora DESC` en `lecturas_por_sensor` y `lecturas_por_zona` (esta última con `sensor_id ASC` como segundo componente, para que dos sensores con la misma marca de tiempo no se pisen).

### Consecuencias
- `LIMIT 10` devuelve directamente las 10 lecturas más recientes de la partición.
- Los rangos temporales se recorren en orden descendente.
- La prueba `test_lecturas_de_un_sensor_ordenadas_por_tiempo` verifica el orden.

---

## 5. Decisión 4: Tabla `lecturas_por_zona` desnormalizada

### Contexto
Se necesita consultar lecturas por zona y rango temporal, pero `lecturas_por_sensor` está particionada por sensor.

### Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| `ALLOW FILTERING` sobre `lecturas_por_sensor` | Escaneo completo; inaceptable en producción. |
| Índice secundario sobre `zona` | Bajo rendimiento con esta cardinalidad y volumen. |
| Tabla `lecturas_por_zona` desnormalizada | Elegida: consultas rápidas a costa de duplicar escrituras. |

### Decisión
Crear `lecturas_por_zona` con partición `(zona, bucket)` y clustering `(fecha_hora DESC, sensor_id ASC)`.

### Consecuencias
- Cada medición se escribe en **dos** tablas de lecturas (`lecturas_por_sensor` y `lecturas_por_zona`), y en otras **dos** (`anomalias_por_sensor` y `anomalias_por_zona`) si es anómala. Además se actualizan `resumen_diario_zona` y `ultima_lectura_sensor`.
- **Es el punto débil medido del diseño.** Con 20 zonas, cada partición zona-día tiene unas 4 579 filas (hasta 379 022 bytes) y la consulta "zona y 1 día" tarda entre 38 y 47 ms de mediana. Con una versión previa del generador de 7 zonas, la partición llegó a 943 127 bytes y la consulta a 201.5 ms. El tamaño de la partición gobierna esa consulta.
- No se evaluó el impacto de la escritura duplicada en el rendimiento de la ingesta.

---

## 6. Decisión 5: TimeWindowCompactionStrategy (TWCS)

### Contexto
Las tablas de series de tiempo acumulan SSTables rápidamente. La compactación por defecto (`SizeTieredCompactionStrategy`) no es óptima para este patrón.

### Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| SizeTieredCompactionStrategy | Pensada para cargas generales; no agrupa por tiempo. |
| LeveledCompactionStrategy | Buena para lecturas aleatorias, pero costosa con escritura intensiva. |
| TimeWindowCompactionStrategy (TWCS) | Elegida: agrupa SSTables por ventana temporal, ideal para series de tiempo. |

### Decisión
Usar TWCS con ventana de 1 día en `lecturas_por_sensor` y `lecturas_por_zona`. Las demás tablas usan la compactación por defecto.

### Consecuencias
- En teoría, las SSTables se agrupan por día y los datos antiguos se compactan por separado.
- **No se configuró ningún TTL** en el prototipo. Un TTL (por ejemplo `default_time_to_live`) permitiría expirar datos antiguos sin compactación costosa, y queda como mejora para producción.
- **No se midió el efecto de TWCS:** los datos cubren solo 11 días y no se comparó contra otras estrategias.

---

## 7. Decisión 6: Tabla `ultima_lectura_sensor`

### Contexto
Obtener la última lectura de un sensor consultando `lecturas_por_sensor` con `LIMIT 1` requiere conocer el bucket del día. Si el bucket del día aún no tiene datos, la consulta devuelve vacío y habría que retroceder día por día.

### Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| `LIMIT 1` sobre `lecturas_por_sensor` | Puede devolver vacío si el bucket del día aún no tiene datos. |
| Índice secundario | No garantiza eficiencia. |
| Tabla `ultima_lectura_sensor` dedicada | Elegida: acceso directo por `sensor_id`. |

### Decisión
Mantener `ultima_lectura_sensor` con una fila por sensor (clave `sensor_id`).

### Consecuencias
- La consulta de última lectura es directa. **Medido:** 1 fila, 2.4 a 2.8 ms de mediana desde Python.
- En el prototipo, el cargador acumula la última lectura de cada sensor en memoria y la escribe **una vez al final** de la carga. En producción se actualizaría con un *upsert* en cada escritura, lo que agrega una escritura por lectura.
- La prueba `test_ultima_lectura_es_la_mas_reciente` compara esta tabla con `lecturas_por_sensor`.

---

## 8. Decisión 7: Replicación en producción

### Contexto
En desarrollo local se usa `SimpleStrategy` con RF=1, pero en producción se requiere alta disponibilidad.

### Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| `SimpleStrategy` en producción | No reconoce centros de datos ni racks. |
| `NetworkTopologyStrategy` con RF=3 | Elegida: tolera la caída de nodos y soporta varios centros de datos. |

### Decisión
Usar `NetworkTopologyStrategy` con RF=3 en producción. **El prototipo corre con `SimpleStrategy` y RF=1.**

### Consecuencias
- Cada dato existiría en 3 nodos.
- Con `QUORUM` se toleraría la caída de un nodo sin pérdida de disponibilidad.
- Mayor uso de disco.
- **No se demostró:** con un solo nodo no se puede probar la replicación ni la tolerancia a fallos (se declara en la sección de limitaciones del paper).

---

## 9. Riesgos identificados

| Riesgo | Mitigación | Estado |
|---|---|---|
| Partición muy grande si un sensor genera muchas lecturas por día | Cambiar a bucket horario (`guia-ajustes-schema.md`). | Con 15 min de intervalo, máximo medido 6 866 bytes. |
| Hotspot de escritura en `lecturas_por_zona`: todas las escrituras de una zona en un día caen en una sola partición | Bucket horario o *shard* en la partition key. | Medido: 20 particiones zona-día activas, hasta 379 022 bytes. Sin probar en un clúster. |
| Consultas con `ALLOW FILTERING` | Diseñar una tabla específica por consulta. | Ninguna consulta del repositorio lo usa; hay una prueba que verifica que una consulta sin partition key es rechazada. |
| Desnormalización inconsistente: los lotes son `UNLOGGED` y por partición, sin atomicidad entre tablas | Verificar después de cada carga (`verificar_carga.py`, `test_anomalias_coinciden_con_lecturas`). | Riesgo aceptado. El cargador no reintenta escrituras fallidas. |
| Pérdida de datos al reiniciar el contenedor | Volumen Docker `cassandra_data` (ya incluido en `docker-compose.yml`). | Tras los reinicios, el millón de filas seguía intacto. |
| Un solo nodo con RF=1 | Clúster de 3 nodos con RF=3 en producción. | Declarado como limitación. |

---

## 10. Alternativas descartadas a nivel de modelado

| Alternativa | Motivo del descarte |
|---|---|
| Modelo normalizado con joins | Cassandra no soporta joins eficientes. |
| Índices secundarios | Bajo rendimiento con alta cardinalidad. |
| Una única tabla para todas las consultas | Imposible sin `ALLOW FILTERING`. |
| Una sola partición por zona, sin bucket | Partición gigante y hotspot. |

---

## 11. Conclusiones

Las decisiones tomadas priorizan:

1. **Rendimiento de escritura** (telemetría intensiva).
2. **Consultas rápidas por sensor y por zona.**
3. **Escalabilidad horizontal** (explicada; no demostrada en un clúster).
4. **Reproducibilidad local** con Docker.
5. **Evitar particiones gigantes**, y reconocer que `lecturas_por_zona` es el punto de mayor riesgo de hotspot.

Cada decisión responde a un requisito del caso AquaSense CR. Los límites del prototipo (un nodo con RF=1, datos sintéticos de 11 días, sin TTL ni comparación entre estrategias de compactación) están declarados en el paper y en `performance/resultados/tablas_metricas.md`.
