# Modelo de Datos - AquaSense CR

**Proyecto:** XS0131 - Gestión de Bases de Datos y Análisis de Información  
**Caso:** 3 - AquaSense CR (Wide-Column)  
**Grupo:** 5  
**Tecnología:** Apache Cassandra 5.0.9  
**Autores:** Jeferson Salazar, Sandy Ruiz, Jimena Díaz, Estefanía Núñez, Keylor Gómez

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
| Partición por `(zone, bucket)` | Permite consultar por zona y rango temporal sin escanear toda la tabla. |
| Clustering por `ts DESC` | Las últimas lecturas se devuelven primero, sin ordenamiento adicional. |
| TimeWindowCompactionStrategy (TWCS) | Óptima para series de tiempo: agrupa SSTables por ventana temporal. |
| Desnormalización | Aceptada en Cassandra a cambio de lecturas rápidas sin joins. |

### 2.2 Bucket temporal

El `bucket` es una fecha (`date`) que agrupa las lecturas por día. Sin él, un sensor con años de datos generaría una partición gigante. Con `bucket`, cada partición corresponde a un sensor en un día específico.

---

## 3. Tablas del Modelo

### 3.1 `sensors` - Catálogo de sensores

| Columna | Tipo | Rol |
|---|---|---|
| sensor_id | uuid | Partition Key |
| zone | text | atributo |
| tipo | text | atributo |
| activo | boolean | atributo |
| lat | double | atributo |
| lon | double | atributo |

**Uso:** consultar metadatos de un sensor por ID.

### 3.2 `sensors_by_zone` - Sensores por zona

| Columna | Tipo | Rol |
|---|---|---|
| zone | text | Partition Key |
| sensor_id | uuid | Clustering Key |
| tipo | text | atributo |
| activo | boolean | atributo |

**Uso:** listar todos los sensores de una zona.

### 3.3 `sensor_readings` - Lecturas por sensor

| Columna | Tipo | Rol |
|---|---|---|
| sensor_id | uuid | Partition Key |
| bucket | date | Partition Key |
| ts | timestamp | Clustering Key (DESC) |
| zone | text | atributo |
| caudal | double | atributo |
| presion | double | atributo |
| temperatura | double | atributo |
| calidad | text | atributo |
| anomalia | boolean | atributo |

**Uso:** últimas lecturas de un sensor, rango temporal de un sensor.

### 3.4 `readings_by_zone` - Lecturas por zona

| Columna | Tipo | Rol |
|---|---|---|
| zone | text | Partition Key |
| bucket | date | Partition Key |
| ts | timestamp | Clustering Key (DESC) |
| sensor_id | uuid | Clustering Key (ASC) |
| caudal, presion, temperatura | double | atributos |
| calidad | text | atributo |
| anomalia | boolean | atributo |

**Uso:** lecturas por zona y rango temporal.

### 3.5 `anomalies_by_sensor` y `anomalies_by_zone`

Réplicas especializadas para consultar solo anomalías, con un campo extra `motivo` que describe la causa.

### 3.6 `daily_zone_stats` - Resumen diario por zona

| Columna | Tipo | Rol |
|---|---|---|
| zone | text | Partition Key |
| day | date | Clustering Key (DESC) |
| sensor_count | int | atributo |
| lectura_count | int | atributo |
| avg_caudal, avg_presion, avg_temperatura | double | atributos |
| anomaly_count | int | atributo |

**Uso:** reportes operativos agregados por zona y día.

### 3.7 `sensor_latest` - Última lectura por sensor

Tabla optimizada para obtener la lectura más reciente de un sensor en O(1).

---

## 4. Consultas Soportadas

```cql
-- 1. Últimas lecturas de un sensor
SELECT * FROM sensor_readings
WHERE sensor_id = ? AND bucket = ?
ORDER BY ts DESC LIMIT 10;

-- 2. Rango temporal de un sensor
SELECT * FROM sensor_readings
WHERE sensor_id = ? AND bucket = ?
  AND ts >= ? AND ts <= ?;

-- 3. Lecturas por zona y periodo
SELECT * FROM readings_by_zone
WHERE zone = ? AND bucket = ?
  AND ts >= ? AND ts <= ?;

-- 4. Anomalías por zona
SELECT * FROM anomalies_by_zone
WHERE zone = ? AND bucket = ?;

-- 5. Resumen diario por zona
SELECT * FROM daily_zone_stats
WHERE zone = ? AND day >= ?;

-- 6. Última lectura de un sensor
SELECT * FROM sensor_latest WHERE sensor_id = ?;
