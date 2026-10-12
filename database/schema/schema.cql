-- ============================================================================
-- XS0131 - Gestión de Bases de Datos y Análisis de Información
-- Caso 3: AquaSense CR - Modelo Wide-Column
-- Grupo 5 - Integrantes : Jeferson Salazar, Sandy Ruiz, Jimena Díaz, Estafnía Núñez, Keylor Gómez
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

CREATE TABLE IF NOT EXISTS sensores (
  sensor_id uuid PRIMARY KEY,
  zona text,
  tipo text,
  activo boolean,
  latitud double,
  longitud double
);

CREATE TABLE IF NOT EXISTS sensores_por_zona (
  zona text,
  sensor_id uuid,
  tipo text,
  activo boolean,
  PRIMARY KEY (zona, sensor_id)
);

-- ============================================================================
-- 3. TABLAS DE LECTURAS (SERIES DE TIEMPO)
-- ============================================================================

CREATE TABLE IF NOT EXISTS lecturas_por_sensor (
  sensor_id uuid,
  bucket date,
  fecha_hora timestamp,
  zona text,
  caudal double,
  presion double,
  temperatura double,
  calidad text,
  anomalia boolean,
  PRIMARY KEY ((sensor_id, bucket), fecha_hora)
) WITH CLUSTERING ORDER BY (fecha_hora DESC)
  AND compaction = {
    'class': 'TimeWindowCompactionStrategy',
    'compaction_window_unit': 'DAYS',
    'compaction_window_size': 1
  };

CREATE TABLE IF NOT EXISTS lecturas_por_zona (
  zona text,
  bucket date,
  fecha_hora timestamp,
  sensor_id uuid,
  caudal double,
  presion double,
  temperatura double,
  calidad text,
  anomalia boolean,
  PRIMARY KEY ((zona, bucket), fecha_hora, sensor_id)
) WITH CLUSTERING ORDER BY (fecha_hora DESC, sensor_id ASC)
  AND compaction = {
    'class': 'TimeWindowCompactionStrategy',
    'compaction_window_unit': 'DAYS',
    'compaction_window_size': 1
  };

-- ============================================================================
-- 4. TABLAS DE ANOMALÍAS
-- ============================================================================

CREATE TABLE IF NOT EXISTS anomalias_por_sensor (
  sensor_id uuid,
  bucket date,
  fecha_hora timestamp,
  zona text,
  caudal double,
  presion double,
  temperatura double,
  calidad text,
  motivo text,
  PRIMARY KEY ((sensor_id, bucket), fecha_hora)
) WITH CLUSTERING ORDER BY (fecha_hora DESC);

CREATE TABLE IF NOT EXISTS anomalias_por_zona (
  zona text,
  bucket date,
  fecha_hora timestamp,
  sensor_id uuid,
  motivo text,
  caudal double,
  presion double,
  temperatura double,
  calidad text,
  PRIMARY KEY ((zona, bucket), fecha_hora, sensor_id)
) WITH CLUSTERING ORDER BY (fecha_hora DESC, sensor_id ASC);

-- ============================================================================
-- 5. TABLAS RESUMEN / AGREGADOS
-- ============================================================================

CREATE TABLE IF NOT EXISTS resumen_diario_zona (
  zona text,
  dia date,
  total_sensores int,
  total_lecturas int,
  promedio_caudal double,
  promedio_presion double,
  promedio_temperatura double,
  total_anomalias int,
  PRIMARY KEY ((zona), dia)
) WITH CLUSTERING ORDER BY (dia DESC);

CREATE TABLE IF NOT EXISTS ultima_lectura_sensor (
  sensor_id uuid PRIMARY KEY,
  zona text,
  fecha_hora timestamp,
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