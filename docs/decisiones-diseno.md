
# Decisiones de Diseño - AquaSense CR

**Proyecto:** XS0131 - Gestión de Bases de Datos y Análisis de Información  
**Caso:** 3 - AquaSense CR (Wide-Column)  
**Grupo:** 5  
**Tecnología:** Apache Cassandra 5.0.9  
**Autores:** Jeferson Salazar, Sandy Ruiz, Jimena Díaz, Estafanía Núñez, Keylor Gómez

---

## 1. Objetivo del documento

Este documento registra las decisiones técnicas tomadas durante el diseño de la solución, las alternativas consideradas y las razones por las que se descartaron. Sirve como evidencia del proceso de diseño y como guía para futuras modificaciones.

---

## 2. Decisión 1: Elección de Apache Cassandra

### Contexto
El caso requiere absorber grandes volúmenes de escritura (telemetría de 1.000 sensores), consultar series de tiempo por sensor y por zona, y escalar horizontalmente.

### Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| ScyllaDB | Compatible con CQL, pero menos documentación y comunidad más pequeña. |
| Apache HBase | Requiere Hadoop y Zookeeper; complejidad operativa mayor. |
| Google Cloud Bigtable | Dependencia de la nube y credenciales; el proyecto debe ser reproducible localmente. |
| Cassandra | Elegida: open source, ampliamente documentada, fácil de levantar con Docker, escalabilidad horizontal comprobada. |

### Decisión
Usar **Apache Cassandra 5.0.9** por su madurez, soporte de CQL, y facilidad de reproducibilidad con Docker.

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
| Solo `sensor_id` | Partición gigante; riesgo de OutOfMemory y degradación. |
| `sensor_id + ts` | Cada lectura sería una partición distinta; se pierde el beneficio del clustering. |
| `sensor_id + bucket` (día) | Elegida: tamaño predecible, consultas por rango temporal eficientes. |
| `sensor_id + bucket` (hora) | Particiones más pequeñas, pero más consultas para rangos largos. Se reserva para producción con mayor frecuencia. |

### Decisión
Particionar por `(sensor_id, bucket)` con bucket diario.

### Consecuencias
- Cada partición corresponde a un sensor en un día específico.
- Los rangos temporales que cruzan días requieren iteración en la aplicación.
- Se evita el crecimiento ilimitado de particiones.

---

## 4. Decisión 3: Clustering por `ts DESC`

### Contexto
Las consultas más frecuentes piden las últimas lecturas de un sensor o un rango temporal reciente.

### Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| `ts ASC` | Las últimas lecturas quedarían al final; se requeriría ordenamiento adicional. |
| Sin clustering | No se podrían hacer consultas por rango temporal eficientemente. |
| `ts DESC` | Elegida: las últimas lecturas se devuelven primero sin costo extra. |

### Decisión
Clustering por `ts DESC` en `sensor_readings` y `readings_by_zone`.

### Consecuencias
- `LIMIT 10` devuelve las últimas 10 lecturas directamente.
- Los rangos temporales se recorren en orden descendente.

---

## 5. Decisión 4: Tabla `readings_by_zone` desnormalizada

### Contexto
Se necesita consultar lecturas por zona y rango temporal, pero `sensor_readings` está particionada por sensor.

### Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| Usar `ALLOW FILTERING` sobre `sensor_readings` | Escaneo completo; prohibido en Cassandra para producción. |
| Índice secundario sobre `zone` | Bajo rendimiento en tablas de alta cardinalidad. |
| Tabla `readings_by_zone` desnormalizada | Elegida: consultas rápidas, a costa de duplicar escrituras. |

### Decisión
Crear `readings_by_zone` con partición `(zone, bucket)` y clustering `(ts DESC, sensor_id ASC)`.

### Consecuencias
- Cada lectura se escribe dos veces: una en `sensor_readings` y otra en `readings_by_zone`.
- Se acepta el costo de escritura a cambio de lecturas rápidas por zona.

---

## 6. Decisión 5: TimeWindowCompactionStrategy (TWCS)

### Contexto
Las tablas de series de tiempo acumulan SSTables rápidamente. La compactación por defecto (SizeTiered) no es óptima para este patrón.

### Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| SizeTieredCompactionStrategy | Diseñada para cargas generales; no agrupa por tiempo. |
| LeveledCompactionStrategy | Buena para lecturas aleatorias, pero costosa para escritura intensiva. |
| TimeWindowCompactionStrategy (TWCS) | Elegida: agrupa SSTables por ventana temporal, ideal para series de tiempo. |

### Decisión
Usar TWCS con ventana de 1 día en `sensor_readings` y `readings_by_zone`.

### Consecuencias
- Las SSTables se agrupan por día.
- Las lecturas recientes son más rápidas.
- Los datos antiguos se pueden eliminar con TTL sin compactación costosa.

---

## 7. Decisión 6: Tabla `sensor_latest` para última lectura

### Contexto
Obtener la última lectura de un sensor recorriendo `sensor_readings` requiere `LIMIT 1` sobre la partición actual, lo cual no siempre es trivial si el bucket cambia.

### Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| Consultar `sensor_readings` con `LIMIT 1` | Puede devolver vacío si el bucket del día aún no tiene datos. |
| Índice secundario | No garantiza eficiencia. |
| Tabla `sensor_latest` dedicada | Elegida: acceso O(1) por `sensor_id`. |

### Decisión
Mantener `sensor_latest` actualizada en cada escritura (upsert).

### Consecuencias
- Cada escritura implica un upsert adicional en `sensor_latest`.
- La consulta de última lectura es directa y rápida.

---

## 8. Decisión 7: Replicación en producción

### Contexto
En desarrollo local se usa `SimpleStrategy` con RF=1, pero en producción se requiere alta disponibilidad.

### Alternativas consideradas
| Alternativa | Por qué se descartó |
|---|---|
| `SimpleStrategy` en producción | No soporta múltiples datacenters. |
| `NetworkTopologyStrategy` RF=3 | Elegida: tolera fallos de nodos, soporta múltiples DCs. |

### Decisión
Usar `NetworkTopologyStrategy` con RF=3 en producción.

### Consecuencias
- Cada dato existe en 3 nodos.
- Tolerancia a fallos de hasta 1 nodo sin pérdida de datos.
- Mayor uso de disco.

---

## 9. Riesgos identificados

| Riesgo | Mitigación |
|---|---|
| Partición muy grande si un sensor genera muchas lecturas por día | Cambiar a bucket horario si es necesario. |
| Hotspot si una zona concentra muchos sensores | Distribuir con bucket horario o añadir shard. |
| Consultas con `ALLOW FILTERING` | Diseñar tablas específicas por consulta. |
| Desnormalización inconsistente | Escribir siempre en todas las tablas derivadas en la misma operación. |
| Contenedor Docker sin persistencia | Usar volúmenes de Docker para producción. |

---

## 10. Alternativas descartadas a nivel de modelado

| Alternativa | Motivo del descarte |
|---|---|
| Modelo normalizado con joins | Cassandra no soporta joins eficientes. |
| Uso de índices secundarios | Bajo rendimiento en alta cardinalidad. |
| Una única tabla para todas las consultas | Imposible sin `ALLOW FILTERING`. |
| Almacenar todo en una sola partición por zona | Partición gigante; riesgo de hotspot. |

---

## 11. Conclusiones

Las decisiones tomadas priorizan:

1. **Rendimiento de escritura** (telemetría intensiva).
2. **Consultas rápidas por sensor y por zona**.
3. **Escalabilidad horizontal**.
4. **Reproducibilidad local** con Docker.
5. **Evitar hotspots y particiones gigantes**.

Cada decisión está alineada con las buenas prácticas de modelado en Cassandra y con los requisitos del caso AquaSense CR.
