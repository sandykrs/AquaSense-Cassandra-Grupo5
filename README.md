
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
```

2. Levantar el contenedor de Cassandra:
```bash
docker-compose up -d
```

3. Crear el esquema de la base de datos:
```bash
docker exec -it aquasense cqlsh -f /database/schema/schema.cql
```

4. Generación y Carga de datos:
```bash
docker exec -it aquasense bash -c "python3 /data/generate_data.py && python3 /data/load_data.py"
```

## Prueba y demostración

Para ejecutar las consultas requeridas y verificar los resultados:

1. Consultar últimas lecturas de un sensor / rango temporal:
```bash
docker exec -it aquasense cqlsh -f /database/queries/consultas_sensor.cql
```

2. Consultar métricas por zona y periodo:
```bash
docker exec -it aquasense cqlsh -f /database/queries/consultas_zona.cql
```

3. Detección de lecturas anómalas:
```bash
docker exec -it aquasense cqlsh -f /database/queries/consultas_anomalias.cql
```

4. Consulta de resumen agregado:
```bash
docker exec -it aquasense cqlsh -f /database/queries/consultas_resumen.cql
```
Luego, ejecutar cada consulta según el requisito del caso:

| Requisito del caso | Archivo |
|---|---|
| Últimas lecturas de un sensor / rango temporal | `database/queries/consultas_sensor.cql` |
| Consulta por zona y periodo | `database/queries/consultas_zona.cql` |
| Detección de lecturas anómalas | `database/queries/consultas_anomalias.cql` |
| Consulta o tabla de resumen agregado | `database/queries/consultas_resumen.cql` |

