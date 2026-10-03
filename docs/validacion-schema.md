
# Validación del Schema - AquaSense CR

**Proyecto:** XS0131 - Gestión de Bases de Datos y Análisis de Información
**Caso:** 3 - AquaSense CR (Wide-Column)
**Grupo:** 5
**Tecnología:** Apache Cassandra 5.0.9
**Autores:** Jeferson Salazar, Sandy Ruiz, Jimena Díaz, Estafanía Núñez, Keylor Gómez
**Fecha de validación:** 2 de octubre de 2026

---

## 1. Objetivo

Validar que las 8 tablas del keyspace `aquasense` (con nomenclatura en español) funcionan correctamente con inserciones y lecturas, sin errores de sintaxis ni de tipos, y sin necesidad de `ALLOW FILTERING`.

---

## 2. Entorno de validación

| Componente | Valor |
|---|---|
| Contenedor Docker | `aquasense` |
| Imagen | `cassandra:latest` |
| Versión de Cassandra | 5.0.9 |
| Puerto | 9042 |
| Keyspace | `aquasense` |
| Cliente | cqlsh |

---

## 3. Comandos de validación

### 3.1 Verificar el contenedor corriendo

```bash
docker ps
```

Resultado: contenedor `aquasense` con estado `Up`.

### 3.2 Entrar a cqlsh

```bash
docker exec -it aquasense cqlsh
```

Resultado: prompt `cqlsh>` con conexión a Test Cluster.

### 3.3 Seleccionar el keyspace

```sql
USE aquasense;
```

### 3.4 Insertar y consultar sensor

```sql
INSERT INTO sensores (sensor_id, zona, tipo, activo, latitud, longitud)
VALUES (11111111-1111-1111-1111-111111111111, 'Z01', 'caudal', true, 9.93, -84.08);

SELECT * FROM sensores WHERE sensor_id = 11111111-1111-1111-1111-111111111111;
```

Resultado: 1 fila.

### 3.5 Insertar y consultar lectura

```sql
INSERT INTO lecturas_por_sensor (sensor_id, bucket, fecha_hora, zona, caudal, presion, temperatura, calidad, anomalia)
VALUES (11111111-1111-1111-1111-111111111111, '2026-10-02', toTimestamp(now()), 'Z01', 12.5, 45.2, 22.1, 'buena', false);

SELECT * FROM lecturas_por_sensor
WHERE sensor_id = 11111111-1111-1111-1111-111111111111
  AND bucket = '2026-10-02'
LIMIT 5;
```

Resultado: 1 fila.

### 3.6 Validar sensores_por_zona

```sql
INSERT INTO sensores_por_zona (zona, sensor_id, tipo, activo)
VALUES ('Z01', 11111111-1111-1111-1111-111111111111, 'caudal', true);

SELECT * FROM sensores_por_zona WHERE zona = 'Z01';
```

Resultado: 1 fila.

### 3.7 Validar lecturas_por_zona

```sql
INSERT INTO lecturas_por_zona (zona, bucket, fecha_hora, sensor_id, caudal, presion, temperatura, calidad, anomalia)
VALUES ('Z01', '2026-10-02', toTimestamp(now()), 11111111-1111-1111-1111-111111111111, 12.5, 45.2, 22.1, 'buena', false);

SELECT * FROM lecturas_por_zona WHERE zona = 'Z01' AND bucket = '2026-10-02';
```

Resultado: 1 fila.

### 3.8 Validar anomalias_por_sensor

```sql
INSERT INTO anomalias_por_sensor (sensor_id, bucket, fecha_hora, zona, caudal, presion, temperatura, calidad, motivo)
VALUES (11111111-1111-1111-1111-111111111111, '2026-10-02', toTimestamp(now()), 'Z01', 150.0, 4.0, 25.0, 'regular', 'flow_high');

SELECT * FROM anomalias_por_sensor
WHERE sensor_id = 11111111-1111-1111-1111-111111111111
  AND bucket = '2026-10-02';
```

Resultado: 1 fila.

### 3.9 Validar anomalias_por_zona

```sql
INSERT INTO anomalias_por_zona (zona, bucket, fecha_hora, sensor_id, motivo, caudal, presion, temperatura, calidad)
VALUES ('Z01', '2026-10-02', toTimestamp(now()), 11111111-1111-1111-1111-111111111111, 'flow_high', 150.0, 4.0, 25.0, 'regular');

SELECT * FROM anomalias_por_zona WHERE zona = 'Z01' AND bucket = '2026-10-02';
```

Resultado: 1 fila.

### 3.10 Validar resumen_diario_zona

```sql
INSERT INTO resumen_diario_zona (zona, dia, total_sensores, total_lecturas, promedio_caudal, promedio_presion, promedio_temperatura, total_anomalias)
VALUES ('Z01', '2026-10-02', 50, 500, 12.5, 45.2, 22.1, 3);

SELECT * FROM resumen_diario_zona WHERE zona = 'Z01';
```

Resultado: 1 fila.

### 3.11 Validar ultima_lectura_sensor

```sql
INSERT INTO ultima_lectura_sensor (sensor_id, zona, fecha_hora, caudal, presion, temperatura, calidad, anomalia)
VALUES (11111111-1111-1111-1111-111111111111, 'Z01', toTimestamp(now()), 12.5, 45.2, 22.1, 'buena', false);

SELECT * FROM ultima_lectura_sensor WHERE sensor_id = 11111111-1111-1111-1111-111111111111;
```

Resultado: 1 fila.

### 3.12 Limpieza de datos de prueba

```sql
TRUNCATE sensores;
TRUNCATE sensores_por_zona;
TRUNCATE lecturas_por_sensor;
TRUNCATE lecturas_por_zona;
TRUNCATE anomalias_por_sensor;
TRUNCATE anomalias_por_zona;
TRUNCATE resumen_diario_zona;
TRUNCATE ultima_lectura_sensor;
```

Resultado: todas las tablas quedaron vacías, listas para recibir datos reales.

---

## 4. Resultados

| Tabla | Inserción | Consulta | Estado |
|---|---|---|---|
| sensores | ✅ | ✅ | OK |
| sensores_por_zona | ✅ | ✅ | OK |
| lecturas_por_sensor | ✅ | ✅ | OK |
| lecturas_por_zona | ✅ | ✅ | OK |
| anomalias_por_sensor | ✅ | ✅ | OK |
| anomalias_por_zona | ✅ | ✅ | OK |
| resumen_diario_zona | ✅ | ✅ | OK |
| ultima_lectura_sensor | ✅ | ✅ | OK |

## 5. Conclusiones
Las 8 tablas del keyspace aquasense están correctamente creadas con nomenclatura en español y operativas.

Todas las consultas se resuelven filtrando por partition key completa, sin ALLOW FILTERING.

Los tipos de datos coinciden con el diseño documentado en modelo-datos.md.
