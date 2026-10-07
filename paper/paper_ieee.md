# Sistema de Monitoreo de Redes de Agua Potable usando Apache Cassandra

**Curso:** XS0131 Gestión de Bases de Datos y Análisis de Información  
**Escuela de Estadística, Universidad de Costa Rica**  

**Autores:**  
Sandy
Estefanía
Keylor
Jimena
Jeferson

---

## Resumen (Abstract)

**Palabras clave:** Apache Cassandra, Wide-Column, NoSQL, Telemetría, Series de Tiempo.

---
## I. Introducción y Problema

## II. Fundamentos del Modelo NoSQL (Columnas Anchas)

## III. Tecnología Seleccionada

### A. Apache Cassandra 5.0.9

Apache Cassandra es una base de datos NoSQL distribuida de columnas anchas, diseñada para manejar grandes volúmenes de datos a través de múltiples nodos sin un punto único de fallo. Originalmente desarrollada en Facebook y liberada como proyecto open source en 2008, hoy es mantenida por la Apache Software Foundation.

Sus características principales son:

- **Arquitectura peer-to-peer:** todos los nodos son iguales, sin maestro.
- **Escalabilidad horizontal lineal:** agregar nodos aumenta la capacidad proporcionalmente.
- **Alta disponibilidad:** replicación configurable y sin downtime.
- **Consistencia ajustable:** desde ONE hasta ALL.
- **Modelo wide-column:** ideal para series de tiempo.
- **CQL (Cassandra Query Language):** sintaxis similar a SQL.

### B. Justificación de la elección

| Alternativa | Motivo del descarte |
|---|---|
| ScyllaDB | Compatible con CQL, pero con menos documentación y comunidad más pequeña. |
| Apache HBase | Requiere Hadoop y Zookeeper; mayor complejidad operativa. |
| Google Cloud Bigtable | Dependencia de la nube; el proyecto debe ser reproducible localmente. |
| **Apache Cassandra** | **Elegida:** open source, madura, ampliamente documentada, fácil de levantar con Docker. |

### C. Versión y entorno

Se utilizó **Apache Cassandra 5.0.9** en un contenedor Docker. Para desarrollo local se usó `SimpleStrategy` con factor de replicación 1. Para producción se documenta el uso de `NetworkTopologyStrategy` con RF=3.

---

## IV. Modelo y Arquitectura

### A. Filosofía de modelado

Cassandra es **query-driven**: las tablas se diseñan a partir de las consultas, no de un modelo normalizado. Cada consulta frecuente tiene su propia tabla desnormalizada, ya que Cassandra no soporta joins eficientes.

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

### C. Decisiones clave de diseño

1. **Bucketing diario:** el campo `bucket` (tipo `date`) agrupa las lecturas por día para evitar particiones gigantes.
2. **Clustering DESC:** las últimas lecturas se devuelven primero sin ordenamiento adicional.
3. **TimeWindowCompactionStrategy (TWCS):** agrupa SSTables por ventana de 1 día, óptimo para series de tiempo.
4. **Desnormalización:** cada lectura se escribe en `lecturas_por_sensor` y `lecturas_por_zona`, aceptando el costo de escritura a cambio de lecturas rápidas.
5. **Tablas dedicadas para anomalías:** evitan el uso de `ALLOW FILTERING`.

### D. Arquitectura de la solución

La arquitectura consta de cuatro capas:

1. **Capa de sensores:** 1.000 sensores distribuidos en 20 zonas que generan telemetría continua.
2. **Capa de ingesta:** scripts Python que generan y cargan los datos en lotes.
3. **Clúster Cassandra:** nodo único en desarrollo (3 nodos en producción con RF=3).
4. **Capa de consulta:** scripts CQL y Python que sirven las consultas operativas.


### E. Escalabilidad y alta disponibilidad

- **Escalabilidad horizontal:** agregar nodos distribuye datos automáticamente mediante consistent hashing.
- **Replicación RF=3:** cada dato existe en 3 nodos.
- **Sin punto único de fallo:** cualquier nodo puede responder consultas.
- **Recuperación:** `nodetool repair` sincroniza réplicas tras fallos.

## V. Implementación

## VI. Pruebas

## VII. Resultados

## VIII. Limitaciones y análisis

## IX. Conclusiones

## X. Referencias
[1] H. A. Herrera y C. Rueda Valenzuela, «NoSQL, la nueva tendencia en el manejo de datos», Tecnol. Investig. Academia TIA, vol. 4, n.º 1, pp. 147–150, may 2016.

[2] M. Barata and J. Bernardino, "Cassandra's performance and scalability evaluation," in Proc. 5th Int. Conf. Data Management Technologies and Applications (DATA), 2016, pp. 127-134, doi: 10.5220/0005980101270134.

[3] A. Gorbenko, A. Romanovsky, and O. Tarasyuk, "Interplaying Cassandra NoSQL consistency and performance: A benchmarking approach," in Dependable Computing – EDCC 2020 Workshops (Communications in Computer and Information Science, vol. 1279), 2020, pp. 168-184, doi: 10.1007/978-3-030-58462-7_14.

[4] Á. H. Santamaría Masapuncho y M. M. Bayas Altamirano, «Monitoreo y evaluación de parámetros de calidad de agua obtenidos por la Internet de las cosas (IoT) para la planta de tratamiento de agua potable el carrizal, perteneciente a la parroquia San Miguel, del Cantón Salcedo, provincia de Cotopaxi», Rev. InGlobal, vol. 4, n.º 2, pp. 280-300, nov. 2025, doi: 10.62943/rig.v4n2.2025.380.

[5] J. Llanos Fariña, «Implementación de un sistema de almacenamiento de datos masivos para monitoreo estructural», Memoria de título, Dept. Ing. Informática, Univ. de Concepción, Concepción, Chile, 2018.

---
> **Nota:** El documento final oficial con la diagramación de dos columnas del formato IEEE y gráficos detallados se encuentra en edición y será adjuntado en esta misma carpeta en formato PDF/Word.
