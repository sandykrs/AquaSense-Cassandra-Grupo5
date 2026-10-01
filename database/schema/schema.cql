-- ============================================================================
-- XS0131 - Gestión de Bases de Datos y Análisis de Información
-- Caso 3: AquaSense CR - Modelo Wide-Column
-- Grupo 5 - Integrante A: Arquitecto de Datos
-- Archivo: cql/schema.cql
-- ============================================================================

-- ============================================================================
-- 0. LIMPIEZA DEL ENTORNO (solo para desarrollo local)
-- ============================================================================
DROP KEYSPACE IF EXISTS aquasense;

-- ============================================================================
-- 1. CREACIÓN DEL KEYSPACE
-- ============================================================================
CREATE KEYSPACE IF NOT EXISTS aquasense
WITH replication = {
  'class': 'SimpleStrategy',
  'replication_factor': 1
};

USE aquasense;

-- ============================================================================
-- 2. TABLAS MAESTRAS / CATÁLOGOS
-- ============================================================================

CREATE TABLE IF NOT EXISTS sensors (
  sensor_id uuid PRIMARY KEY,
  zone text,
  tipo text,
  activo boolean,
  lat double,
  lon double
);

CREATE TABLE IF NOT EXISTS sensors_by_zone (
  zone text,
  sensor_id uuid,
  tipo text,
  activo boolean,
  PRIMARY KEY (zone, sensor_id)
);

-- ============================================================================
-- 3. TABLAS DE LECTURAS (SERIES DE TIEMPO)
-- ============================================================================

CREATE TABLE IF NOT EXISTS sensor_readings (
  sensor_id uuid,
  bucket date,
  ts timestamp,
  zone text,
  caudal double,
  presion double,
  temperatura double,
  calidad text,
  anomalia boolean,
  PRIMARY KEY ((sensor_id, bucket), ts)
) WITH CLUSTERING ORDER BY (ts DESC)
  AND compaction = {
    'class': 'TimeWindowCompactionStrategy',
    'compaction_window_unit': 'DAYS',
    'compaction_window_size': 1
  };

CREATE TABLE IF NOT EXISTS readings_by_zone (
  zone text,
  bucket date,
  ts timestamp,
  sensor_id uuid,
  caudal double,
  presion double,
  temperatura double,
  calidad text,
  anomalia boolean,
  PRIMARY KEY ((zone, bucket), ts, sensor_id)
) WITH CLUSTERING ORDER BY (ts DESC, sensor_id ASC)
  AND compaction = {
    'class': 'TimeWindowCompactionStrategy',
    'compaction_window_unit': 'DAYS',
    'compaction_window_size': 1
  };

-- ============================================================================
-- 4. TABLAS DE ANOMALÍAS
-- ============================================================================

CREATE TABLE IF NOT EXISTS anomalies_by_sensor (
  sensor_id uuid,
  bucket date,
  ts timestamp,
  zone text,
  caudal double,
  presion double,
  temperatura double,
  calidad text,
  motivo text,
  PRIMARY KEY ((sensor_id, bucket), ts)
) WITH CLUSTERING ORDER BY (ts DESC);

CREATE TABLE IF NOT EXISTS anomalies_by_zone (
  zone text,
  bucket date,
  ts timestamp,
  sensor_id uuid,
  motivo text,
  caudal double,
  presion double,
  temperatura double,
  calidad text,
  PRIMARY KEY ((zone, bucket), ts, sensor_id)
) WITH CLUSTERING ORDER BY (ts DESC, sensor_id ASC);

-- ============================================================================
-- 5. TABLAS RESUMEN / AGREGADOS
-- ============================================================================

CREATE TABLE IF NOT EXISTS daily_zone_stats (
  zone text,
  day date,
  sensor_count int,
  lectura_count int,
  avg_caudal double,
  avg_presion double,
  avg_temperatura double,
  anomaly_count int,
  PRIMARY KEY ((zone), day)
) WITH CLUSTERING ORDER BY (day DESC);

CREATE TABLE IF NOT EXISTS sensor_latest (
  sensor_id uuid PRIMARY KEY,
  zone text,
  ts timestamp,
  caudal double,
  presion double,
  temperatura double,
  calidad text,
  anomalia boolean
);

-- ============================================================================
-- 6. CONSULTAS DE VERIFICACIÓN
-- ============================================================================

SELECT table_name
FROM system_schema.tables
WHERE keyspace_name = 'aquasense';