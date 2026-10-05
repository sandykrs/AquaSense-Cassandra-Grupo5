
## III. Tecnología Seleccionada

### A. Apache Cassandra 5.0.9

Apache Cassandra es una base de datos NoSQL distribuida de columnas anchas, diseñada para manejar grandes volúmenes de datos a través de múltiples nodos sin un punto único de fallo. Fue originalmente desarrollada en Facebook y liberada como proyecto open source en 2008, y hoy es mantenida por la Apache Software Foundation.

Características principales:
- **Arquitectura peer-to-peer:** todos los nodos son iguales, sin maestro.
- **Escalabilidad horizontal lineal:** agregar nodos aumenta la capacidad.
- **Alta disponibilidad:** replicación configurable, sin downtime.
- **Consistencia ajustable:** desde ONE hasta ALL.
- **Modelo wide-column:** ideal para series de tiempo.
- **CQL (Cassandra Query Language):** similar a SQL, fácil de aprender.

### B. Justificación de la elección

| Alternativa | Por qué se descartó |
|---|---|
| ScyllaDB | Compatible con CQL, pero menos documentación y comunidad. |
| Apache HBase | Requiere Hadoop y Zookeeper; complejidad operativa mayor. |
| Google Cloud Bigtable | Dependencia de la nube; el proyecto debe ser reproducible localmente. |
| **Cassandra** | **Elegida:** open source, madura, documentada, fácil de levantar con Docker. |

### C. Versión utilizada

Se utilizó **Apache Cassandra 5.0.9** en un contenedor Docker, con SimpleStrategy y RF=1 para desarrollo local, y NetworkTopologyStrategy con RF=3 para producción.

---

## IV. Modelo y Arquitectura

### A. Filosofía de modelado

Cassandra es **query-driven**: las tablas se diseñan a partir de las consultas, no de un modelo normalizado. Cada consulta frecuente tiene su propia tabla desnormalizada. Esto se debe a que Cassandra no soporta joins eficientes.

### B. Tablas del modelo

El keyspace `aquasense` contiene 8 tablas:

| Tabla | Propósito | Partition Key | Clustering Key |
|---|---|---|---|
| `sensores` | Catálogo de sensores | `sensor_id` | — |
| `sensores_por_zona` | Sensores por zona | `zona` | `sensor_id` |
| `lecturas_por_sensor` | Series de tiempo por sensor | `(sensor_id, bucket)` | `fecha_hora DESC` |
| `lecturas_por_zona` | Series de tiempo por zona | `(zona, bucket)` | `fecha_hora DESC, sensor_id ASC` |
| `anomalias_por_sensor` | Anomalías por sensor | `(sensor_id, bucket)` | `fecha_hora DESC` |
| `anomalias_por_zona` | Anomalías por zona | `(zona, bucket)` | `fecha_hora DESC, sensor_id ASC` |
| `resumen_diario_zona` | Agregados diarios | `zona` | `dia DESC` |
| `ultima_lectura_sensor` | Última lectura por sensor | `sensor_id` | — |

### C. Decisiones clave

1. **Bucketing diario:** el campo `bucket` (tipo `date`) agrupa las lecturas por día para evitar particiones gigantes.
2. **Clustering DESC:** las últimas lecturas se devuelven primero sin ordenamiento adicional.
3. **TWCS:** TimeWindowCompactionStrategy agrupa SSTables por ventana de 1 día, óptimo para series de tiempo.
4. **Desnormalización:** cada lectura se escribe en `lecturas_por_sensor` y `lecturas_por_zona`, aceptando el costo de escritura a cambio de lecturas rápidas.
5. **Tablas dedicadas para anomalías:** evitan `ALLOW FILTERING`.

### D. Arquitectura


La arquitectura consta de:
- **Capa de ingesta:** API en Python que recibe lecturas y las escribe en Cassandra.
- **Clúster Cassandra:** 1 nodo en desarrollo, 3 en producción con RF=3.
- **Capa de consulta:** API que sirve dashboards y reportes operativos.

### E. Escalabilidad y alta disponibilidad

- **Escalabilidad horizontal:** agregar nodos distribuye datos automáticamente.
- **Replicación RF=3:** cada dato existe en 3 nodos.
- **Sin punto único de fallo:** cualquier nodo puede responder.
- **Recuperación:** `nodetool repair` sincroniza réplicas.
