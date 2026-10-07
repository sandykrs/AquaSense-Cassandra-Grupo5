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
Las organizaciones que operan infraestructuras críticas, como las redes de distribución de agua potable, enfrentan hoy un crecimiento constante en el volumen de datos generados por sus procesos de monitoreo. Esta tendencia ha impulsado la adopción de bases de datos NoSQL, una alternativa que surge frente a las limitaciones de escalabilidad y flexibilidad de esquema que presentan los modelos relacionales tradicionales cuando deben gestionar grandes volúmenes de información [1].

AquaSense CR es una empresa que monitorea redes de agua potable mediante sensores de caudal, presión, temperatura y calidad instalados en distintas zonas de su infraestructura. Estos dispositivos generan lecturas de forma continua, lo que exige un sistema de almacenamiento capaz de absorber una alta frecuencia de escritura sin degradar su desempeño, además de permitir consultas rápidas de series de tiempo por sensor y por intervalo, incluso cuando el volumen histórico de datos crece de manera sostenida durante meses de operación.

Esta problemática no es exclusiva de AquaSense CR. Experiencias similares en plantas de tratamiento de agua potable muestran que los sistemas de monitoreo manual o discontinuo limitan la capacidad de detectar cambios repentinos en los parámetros críticos y dificultan el ajuste oportuno de los procesos operativos [4]. La digitalización de estas infraestructuras mediante sensores y sistemas de almacenamiento especializados representa, por tanto, una alternativa viable para superar dichas limitaciones.

Los modelos de bases de datos relacionales, al estar optimizados para transacciones estructuradas y consultas complejas mediante uniones (joins) entre tablas, no están diseñados para sostener cargas de escritura masivas y continuas como las que produce una red de sensores de monitoreo. Casos de uso similares, como el almacenamiento de datos de telemetría para el monitoreo estructural de infraestructuras, han optado por bases de datos especializadas en grandes volúmenes de datos, evidenciando que los sistemas NoSQL de tipo columnas anchas se ajustan particularmente bien a necesidades de ingestión intensiva y consulta eficiente por rangos temporales [5].

En este contexto, el presente trabajo tiene como objetivo diseñar e implementar una solución de datos basada en el modelo de columnas anchas, utilizando Apache Cassandra, que permita a AquaSense CR ingerir de forma continua las lecturas de sus sensores, consultar eficientemente por sensor, zona y rango de tiempo, y mantener un desempeño estable y escalable a medida que el volumen de datos crece. La selección de esta tecnología se sustenta en evaluaciones previas de rendimiento y escalabilidad de Cassandra [2], así como en estudios sobre el comportamiento de su modelo de consistencia ajustable frente a distintas cargas de trabajo [3], aspectos que se detallan en las secciones siguientes.

## II. Fundamentos del Modelo NoSQL (Columnas Anchas)
Las bases de datos NoSQL aparecieron como solución a la necesidad de manejar volúmenes de datos crecientes y con estructuras más diversas, en situaciones donde el modelo relacional clásico muestra limitaciones de escalabilidad y rigidez de esquema [1]. A diferencia de las bases de datos relacionales, que estructuran la información en tablas con un esquema rígido y relaciones establecidas, las bases de datos NoSQL se enfocan en la distribución horizontal de los datos y permiten estructuras más versátiles, ajustadas a las necesidades particulares de cada aplicación.

En la clasificación de bases de datos NoSQL, el modelo de columnas anchas (wide-column) se distingue por estructurar la información en filas identificadas por una clave, donde cada fila puede tener un número variable de columnas agrupadas en familias de columnas [2]. A diferencia de una tabla relacional tradicional, no es imprescindible que todas las filas tengan la misma estructura de columnas, lo que proporciona flexibilidad al modelo sin perder la organización tabular.

El componente principal del diseño en este tipo de bases de datos es la clave de partición, que establece en qué nodo del clúster se guarda físicamente cada fila, y la clave de ordenamiento o clustering key, que establece el orden en que los datos se almacenan dentro de una misma partición. Esta combinación facilita que las consultas por rango —por ejemplo, todas las lecturas de un sensor en un periodo específico— se resuelvan accediendo directamente a los datos pertinentes, sin tener que recorrer toda la base de datos [2].

A diferencia de los sistemas relacionales, en un modelo de columnas anchas el diseño de las tablas se basa en las consultas que la aplicación debe satisfacer (diseño basado en consultas), en lugar de normalizar los datos según las relaciones entre las entidades. Esto significa que, en numerosas ocasiones, es fundamental replicar datos en varias tablas para mejorar diferentes patrones de acceso, una práctica que en el modelo relacional se vería como un incumplimiento de las formas normales, pero que en este contexto es beneficiosa para aumentar la eficiencia de lectura.

Respecto a la consistencia de los datos, las bases de datos de columnas anchas como Apache Cassandra no proporcionan por defecto una consistencia inmediata entre replicas, sino que permiten niveles de consistencia configurables de acuerdo con las necesidades de la aplicación. Esta propiedad, denominada consistencia eventual, permite equilibrar la disponibilidad y el rendimiento del sistema en relación a la precisión total de los datos en todo momento, y su configuración influye de manera directa y cuantificable en la latencia y el throughput del sistema [3].

Finalmente, la escalabilidad horizontal es una característica esencial de este modelo: el sistema puede expandirse incorporando más nodos al clúster, sin que esto requiera interrupciones en el servicio ni una reconfiguración manual complicada, lo que es especialmente importante para aplicaciones que, como el monitoreo de sensores, producen volúmenes de datos en aumento de manera continua a lo largo del tiempo [5].


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
