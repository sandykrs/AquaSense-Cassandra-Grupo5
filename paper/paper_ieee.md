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
Las bases de datos NoSQL aparecieron como solución a la necesidad de manejar volúmenes de datos crecientes y con estructuras más diversas, en situaciones donde el modelo relacional clásico muestra limitaciones de escalabilidad y rigidez de esquema [1]. A diferencia de las bases de datos relacionales, que estructuran la información en tablas con un esquema rígido y relaciones establecidas, las bases de datos NoSQL se enfocan en la distribución horizontal de los datos y permiten estructuras más versátiles, ajustadas a las necesidades particulares de cada aplicación.

En la clasificación de bases de datos NoSQL, el modelo de columnas anchas (wide-column) se distingue por estructurar la información en filas identificadas por una clave, donde cada fila puede tener un número variable de columnas agrupadas en familias de columnas [2]. A diferencia de una tabla relacional tradicional, no es imprescindible que todas las filas tengan la misma estructura de columnas, lo que proporciona flexibilidad al modelo sin perder la organización tabular.

El componente principal del diseño en este tipo de bases de datos es la clave de partición, que establece en qué nodo del clúster se guarda físicamente cada fila, y la clave de ordenamiento o clustering key, que establece el orden en que los datos se almacenan dentro de una misma partición. Esta combinación facilita que las consultas por rango —por ejemplo, todas las lecturas de un sensor en un periodo específico— se resuelvan accediendo directamente a los datos pertinentes, sin tener que recorrer toda la base de datos [2].

A diferencia de los sistemas relacionales, en un modelo de columnas anchas el diseño de las tablas se basa en las consultas que la aplicación debe satisfacer (diseño basado en consultas), en lugar de normalizar los datos según las relaciones entre las entidades. Esto significa que, en numerosas ocasiones, es fundamental replicar datos en varias tablas para mejorar diferentes patrones de acceso, una práctica que en el modelo relacional se vería como un incumplimiento de las formas normales, pero que en este contexto es beneficiosa para aumentar la eficiencia de lectura.

Respecto a la consistencia de los datos, las bases de datos de columnas anchas como Apache Cassandra no proporcionan por defecto una consistencia inmediata entre replicas, sino que permiten niveles de consistencia configurables de acuerdo con las necesidades de la aplicación. Esta propiedad, denominada consistencia eventual, permite equilibrar la disponibilidad y el rendimiento del sistema en relación a la precisión total de los datos en todo momento, y su configuración influye de manera directa y cuantificable en la latencia y el throughput del sistema [3].

Finalmente, la escalabilidad horizontal es una característica esencial de este modelo: el sistema puede expandirse incorporando más nodos al clúster, sin que esto requiera interrupciones en el servicio ni una reconfiguración manual complicada, lo que es especialmente importante para aplicaciones que, como el monitoreo de sensores, producen volúmenes de datos en aumento de manera continua a lo largo del tiempo [5].


## III. Tecnología Seleccionada

## IV. Modelo y Arquitectura

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
