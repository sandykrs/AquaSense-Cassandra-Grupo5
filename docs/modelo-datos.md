# Modelo de Datos - AquaSense CR

**Proyecto:** XS0131 - Gestión de Bases de Datos y Análisis de Información  
**Caso:** 3 - AquaSense CR (Wide-Column)  
**Grupo:** 5  
**Tecnología:** Apache Cassandra 5.0.9  
**Autores:** Jeferson Salazar, Sandy Ruiz, Jimena Díaz, Estafanía Núñez, Keylor Gómez

---

## 1. Introducción

AquaSense CR monitorea redes de agua potable mediante sensores que generan lecturas continuas de caudal, presión, temperatura y calidad. El sistema requiere:

- Absorber grandes volúmenes de escritura (telemetría).
- Consultar rápidamente series de tiempo por sensor y por rango temporal.
- Consultar por zona y periodo.
- Identificar lecturas anómalas.
- Escalar horizontalmente sin degradar el rendimiento.

Apache Cassandra es adecuado porque ofrece escritura distribuida, alta disponibilidad, escalabilidad horizontal y un modelo wide-column optimizado para series de tiempo.

---

## 2. Estrategia de Modelado

Cassandra es **query-driven**: las tablas se diseñan a partir de las consultas, no a partir de un modelo normalizado. Cada consulta frecuente tiene su propia tabla desnormalizada.

### 2.1 Decisiones clave

| Decisión | Justificación |
|---|---|
| Partición por `(sensor_id, bucket)` | Evita particiones ilimitadas por sensor. El bucket (día) mantiene un tamaño predecible. |
| Partición por `(zona, bucket)` | Permite consultar por zona y rango temporal sin escanear toda la tabla. |
| Clustering por `fecha_hora DESC` | Las últimas lecturas se devuelven primero, sin ordenamiento adicional. |
| TimeWindowCompactionStrategy (TWCS) | Óptima para series de tiempo: agrupa SSTables por ventana temporal. |
| Desnormalización | Aceptada en Cassandra a cambio de lecturas rápidas sin joins. |

### 2.2 Bucket temporal

El `bucket` es una fecha (`date`) que agrupa las lecturas por día. Sin él, un sensor con años de datos generaría una partición gigante. Con `bucket`, cada partición corresponde a un sensor en un día específico.

---

## 3. Tablas del Modelo

### 3.1 `sensores` - Catálogo de sensores

| Columna | Tipo | Rol |
|---|---|---|
| sensor_id | uuid | Partition Key |
| zona | text | atributo |
| tipo | text | atributo |
| activo | boolean | atributo |
| latitud | double | atributo |
| longitud | double | atributo |

**Uso:** consultar metadatos de un sensor por ID.

### 3.2 `sensores_por_zona` - Sensores por zona

| Columna | Tipo | Rol |
|---|---|---|
| zona | text | Partition Key |
| sensor_id | uuid | Clustering Key |
| tipo | text | atributo |
| activo | boolean | atributo |

**Uso:** listar todos los sensores de una zona.

### 3.3 `lecturas_por_sensor` - Lecturas por sensor

| Columna | Tipo | Rol |
|---|---|---|
| sensor_id | uuid | Partition Key |
| bucket | date | Partition Key |
| fecha_hora | timestamp | Clustering Key (DESC) |
| zona | text | atributo |
| caudal | double | atributo |
| presion | double | atributo |
| temperatura | double | atributo |
| calidad | text | atributo |
| anomalia | boolean | atributo |

**Uso:** últimas lecturas de un sensor, rango temporal de un sensor.

### 3.4 `lecturas_por_zona` - Lecturas por zona

| Columna | Tipo | Rol |
|---|---|---|
| zona | text | Partition Key |
| bucket | date | Partition Key |
| fecha_hora | timestamp | Clustering Key (DESC) |
| sensor_id | uuid | Clustering Key (ASC) |
| caudal, presion, temperatura | double | atributos |
| calidad | text | atributo |
| anomalia | boolean | atributo |

**Uso:** lecturas por zona y rango temporal.

### 3.5 `anomalias_por_sensor` y `anomalias_por_zona`

Réplicas especializadas para consultar solo anomalías, con un campo extra `motivo` que describe la causa.

### 3.6 `resumen_diario_zona` - Resumen diario por zona

| Columna | Tipo | Rol |
|---|---|---|
| zona | text | Partition Key |
| dia | date | Clustering Key (DESC) |
| total_sensores | int | atributo |
| total_lecturas | int | atributo |
| promedio_caudal, promedio_presion, promedio_temperatura | double | atributos |
| total_anomalias | int | atributo |

**Uso:** reportes operativos agregados por zona y día.

### 3.7 `ultima_lectura_sensor` - Última lectura por sensor

Tabla optimizada para obtener la lectura más reciente de un sensor en O(1).

---

## 4. Consultas Soportadas

```cql
-- 1. Últimas lecturas de un sensor
SELECT * FROM lecturas_por_sensor
WHERE sensor_id = ? AND bucket = ?
ORDER BY fecha_hora DESC LIMIT 10;

-- 2. Rango temporal de un sensor
SELECT * FROM lecturas_por_sensor
WHERE sensor_id = ? AND bucket = ?
  AND fecha_hora >= ? AND fecha_hora <= ?;

-- 3. Lecturas por zona y periodo
SELECT * FROM lecturas_por_zona
WHERE zona = ? AND bucket = ?
  AND fecha_hora >= ? AND fecha_hora <= ?;

-- 4. Anomalías por zona
SELECT * FROM anomalias_por_zona
WHERE zona = ? AND bucket = ?;

-- 5. Resumen diario por zona
SELECT * FROM resumen_diario_zona
WHERE zona = ? AND dia >= ?;

-- 6. Última lectura de un sensor
SELECT * FROM ultima_lectura_sensor WHERE sensor_id = ?;
