
# AquaSense CR - Monitoreo de Redes de Agua Potable

**Curso:** XS0131 Gestión de Bases de Datos y Análisis de Información  
**Universidad de Costa Rica - Escuela de Estadística**  
**Modelo NoSQL:** Columnas Anchas (Wide-Column)  
**Tecnología:** Apache Cassandra  

## Integrantes - Grupo 5
* Sandy
* Keylor
* Jimena
* Jefferson
* Estefanía

## Descripción del Proyecto
AquaSense CR es un sistema diseñado para monitorear redes de agua potable mediante sensores de caudal, presión, temperatura y calidad. Este repositorio contiene la implementación de una capa de datos de alta velocidad en **Apache Cassandra** capaz de soportar la ingesta continua de datos de telemetría y consultar eficientemente series de tiempo por sensor y por intervalo.

## Prerrequisitos
Para ejecutar este proyecto de forma local se requiere:
* **Docker Desktop** 
* **Python 3.10+**
* Cliente `cqlsh`
## Instalación
1. Clonar el repositorio y entrar a la carpeta:
   ```bash
   git clone [https://github.com/sandykrs/AquaSense-Cassandra-Grupo5.git](https://github.com/sandykrs/AquaSense-Cassandra-Grupo5.git)
   cd AquaSense-Cassandra-Grupo5
## Carga de datos
Para generar y cargar el millón de mediciones sintéticas:

```bash
python data/generate_data.py
python data/load_data.py
```
## Prueba y demostración
Primero, crear las tablas en Cassandra:

```bash
docker exec -it cassandra cqlsh -f database/schema/schema.cql
```

Luego, ejecutar cada consulta según el requisito del caso:

| Requisito del caso | Archivo |
|---|---|
| Últimas lecturas de un sensor / rango temporal | `database/queries/consultas_sensor.cql` |
| Consulta por zona y periodo | `database/queries/consultas_zona.cql` |
| Detección de lecturas anómalas | `database/queries/consultas_anomalias.cql` |
| Consulta o tabla de resumen agregado | `database/queries/consultas_resumen.cql` |

## Pruebas, benchmarks y métricas

Con Cassandra encendida y los datos cargados (ver "Carga de datos"):

```bash
pip install cassandra-driver pyasyncore
python performance/verificar_carga.py     # verifica 1 000 000 de filas y las particiones
python tests/test_consultas.py            # 9 pruebas funcionales de consultas
python tests/test_concurrencia.py         # 3 pruebas de concurrencia (keyspace aparte)
python performance/benchmark_lectura.py   # latencia p50 y p95 de 8 consultas
```

`pyasyncore` solo hace falta con Python 3.12 o más nuevo.

**Benchmark de escritura.** Vacía las tablas y recarga el millón de mediciones en cada corrida, por lo que **borra los datos existentes**:

```bash
python performance/benchmark_escritura.py --corridas 3
```

**Stress test (`cassandra-stress`).** Usa un keyspace aparte (`aquasense_stress`) y no toca los datos del proyecto. Reemplace `NOMBRE_CONTENEDOR` por el nombre que muestra `docker ps`:

```bash
docker cp performance/stress_test.yaml NOMBRE_CONTENEDOR:/tmp/stress_test.yaml
docker exec NOMBRE_CONTENEDOR /opt/cassandra/tools/bin/cassandra-stress user profile=/tmp/stress_test.yaml n=50000 "ops(insert=1)" no-warmup -rate threads=8
docker exec NOMBRE_CONTENEDOR cqlsh -e "DROP KEYSPACE IF EXISTS aquasense_stress;"
```

Los resultados medidos están en `performance/resultados/`; el resumen es `tablas_metricas.md`.
