```markdown
# Arquitectura de la Solución - AquaSense CR

**Grupo:** 5  
**Tecnología:** Apache Cassandra 5.0.9  
**Autores:** Jeferson Salazar, Sandy Ruiz, Jimena Díaz, Estafanía Núñez, Keylor Gómez

---

## 1. Visión General
+-------------+ +----------------+ +------------------+
| Sensores | --> | API Ingesta | --> | Cassandra |
| (1000+) | | (Python/Node) | | (3 nodos RF=3) |
+-------------+ +----------------+ +------------------+
|
v
+------------------+
| API Consultas |
| + Dashboards |
+------------------+

text

- **Sensores:** 1000 sensores distribuidos en 20 zonas.
- **API de ingesta:** recibe lecturas y las escribe en Cassandra con batch por sensor/bucket.
- **Cassandra:** clúster con replicación para alta disponibilidad.
- **API de consultas:** sirve dashboards y reportes operativos.

---

## 2. Flujo de Datos

1. **Ingesta:** cada sensor envía lecturas cada N segundos.
2. **Escritura:** la API escribe en `lecturas_por_sensor`, `lecturas_por_zona` y `ultima_lectura_sensor`.
3. **Detección de anomalías:** se evalúa en la ingesta o en un job periódico; si aplica, escribe en `anomalias_por_sensor` y `anomalias_por_zona`.
4. **Agregados:** un job diario calcula `resumen_diario_zona`.
5. **Consulta:** los dashboards consultan por sensor, zona o rango temporal.

---

## 3. Modelo de Despliegue

| Componente | Tecnología | Notas |
|---|---|---|
| Base de datos | Apache Cassandra 5.0.9 | 3 nodos en producción |
| Replicación | NetworkTopologyStrategy RF=3 | 1 datacenter |
| Compaction | TWCS (1 día) | Óptimo para series de tiempo |
| Cliente | cqlsh / driver Python | cqlsh para pruebas |

---

## 4. Escalabilidad

- **Horizontal:** agregar nodos al clúster distribuye datos automáticamente (consistent hashing).
- **Escritura:** Cassandra está optimizada para escritura append-only.
- **Lectura:** cada tabla está optimizada para una consulta específica.
- **Particionado:** `(sensor_id, bucket)` y `(zona, bucket)` evitan hotspots.

---

## 5. Alta Disponibilidad

- **Replicación RF=3:** cada dato existe en 3 nodos.
- **Sin punto único de falla:** cualquier nodo puede responder.
- **Consistencia ajustable:** `ONE`, `QUORUM`, `LOCAL_QUORUM`.
- **Recuperación:** `nodetool repair` sincroniza réplicas.

---

## 6. Seguridad

- Credenciales por variables de entorno (`.env`).
- No se suben secretos al repositorio.
- Autenticación nativa de Cassandra habilitada en producción.

---

## 7. Reproducibilidad

El entorno se levanta con Docker:

```bash
docker run --name aquasense -p 9042:9042 -d cassandra:latest
docker cp cql/schema.cql aquasense:/schema.cql
docker exec -it aquasense cqlsh
Dentro de cqlsh:

cql
SOURCE '/schema.cql';
text

---



## 5. Referencias

- `docs/modelo-datos.md`
- `docs/arquitectura.md`
- `cql/schema.cql`
