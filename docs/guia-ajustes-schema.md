# Guía de Ajustes al Schema - AquaSense CR

**Grupo:** 5  
**Tecnología:** Apache Cassandra 5.0.9  
**Autores:** Jeferson Salazar, Sandy Ruiz, Jimena Díaz, Estafanía Núñez, Keylor Gómez

---

## 1. Cuándo ajustar el schema

En Cassandra, ajustar el schema es costoso porque no se pueden modificar partition keys ni clustering keys de una tabla existente. Los ajustes se hacen creando una tabla nueva y migrando los datos.

Se debe considerar un ajuste cuando:

- Una consulta requiere `ALLOW FILTERING`.
- Una partición supera los 100 MB.
- Se detecta un hotspot evidente en una zona o sensor.
- Cambia la frecuencia de ingesta (por ejemplo, de diaria a horaria).
- Aparecen nuevas consultas no cubiertas por el diseño actual.

---

## 2. Cómo ajustar correctamente

### 2.1 Proceso general

1. **Identificar el problema:** latencia alta, error de query, hotspot.
2. **Diseñar la tabla corregida** con las nuevas partition/clustering keys.
3. **Crear la tabla nueva** con otro nombre (por ejemplo, `sensor_readings_v2`).
4. **Migrar datos** con un script (Spark o Python con driver cassandra-driver).
5. **Actualizar la aplicación** para escribir y leer de la tabla nueva.
6. **Eliminar la tabla antigua** solo cuando ya no se use.
7. **Actualizar la documentación.**

### 2.2 Cosas que NO se pueden cambiar

- Partition key de una tabla existente.
- Clustering key de una tabla existente.
- Tipo de dato de una partition o clustering key.

### 2.3 Cosas que SÍ se pueden cambiar sin migrar

- Añadir columnas nuevas.
- Eliminar columnas (aunque no se recomienda).
- Cambiar propiedades de compactación.
- Añadir o modificar índices secundarios.

---

## 3. Ajustes comunes y sus soluciones

| Problema | Síntoma | Solución |
|---|---|---|
| Partición muy grande | Timeout en lecturas, OutOfMemory en nodos | Cambiar bucket diario a horario |
| Hotspot por zona | Un nodo con más carga que otros | Añadir shard a la partition key |
| Consulta por rango cruza buckets | Múltiples queries a distintos buckets | Iterar por bucket en la aplicación |
| Consulta no soportada | Requiere ALLOW FILTERING | Crear tabla específica para esa consulta |
| Frecuencia de ingesta aumentó | Particiones crecen muy rápido | Reducir el tamaño del bucket (día → hora) |

---

## 4. Ejemplo: cambiar bucket diario a horario

Si un sensor genera muchas más lecturas de las previstas, se puede reducir el bucket:

```cql
-- Tabla original
CREATE TABLE sensor_readings (
  sensor_id uuid,
  bucket date,
  ts timestamp,
  ...
  PRIMARY KEY ((sensor_id, bucket), ts)
);

-- Tabla ajustada
CREATE TABLE sensor_readings_v2 (
  sensor_id uuid,
  bucket_hour text,  -- formato 'YYYY-MM-DD-HH'
  ts timestamp,
  ...
  PRIMARY KEY ((sensor_id, bucket_hour), ts)
);