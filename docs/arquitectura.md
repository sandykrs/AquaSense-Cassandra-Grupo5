# Arquitectura de la Solución - AquaSense CR

**Proyecto:** XS0131 - Gestión de Bases de Datos y Análisis de Información  
**Caso:** 3 - AquaSense CR (Wide-Column)  
**Grupo:** 5  
**Tecnología:** Apache Cassandra 5.0.9  
**Autores:** Jeferson Salazar, Sandy Ruiz, Jimena Díaz, Estefanía Núñez, Keylor Gómez

> Este documento distingue entre lo que **está implementado y medido** en el repositorio (prototipo de un nodo) y lo que se **propone para producción** pero no se desplegó. Cada sección lo indica.

---

## 1. Visión general

### 1.1 Prototipo implementado (lo que se ejecuta con este repositorio)

```text
+------------------+     +------------------+     +---------------------------+
| generate_data.py | --> |  load_data.py    | --> | Apache Cassandra 5.0.9    |
| (semilla 42)     |     | (cargador Python)|     | 1 nodo, SimpleStrategy RF=1|
| 1 000 sensores   |     | batches de 50,   |     | contenedor `aquasense`    |
| 20 zonas         |     | concurrencia 32  |     | keyspace `aquasense`      |
+------------------+     +------------------+     +-------------+-------------+
                                                                |
                         +--------------------------------------+
                         |
                         v
        +--------------------------------------------+
        | Consultas: cqlsh, queries/consultas.py     |
        | (driver Python) y queries/*.ipynb          |
        | Verificación: performance/verificar_carga.py|
        | Pruebas: tests/ (consultas y concurrencia) |
        +--------------------------------------------+
```

- **Sensores:** 1 000 sensores sintéticos distribuidos en 20 zonas (50 por zona). Alrededor de un 5 % queda inactivo y no genera lecturas.
- **Generador (`data/generate_data.py`):** produce las mediciones en orden de tiempo, con una lectura cada 15 minutos por sensor activo, un ciclo diario de consumo, ruido gaussiano y un 2 % de lecturas anómalas de seis tipos. Con la misma semilla (42) genera siempre los mismos datos.
- **Cargador (`data/load_data.py`):** acumula un buffer de 20 000 filas, las agrupa por partición y las envía como lotes `UNLOGGED` de hasta 50 filas con `execute_concurrent` (32 operaciones simultáneas) y sentencias preparadas.
- **Cassandra:** un solo nodo levantado con `docker-compose.yml` (imagen `cassandra:5.0.9`, contenedor `aquasense`, heap de 1 GB, volumen `cassandra_data`).
- **Consultas:** se ejecutan con `cqlsh` o con el driver de Python (`queries/consultas.py`). No hay una API intermedia.

### 1.2 Arquitectura propuesta para producción (no implementada)

```text
+-------------+     +----------------+     +--------------------------+
| Sensores    | --> | API de ingesta | --> | Cassandra                |
| (1 000+)    |     | (por construir)|     | 3 nodos, RF=3,           |
+-------------+     +----------------+     | NetworkTopologyStrategy  |
                                           +------------+-------------+
                                                        |
                                                        v
                                           +--------------------------+
                                           | API de consultas         |
                                           | + dashboards             |
                                           | (por construir)          |
                                           +--------------------------+
```

La API de ingesta, la API de consultas, los dashboards y el clúster de tres nodos son **trabajo futuro**. El prototipo no los incluye, y las pruebas se hicieron en un único nodo con RF=1.

---

## 2. Flujo de datos

### 2.1 En el prototipo

1. **Catálogo:** el cargador escribe primero `sensores` y `sensores_por_zona`.
2. **Ingesta:** por cada medición escribe en `lecturas_por_sensor` y `lecturas_por_zona`.
3. **Anomalías:** el generador marca cada lectura anómala (`anomalia = true` y un tipo). El cargador la copia además a `anomalias_por_sensor` y `anomalias_por_zona`, con el campo `motivo`.
4. **Resumen y última lectura:** mientras recorre las mediciones, el cargador acumula en memoria los totales por zona y día, y la última lectura de cada sensor. Al terminar escribe `resumen_diario_zona` y `ultima_lectura_sensor`.
5. **Verificación:** `performance/verificar_carga.py` recorre `lecturas_por_sensor` y cuenta filas, anomalías y particiones.
6. **Consulta:** `queries/consultas.py` y `cqlsh` consultan por sensor y día, por zona y día, anomalías, resumen y última lectura.

Los lotes son `UNLOGGED` y por partición, así que **no hay atomicidad entre tablas**: si una carga falla a la mitad, las tablas derivadas pueden quedar desalineadas. Por eso existe la prueba `test_anomalias_coinciden_con_lecturas`, y el cargador no reintenta escrituras fallidas (una carga con el motor `asyncio` falló una vez por `WriteTimeout`).

### 2.2 En producción (propuesta)

En una operación continua, la API escribiría cada lectura en `lecturas_por_sensor`, `lecturas_por_zona` y `ultima_lectura_sensor` (un *upsert*). Las anomalías se detectarían en la ingesta o en un proceso periódico, y `resumen_diario_zona` se recalcularía con un trabajo diario.

---

## 3. Modelo de despliegue

| Componente | Prototipo (implementado) | Producción (propuesta) |
|---|---|---|
| Base de datos | Apache Cassandra 5.0.9, 1 nodo | Apache Cassandra 5.0.9, 3 nodos |
| Replicación | `SimpleStrategy`, RF=1 | `NetworkTopologyStrategy`, RF=3 |
| Compactación | TWCS (ventana de 1 día) en `lecturas_por_sensor` y `lecturas_por_zona` | TWCS en las tablas de lecturas; revisar las demás tablas |
| Cliente | `cqlsh` y driver Python | API de ingesta y de consultas |
| Persistencia | Volumen Docker `cassandra_data` | Volúmenes/discos por nodo |
| Autenticación | No habilitada (sin credenciales en el repositorio) | Autenticación nativa de Cassandra habilitada |

Las tablas `anomalias_*`, `resumen_diario_zona` y `ultima_lectura_sensor` usan la compactación por defecto.

---

## 4. Escalabilidad

- **Horizontal:** Cassandra distribuye las particiones entre los nodos con hash consistente, así que agregar nodos reparte los datos. Esto se explica en el paper, pero **no se demostró** porque el prototipo corre en un solo nodo.
- **Escritura:** el diseño es de solo agregar datos (*append-only*), lo que Cassandra maneja bien. En el prototipo se midieron 7 824 filas/s con el cargador final (varias tablas por medición).
- **Lectura:** cada tabla responde una consulta específica con la partition key completa, sin `ALLOW FILTERING`.
- **Particionado:** `(sensor_id, bucket)` produce particiones pequeñas, de hasta 6.7 KB medidos. `(zona, bucket)` produce particiones mayores, de hasta unos 370 KB medidos (4 579 filas por zona y día).
- **Punto débil conocido:** todas las escrituras de una zona en un día caen en una sola partición, así que solo hay 20 particiones de zona activas a la vez. En un clúster real eso puede concentrar escritura. La mitigación prevista es un bucket horario o un *shard* en la clave (ver `decisiones-diseno.md` y `guia-ajustes-schema.md`).

Las cifras provienen de `performance/resultados/tablas_metricas.md`.

---

## 5. Alta disponibilidad y consistencia

**En el prototipo no se demuestran.** Con un solo nodo y RF=1 no hay réplicas, así que no hay tolerancia a fallos y los niveles de consistencia no se diferencian entre sí. Lo que sí se midió es la recuperación tras reiniciar el contenedor (ver `tablas_metricas.md`).

**Propuesta para producción:**

- Replicación RF=3: cada dato existe en 3 nodos.
- Consistencia ajustable (`ONE`, `QUORUM`, `LOCAL_QUORUM`). Con `QUORUM` se tolera la caída de un nodo.
- `nodetool repair` para sincronizar réplicas.
- No hay punto único de falla: cualquier nodo puede coordinar una consulta.

---

## 6. Seguridad

- El repositorio **no contiene credenciales ni secretos**. El prototipo corre sin autenticación porque es un entorno local de demostración.
- Para producción se habilitaría la autenticación nativa de Cassandra, con las credenciales en variables de entorno (archivo `.env` fuera del repositorio, con un `.env.example` sin secretos).
- Advertencia: `database/schema/schema.cql` empieza con `DROP KEYSPACE IF EXISTS aquasense`. Es intencional para el desarrollo local y **borra los datos** al ejecutarlo.

---

## 7. Reproducibilidad

Los pasos completos están en el `README.md`. Resumen:

```bash
# 1. Levantar Cassandra (desde la raíz del repositorio)
docker compose up -d
docker ps                              # esperar a que diga (healthy)
docker exec aquasense nodetool status  # el nodo debe aparecer como UN

# 2. Crear keyspace y tablas (el schema ya está montado en /schema.cql)
docker exec -it aquasense cqlsh -f /schema.cql

# 3. Cargar 1 000 000 de mediciones (Mac/Linux; en Windows ver el README)
docker run --rm --network container:aquasense -v "$(pwd):/app" -w /app python:3.10 \
  sh -c "pip install cassandra-driver && python data/load_data.py"

# 4. Verificar la carga
pip install cassandra-driver
python performance/verificar_carga.py
```

Para borrar todo y empezar de cero: `docker compose down -v`.
