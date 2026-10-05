import time
from collections import Counter

from cassandra.cluster import Cluster
from cassandra.query import SimpleStatement

cluster = Cluster(["127.0.0.1"], port=9042)
session = cluster.connect("aquasense")

stmt = SimpleStatement(
    "SELECT sensor_id, bucket, anomalia FROM lecturas_por_sensor",
    fetch_size=5000,
)

inicio = time.time()
total = 0
anomalias = 0
por_particion = Counter()

for fila in session.execute(stmt, timeout=600):
    total += 1
    if fila.anomalia:
        anomalias += 1
    por_particion[(fila.sensor_id, fila.bucket)] += 1

duracion = time.time() - inicio
tamanos = list(por_particion.values())

print("Tabla: lecturas_por_sensor")
print(f"Filas totales:            {total:,}")
print(f"Filas anomalas:           {anomalias:,} ({100 * anomalias / total:.2f} %)")
print(f"Particiones distintas:    {len(por_particion):,}")
print(f"Filas por particion:      min={min(tamanos)}  media={total / len(tamanos):.1f}  max={max(tamanos)}")
print(f"Tiempo de verificacion:   {duracion:.1f} s")

cluster.shutdown()