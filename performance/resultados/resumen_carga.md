\# Resumen de carga masiva (1 000 000 de mediciones)



Configuración del cargador: batches de hasta 50 filas, 32 operaciones concurrentes.

Entorno: ver entorno.md. Cassandra 5.0.9 en un solo nodo, con 3.7 GiB de memoria asignada a Docker.



| Corrida | Tiempo (s) | Velocidad (filas/s) | Anomalías | Batches |

|---|---|---|---|---|

| 1 | 166.4 | 6 008 | 15 176 | 104 909 |

| 2 | 148.0 | 6 759 | 15 176 | 104 909 |

| 3 | 145.7 | 6 862 | 15 176 | 104 909 |

| Promedio | 153.4 | 6 543 | | |

| Desviación estándar | 11.4 | 466 | | |



Verificación (verificar\_carga.py) en las tres corridas: 1 000 000 de filas, 15 176 anómalas (1.52 %), 30 000 particiones, entre 33 y 34 filas por partición.



Notas:

\- La velocidad cuenta mediciones por segundo, no escrituras totales a todas las tablas.

\- Cada corrida se hizo con las tablas vacías.

