\## VI. Pruebas



Las pruebas se ejecutaron en una laptop con Windows 11 Home, procesador Intel Core i7-1065G7 (4 núcleos, 8 hilos) y 8 GB de RAM, con Docker Desktop asignando 3.7 GiB. Cassandra 5.0.9 corrió en un solo nodo con SimpleStrategy y factor de replicación 1. Se midió con dos configuraciones del contenedor: uno propio (heap máximo de 1 904 MB) y el definido en `docker-compose.yml` (heap de 1 024 MB).



Se realizaron seis tipos de prueba, todos reproducibles desde el repositorio:

1\. \*\*Carga masiva:\*\* carga de 1 000 000 de mediciones con batches de 50 filas, concurrencia 32 y buffer de 20 000, verificando el total con `performance/verificar\_carga.py`.

2\. \*\*Recuperación:\*\* reinicio del contenedor (`docker restart`) y medición del tiempo hasta aceptar consultas, seguido de una verificación de los datos.

3\. \*\*Latencia de lectura:\*\* ocho consultas con 30 repeticiones y 5 de calentamiento, usando sentencias preparadas, y reportando mediana y percentil 95.

4\. \*\*Estrés:\*\* `cassandra-stress` con un perfil propio (`performance/stress\_test.yaml`) en un keyspace aparte, con 4, 8, 16 y 32 hilos y 50 000 operaciones por nivel.

5\. \*\*Funcionales:\*\* nueve pruebas sobre el esquema y las consultas (`tests/test\_consultas.py`).

6\. \*\*Concurrencia:\*\* tres pruebas con hilos en un keyspace aparte (`tests/test\_concurrencia.py`).



\## VII. Resultados



\*\*Carga masiva.\*\* Con la versión inicial del generador, cuatro cargas del millón en el contenedor propio tardaron en promedio 149.8 s (desviación estándar 11.7 s; 6 706 filas/s). En el entorno del compose, la carga tardó 143.8 s con el generador inicial y 126.0 s con el generador de `main`. Todas las cargas completadas se verificaron con 1 000 000 de filas. Las cargas de la tarde fueron más lentas (183 a 288 s), por lo que el rendimiento depende del estado del equipo. Una carga con el motor `asyncio` falló por `WriteTimeout`, porque el cargador no reintenta escrituras fallidas.



\*\*Recuperación.\*\* El tiempo hasta aceptar consultas fue de 67.0, 31.9 y 24.3 s (mediana 31.9 s); el primero corresponde a un arranque en frío. Tras los reinicios, los 1 000 000 de filas seguían intactos. Al ser un solo nodo, el servicio no responde durante ese tiempo.



\*\*Latencia de lectura.\*\* Las consultas por una sola partición respondieron en 4 a 7 ms (mediana, desde Python). Con el generador de `main`, la consulta por zona y día devolvió unas 13 000 filas y tardó 201 ms (p95: 316 ms), contra 39 ms con el generador inicial. El servidor midió una latencia de lectura de 0.64 ms (mediana), por lo que la diferencia con el cliente se atribuye al driver y a la red de Docker.



\*\*Estrés.\*\* De 4 a 32 hilos, las escrituras subieron de 1 163 a 2 347 op/s y su latencia p99 de 13.7 a 100.7 ms. Las lecturas por sensor y día subieron de 1 828 a 3 725 op/s, y las de las últimas diez lecturas de 2 108 a 5 106 op/s. No hubo errores en ninguna corrida.



\*\*Particiones.\*\* Con el generador inicial, las particiones por sensor y día pesaron como máximo 2 299 bytes y las de zona y día 126 934 bytes. Con el generador de `main`, 6 866 y 943 127 bytes. En ambos casos están muy por debajo de la referencia de 100 MB, aunque la tabla por zona concentra las escrituras de cada zona en pocas particiones.



\*\*Pruebas funcionales y de concurrencia.\*\* Con el generador inicial pasaron las 9 pruebas funcionales. Con el de `main` pasan 8: la de cantidad de zonas detecta que se generan 7 y no las 20 que exige el caso. Las 3 pruebas de concurrencia pasaron: no se pierden escrituras con 8 hilos y una misma clave queda con una sola fila.



\*\*Limitaciones.\*\* Un solo nodo con factor de replicación 1, datos sintéticos, y `cassandra-stress` ejecutándose dentro del mismo contenedor, por lo que comparte CPU y memoria con la base de datos.

