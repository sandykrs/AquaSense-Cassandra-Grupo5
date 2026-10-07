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
Para la implementación de la solución, se optó por Apache Cassandra, una base de datos de código abierto NoSQL que claramente se enmarca en el modelo de columnas anchas, diseñada para manejar grandes volúmenes de datos a través de múltiples nodos sin un punto único de fallo. Su arquitectura de tipo peer-to-peer, sin un nodo maestro, elimina los puntos únicos de fallo y permite que cualquier nodo dentro del clúster gestione solicitudes tanto de lectura como de escritura, lo que la hace ideal para un sistema de monitoreo que necesita funcionar de manera continua [2].

Originalmente desarrollada en Facebook y liberada como proyecto open source en 2008, hoy es mantenida por la Apache Software Foundation.

Sus características principales son:

- **Arquitectura peer-to-peer:** todos los nodos son iguales, sin maestro.
- **Escalabilidad horizontal lineal:** agregar nodos aumenta la capacidad proporcionalmente.
- **Alta disponibilidad:** replicación configurable y sin downtime.
- **Consistencia ajustable:** desde ONE hasta ALL.
- **Modelo wide-column:** ideal para series de tiempo.
- **CQL (Cassandra Query Language):** sintaxis similar a SQL.

### B. Justificación de la elección

La selección de Cassandra en lugar de otras opciones de columnas anchas está respaldada por varios factores. Primero, las pruebas experimentales de rendimiento indican que la base de datos se escala favorablemente al incrementar el número de nodos, mejorando notablemente los tiempos de respuesta en cargas de lectura y escritura con grandes volúmenes de datos [2]. En segundo lugar, su modelo de consistencia ajustable (configurable a través de niveles como ONE, QUORUM o ALL) permite encontrar un balance entre la disponibilidad del sistema y la precisión de los datos ofrecidos, lo que es una elección de diseño que afecta directamente el rendimiento observado en las evaluaciones [3].

| Alternativa | Motivo del descarte |
|---|---|
| ScyllaDB | Compatible con CQL, pero con menos documentación y comunidad más pequeña. |
| Apache HBase | Requiere Hadoop y Zookeeper; mayor complejidad operativa. |
| Google Cloud Bigtable | Dependencia de la nube; el proyecto debe ser reproducible localmente. |
| **Apache Cassandra** | **Elegida:** open source, madura, ampliamente documentada, fácil de levantar con Docker. |

Además, Cassandra es gratuita y de código abierto bajo la licencia Apache 2.0, y se puede desplegar de manera reproducible utilizando contenedores Docker en cualquier sistema operativo que soporte dicha tecnología, cumpliendo así con el requerimiento de que la solución funcione sin depender de licencias costosas ni de credenciales privadas.

### C. Versión y entorno
Versión utilizada: se utilizó Apache Cassandra 5.0.9, desplegada mediante Docker en un contenedor único (clúster "AquaSenseCluster"). Para el entorno de desarrollo se empleó la estrategia de replicación SimpleStrategy con factor de replicación 1; para un entorno de producción se documenta el uso recomendado de NetworkTopologyStrategy con factor de replicación 3  (RF=3).

---

## IV. Modelo y Arquitectura

### A. Filosofía de modelado

Cassandra es **query-driven**: las tablas se diseñan a partir de las consultas, no de un modelo normalizado. Cada consulta frecuente tiene su propia tabla desnormalizada, ya que Cassandra no soporta joins eficientes.

Este método sugiere que, antes de crear cualquier tabla, es esencial determinar con exactitud los patrones de acceso que la aplicación deberá manejar. Para AquaSense CR, esos patrones se relacionan con los siete requisitos esenciales establecidos para el caso: verificación de lecturas recientes por sensor, consulta por área y tiempo, identificación de anomalías, y creación de resúmenes consolidados, entre otros.

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

Como se puede notar, las tablas lecturas_por_sensor y lecturas_por_zona abordan el mismo tipo de datos (las lecturas de los sensores), aunque divididas según dos criterios de acceso diferentes. Esta intencionada repetición de datos (una acción que se evitaría) en un modelo relacional normalizado es justo lo que permite que ambas consultas (por sensor y por zona) se atiendan con acceso directo a la partición correspondiente, sin requerir operaciones adicionales de filtrado o combinación entre tablas [2].

### C. Decisiones clave de diseño

1. **Bucketing diario:** el campo `bucket` (tipo `date`) agrupa las lecturas por día para evitar particiones gigantes.
2. **Clustering DESC:** las últimas lecturas se devuelven primero sin ordenamiento adicional.
3. **TimeWindowCompactionStrategy (TWCS):** agrupa SSTables por ventana de 1 día, óptimo para series de tiempo.
4. **Desnormalización:** cada lectura se escribe en `lecturas_por_sensor` y `lecturas_por_zona`, aceptando el costo de escritura a cambio de lecturas rápidas.
5. **Tablas dedicadas para anomalías:** evitan el uso de `ALLOW FILTERING`.

El primer punto (bucketing diario) requiere atención especial, pues aborda directamente uno de los requisitos explícitos del caso: prevenir que una partición acumule un volumen de datos excesivo a medida que se expande el historial de mediciones. Sin este mecanismo, una partición definida exclusivamente por sensor_id o por zona se expandiría de manera indefinida con el tiempo, perjudicando el rendimiento de lectura de esa partición en particular [2].

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

Es fundamental señalar que estas características de replicación y resistencia a fallos se refieren a la configuración sugerida para un entorno de producción (RF=3 de varios nodos). El entorno de pruebas empleado en este proyecto funciona con un solo nodo y un factor de replicación de 1, una configuración idónea para el desarrollo reproducible en una única máquina, aunque no permite evidenciar experimentalmente esas capacidades de replicación, esta restricción se aborda en la Sección VIII.

diagrama ¿?

## V. Implementación

Se desarrolló un generador (data/generate_data.py) que genera datos sintéticos de forma reproducible utilizando una semilla constante, simulando 1000 sensores distribuidos en 7 áreas que corresponden a provincias de Costa Rica, con un volumen mínimo de 1 000 000 de mediciones y un porcentaje fijo del 2% de lecturas anómalas incluidas intencionalmente para validar su detección posterior. El generador también recrea un patrón de consumo diario realista, modificando el caudal según la hora del día a través de una función senoidal que imita una mayor demanda durante el día y una menor en la madrugada.

La carga de datos (data/load_data.py) se llevó a cabo a través de ingesta asíncrona mediante execute_concurrent del controlador oficial de Cassandra para Python, con un nivel de concurrencia ajustable (32 operaciones simultáneas por defecto). Las escrituras se llevan a cabo mediante sentencias preparadas (prepared statements) organizadas en lotes no registrados (UNLOGGED batches) de tamaño ajustable (50 filas por defecto), que se acumulan en un búfer antes de ser enviados al clúster (20 000 filas por defecto). Esta mezcla de métodos disminuye notablemente la carga de comunicación con el clúster en comparación con inserciones individuales síncronas, alineándose con las sugerencias de la literatura sobre el rendimiento de Cassandra en contextos de escritura intensiva [2].

Las consultas correspondientes a cada requisito del caso se implementaron en los archivos database/queries/consultas_sensor.cql, consultas_zona.cql, consultas_anomalias.cql y consultas_resumen.cql, ejecutadas a través de la consola cqlsh del clúster.

Las lecturas anómalas se producen a través de una probabilidad constante del 2% que se aplica a cada medición simulada. Cuando una medición se identifica como anómala, se le asigna de manera aleatoria uno de seis tipos posibles de anomalía: fuga, baja presión, alta presión, temperatura elevada, caudal irregular, o mala calidad. Cada clase de anomalía altera los valores de caudal, presión y temperatura de manera realista; por ejemplo, una fuga aumenta el caudal de 1.6 a 2.5 veces su valor original y disminuye la presión entre un 30% y un 60%. Este campo booleano (anomalia) se guarda directamente en las tablas de lecturas y se replica en las tablas específicas de anomalías (anomalias_por_sensor, anomalias_por_zona), lo que elimina la necesidad de la operación ALLOW FILTERING.

## VI. Pruebas y Resultados

## VII. Limitaciones 
El clúster de pruebas se implementó con un solo nodo y una estrategia de replicación SimpleStrategy cuyo factor de replicación es 1. Esta configuración es apropiada para un ambiente de desarrollo reproducible en una única máquina, sin embargo, no permite evidenciar experimentalmente las capacidades de replicación y tolerancia a fallos de nodo que proporciona Cassandra en un despliegue distribuido de producción con varios nodos (para lo cual se sugiere, como trabajo futuro, el uso de NetworkTopologyStrategy con un factor de replicación de 3).

Igualmente, las pruebas de rendimiento se llevaron a cabo en una sola máquina de desarrollo, por lo que los resultados obtenidos representan el comportamiento del sistema bajo esas condiciones particulares de hardware, y podrían cambiar en un entorno de producción con recursos asignados.

## VIII. Conclusiones

## IX. Referencias

[1] H. A. Herrera y C. Rueda Valenzuela, «NoSQL, la nueva tendencia en el manejo de datos», Tecnol. Investig. Academia TIA, vol. 4, n.º 1, pp. 147–150, may 2016.

[2] M. Barata and J. Bernardino, "Cassandra's performance and scalability evaluation," in Proc. 5th Int. Conf. Data Management Technologies and Applications (DATA), 2016, pp. 127-134, doi: 10.5220/0005980101270134.

[3] A. Gorbenko, A. Romanovsky, and O. Tarasyuk, "Interplaying Cassandra NoSQL consistency and performance: A benchmarking approach," in Dependable Computing – EDCC 2020 Workshops (Communications in Computer and Information Science, vol. 1279), 2020, pp. 168-184, doi: 10.1007/978-3-030-58462-7_14.

[4] Á. H. Santamaría Masapuncho y M. M. Bayas Altamirano, «Monitoreo y evaluación de parámetros de calidad de agua obtenidos por la Internet de las cosas (IoT) para la planta de tratamiento de agua potable el carrizal, perteneciente a la parroquia San Miguel, del Cantón Salcedo, provincia de Cotopaxi», Rev. InGlobal, vol. 4, n.º 2, pp. 280-300, nov. 2025, doi: 10.62943/rig.v4n2.2025.380.

[5] J. Llanos Fariña, «Implementación de un sistema de almacenamiento de datos masivos para monitoreo estructural», Memoria de título, Dept. Ing. Informática, Univ. de Concepción, Concepción, Chile, 2018.

## X.Enlace a al repositorio

---
> **Nota:** El documento final oficial con la diagramación de dos columnas del formato IEEE y gráficos detallados se encuentra en edición y será adjuntado en esta misma carpeta en formato PDF/Word.
