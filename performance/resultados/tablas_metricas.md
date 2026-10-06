\# Métricas de rendimiento (AquaSense CR, Apache Cassandra, un nodo)



\## 1. Entorno de las mediciones

| Componente | Valor |

|---|---|

| Equipo | Windows 11 Home, Intel Core i7-1065G7 (4 núcleos, 8 hilos), 7 959 MB de RAM |

| Docker | 29.8.1, con 8 CPUs y 3.711 GiB de memoria |

| Cassandra | 5.0.9, un nodo, contenedor `cassandra` (imagen cassandra:5.0) |

| Heap de la JVM | máximo de 1 904 MB (valor automático) |

| Replicación | SimpleStrategy, factor 1 |



Nota: `docker-compose.yml` fija `MAX\_HEAP\_SIZE=1G` y el contenedor `aquasense`. Estas mediciones se hicieron con el contenedor `cassandra` y el heap automático.



\## 2. Carga masiva de 1 000 000 de mediciones

Cargador con batches de 50 filas, concurrencia 32 y buffer de 20 000. En todas las cargas: 15 176 anomalías (1.52 %) y 104 909 batches.



| # | Fecha | Motor | Tiempo (s) | Filas/s | Nota |

|---|---|---|---|---|---|

| 1 | 4 oct | asyncore | 166.4 | 6 008 | |

| 2 | 5 oct, mañana | asyncore | 148.0 | 6 759 | |

| 3 | 5 oct, mañana | asyncore | 139.0 | 7 195 | carga adicional, sin salida guardada |

| 4 | 5 oct, mañana | asyncore | 145.7 | 6 862 | |

| 5 | 5 oct, tarde | asyncio | 233.4 | 4 285 | |

| 6 | 5 oct, tarde | asyncio | 287.6 | 3 477 | |

| 7 | 5 oct, tarde | asyncore | 194.5 | 5 140 | |

| 8 | 5 oct, tarde | asyncio | 237.0 | 4 220 | |

| 9 | 5 oct, tarde | asyncore | 183.2 | 5 457 | |

| 10 | 5 oct, tarde | asyncio | 186.5 | 5 361 | tras borrar snapshots |

| 11 | 6 oct | asyncore | 139.5 | 7 168 | cargador final tras el merge con main |



Una carga adicional con asyncio falló por `WriteTimeout` cerca de las 180 000 filas (el cargador no reintenta escrituras fallidas). Todas las cargas completadas se verificaron con 1 000 000 de filas.



| Grupo | Corridas | Tiempo medio (s) | Desv. est. | Filas/s medias |

|---|---|---|---|---|

| Mañana, asyncore (1 a 4) | 4 | 149.8 | 11.7 | 6 706 |

| Tarde, asyncore | 2 | 188.9 | | |

| Tarde, asyncio | 4 | 236.1 | 41.3 | |



Sin la carga adicional (#3), la mañana da 153.4 s (desv. 11.3). Las cargas de la tarde fueron más lentas que las de la mañana con el mismo motor, y la variación entre corridas es grande, por lo que la comparación entre motores no es concluyente.



\## 3. Recuperación tras reinicio (`docker restart`)

| Reinicio | Tiempo hasta aceptar consultas |

|---|---|

| 1 (arranque en frío) | 67.0 s |

| 2 | 31.9 s |

| 3 | 24.3 s |



Mediana 31.9 s; media 41.1 s (desv. 22.8). Tras los reinicios, los 1 000 000 de filas seguían intactos.



\## 4. Latencia de lectura desde Python (30 repeticiones, 5 de calentamiento, sentencias preparadas)

| Consulta | Filas | asyncore p50 / p95 (ms) | asyncio p50 / p95 (ms) |

|---|---|---|---|

| Última lectura de un sensor | 1 | 15.57 / 17.20 | 4.01 / 4.98 |

| Últimas 10 lecturas de un sensor | 10 | 15.74 / 18.61 | 4.43 / 5.01 |

| Sensor y 1 día | 34 | 15.84 / 16.99 | 4.58 / 6.49 |

| Sensor y 7 días | 233 | 17.31 / 42.53 | 12.17 / 17.26 |

| Zona y 1 día | 1 675 | 51.66 / 66.88 | 39.07 / 50.74 |

| Anomalías de un sensor | 1.4 | 15.99 / 17.04 | 3.93 / 4.75 |

| Anomalías de una zona | 25.3 | 15.82 / 18.49 | 4.91 / 5.90 |

| Resumen diario de una zona (7 días) | 7 | 15.87 / 17.29 | 3.93 / 6.90 |



Del lado del servidor (`nodetool tablehistograms`, acumulado desde el último reinicio): lectura p50 0.64 ms y p95 1.11 ms.



\## 5. Particiones

| Tabla | Particiones | Filas por partición | Tamaño |

|---|---|---|---|

| lecturas\_por\_sensor (sensor y día) | 30 000 | 33 a 34 | máximo 2 299 bytes |

| lecturas\_por\_zona (zona y día) | 600 (estimación) | unas 1 670 | 105 779 a 126 934 bytes |



\## 6. Stress test (cassandra-stress, 50 000 operaciones por nivel, 0 errores)

Perfil `stress\_test.yaml` en un keyspace aparte. Cada operación inserta o lee una partición de 33 filas.



| Hilos | Escritura op/s | Filas/s | Media (ms) | p95 | p99 |

|---|---|---|---|---|---|

| 4 | 1 163 | 38 381 | 3.3 | 7.1 | 13.7 |

| 8 | 1 389 | 45 851 | 5.6 | 13.1 | 27.1 |

| 16 | 1 685 | 55 609 | 9.4 | 23.7 | 62.0 |

| 32 | 2 347 | 77 444 | 13.0 | 31.1 | 100.7 |



| Hilos | Por sensor y día op/s | Media / p95 / p99 (ms) | Últimas 10 op/s | Media / p95 / p99 (ms) |

|---|---|---|---|---|

| 4 | 1 828 | 2.1 / 4.7 / 7.9 | 2 108 | 1.8 / 3.7 / 8.6 |

| 8 | 2 958 | 2.6 / 5.6 / 10.4 | 4 147 | 1.8 / 3.9 / 6.8 |

| 16 | 3 120 | 5.0 / 12.2 / 18.9 | 3 791 | 4.0 / 11.4 / 20.5 |

| 32 | 3 725 | 8.4 / 20.4 / 32.4 | 5 106 | 5.8 / 15.6 / 26.2 |



Validación: con 4 hilos, 60 328 filas/s entre 1 828 op/s da 33 filas por operación, así que las lecturas encontraron particiones completas.



\## 7. Pruebas funcionales

\- 9 pruebas de consultas: todas correctas (incluye que una consulta sin clave de partición es rechazada).

\- 3 pruebas de concurrencia en un keyspace aparte: todas correctas (27.1 s).



\## 8. Limitaciones a declarar

\- Un solo nodo con factor de replicación 1: no hay tolerancia a fallas ni se prueba la consistencia entre réplicas.

\- Datos sintéticos de 30 días, con particiones muy parejas.

\- cassandra-stress corre dentro del mismo contenedor, así que comparte CPU y memoria con Cassandra.

\- Por el diseño del perfil (30 000 particiones posibles), muchas escrituras del stress sobrescriben particiones existentes.

\- Las filas/s del stress (una tabla) no son comparables con las del cargador (varias tablas por medición).

\- Las cargas varían mucho según el estado de la laptop (139 a 288 s).

