
### 3.5 Insertar y consultar lectura

```sql
INSERT INTO sensor_readings (sensor_id, bucket, ts, zone, caudal, presion, temperatura, calidad, anomalia)
VALUES (11111111-1111-1111-1111-111111111111, '2026-10-01', toTimestamp(now()), 'Zona1', 12.5, 45.2, 22.1, 'buena', false);

SELECT * FROM sensor_readings
WHERE sensor_id = 11111111-1111-1111-1111-111111111111
  AND bucket = '2026-10-01'
LIMIT 5;
```

### 3.6 Validar sensors_by_zone

```sql
INSERT INTO sensors_by_zone (zone, sensor_id, tipo, activo)
VALUES ('Zona1', 11111111-1111-1111-1111-111111111111, 'caudal', true);

SELECT * FROM sensors_by_zone WHERE zone = 'Zona1';
```

### 3.7 Validar readings_by_zone

```sql
INSERT INTO readings_by_zone (zone, bucket, ts, sensor_id, caudal, presion, temperatura, calidad, anomalia)
VALUES ('Zona1', '2026-10-01', toTimestamp(now()), 11111111-1111-1111-1111-111111111111, 12.5, 45.2, 22.1, 'buena', false);

SELECT * FROM readings_by_zone WHERE zone = 'Zona1' AND bucket = '2026-10-01';
```

### 3.8 Validar sensor_latest

```sql
INSERT INTO sensor_latest (sensor_id, zone, ts, caudal, presion, temperatura, calidad, anomalia)
VALUES (11111111-1111-1111-1111-111111111111, 'Zona1', toTimestamp(now()), 12.5, 45.2, 22.1, 'buena', false);

SELECT * FROM sensor_latest WHERE sensor_id = 11111111-1111-1111-1111-111111111111;
```

### 3.9 Validar daily_zone_stats

```sql
INSERT INTO daily_zone_stats (zone, day, sensor_count, lectura_count, avg_caudal, avg_presion, avg_temperatura, anomaly_count)
VALUES ('Zona1', '2026-10-01', 1, 1, 12.5, 45.2, 22.1, 0);

SELECT * FROM daily_zone_stats WHERE zone = 'Zona1';
```

Resultado: 1 fila.

### 3.10 Limpieza de datos de prueba

```sql
TRUNCATE sensors;
TRUNCATE sensors_by_zone;
TRUNCATE sensor_readings;
TRUNCATE readings_by_zone;
TRUNCATE anomalies_by_sensor;
TRUNCATE anomalies_by_zone;
TRUNCATE daily_zone_stats;
TRUNCATE sensor_latest;
```

Resultado: todas las tablas quedaron vacías, listas para recibir datos reales.

---

## 4. Resultados

| Tabla | Inserción | Consulta | Estado |
|---|---|---|---|
| sensors | ✅ | ✅ | OK |
| sensors_by_zone | ✅ | ✅ | OK |
| sensor_readings | ✅ | ✅ | OK |
| readings_by_zone | ✅ | ✅ | OK |
| anomalies_by_sensor | ✅ (estructura) | ✅ (estructura) | OK |
| anomalies_by_zone | ✅ (estructura) | ✅ (estructura) | OK |
| daily_zone_stats | ✅ | ✅ | OK |
| sensor_latest | ✅ | ✅ | OK |

---

## 5. Conclusiones

- Las 8 tablas del keyspace `aquasense` están correctamente creadas y operativas.
- Todas las consultas se resuelven filtrando por partition key completa, sin `ALLOW FILTERING`.
- Los tipos de datos coinciden con el diseño documentado en `modelo-datos.md`.
- El schema queda validado para recibir los datos sintéticos del Integrante B.