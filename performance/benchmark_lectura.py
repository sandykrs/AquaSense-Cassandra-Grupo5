"""Benchmark de lectura: latencia de las consultas principales de AquaSense.

Uso (con Cassandra encendida y los datos cargados):
    python performance/benchmark_lectura.py
Genera performance/resultados/benchmark_lectura.csv
"""
import csv
import statistics
import time
from collections import defaultdict
from pathlib import Path

from cassandra.cluster import Cluster

REPETICIONES = 30
CALENTAMIENTO = 5
MUESTRAS = REPETICIONES + CALENTAMIENTO
SALIDA = Path(__file__).parent / "resultados" / "benchmark_lectura.csv"

from cassandra.io.asyncioreactor import AsyncioConnection
cluster = Cluster(["127.0.0.1"], port=9042, connection_class=AsyncioConnection)
session = cluster.connect("aquasense")


def dia(fecha):
    return fecha.days_from_epoch


# ---------- Datos de muestra (esta parte no se mide) ----------
buckets_por_sensor = defaultdict(list)
for f in session.execute("SELECT DISTINCT sensor_id, bucket FROM lecturas_por_sensor", timeout=300):
    buckets_por_sensor[f.sensor_id].append(f.bucket)
if not buckets_por_sensor:
    raise SystemExit("lecturas_por_sensor esta vacia: carga los datos primero.")
for lista in buckets_por_sensor.values():
    lista.sort(key=dia)
sensores = list(buckets_por_sensor)[:MUESTRAS]

zonas = sorted(f.zona for f in session.execute("SELECT DISTINCT zona FROM sensores_por_zona"))
dias = sorted({b for lista in buckets_por_sensor.values() for b in lista}, key=dia)
zona_dia = [(z, d) for d in dias[-10:] for z in zonas][:MUESTRAS]

anom_sensor = [(f.sensor_id, f.bucket) for f in session.execute(
    "SELECT DISTINCT sensor_id, bucket FROM anomalias_por_sensor LIMIT 500", timeout=300)][:MUESTRAS]
anom_zona = [(f.zona, f.bucket) for f in session.execute(
    "SELECT DISTINCT zona, bucket FROM anomalias_por_zona LIMIT 500", timeout=300)][:MUESTRAS]


def medio(sensor):
    lista = buckets_por_sensor[sensor]
    return lista[len(lista) // 2]


CONSULTAS = [
    ("Ultima lectura de un sensor (tabla derivada)",
     "SELECT * FROM ultima_lectura_sensor WHERE sensor_id = ?",
     lambda i: (sensores[i],)),
    ("Ultimas 10 lecturas de un sensor (dia reciente)",
     "SELECT * FROM lecturas_por_sensor WHERE sensor_id = ? AND bucket = ? LIMIT 10",
     lambda i: (sensores[i], buckets_por_sensor[sensores[i]][-1])),
    ("Sensor y rango de 1 dia",
     "SELECT * FROM lecturas_por_sensor WHERE sensor_id = ? AND bucket = ?",
     lambda i: (sensores[i], medio(sensores[i]))),
    ("Sensor y rango de 7 dias",
     "SELECT * FROM lecturas_por_sensor WHERE sensor_id = ? AND bucket IN ?",
     lambda i: (sensores[i], buckets_por_sensor[sensores[i]][-7:])),
    ("Zona y 1 dia",
     "SELECT * FROM lecturas_por_zona WHERE zona = ? AND bucket = ?",
     lambda i: zona_dia[i % len(zona_dia)]),
    ("Anomalias de un sensor (dia con anomalias)",
     "SELECT * FROM anomalias_por_sensor WHERE sensor_id = ? AND bucket = ?",
     lambda i: anom_sensor[i % len(anom_sensor)]),
    ("Anomalias de una zona (dia con anomalias)",
     "SELECT * FROM anomalias_por_zona WHERE zona = ? AND bucket = ?",
     lambda i: anom_zona[i % len(anom_zona)]),
    ("Resumen diario de una zona (ultimos 7 dias)",
     "SELECT * FROM resumen_diario_zona WHERE zona = ? LIMIT 7",
     lambda i: (zonas[i % len(zonas)],)),
]

# ---------- Medicion ----------
resultados = []
print(f"Latencias en ms ({REPETICIONES} repeticiones, {CALENTAMIENTO} de calentamiento)")
print(f"{'Consulta':<50}{'p50':>8}{'p95':>8}{'media':>8}{'min':>8}{'max':>8}{'filas':>8}")
for nombre, cql, params in CONSULTAS:
    stmt = session.prepare(cql)
    for i in range(CALENTAMIENTO):
        session.execute(stmt, params(i))
    tiempos, filas = [], []
    for i in range(CALENTAMIENTO, MUESTRAS):
        t0 = time.perf_counter()
        n = len(list(session.execute(stmt, params(i))))
        tiempos.append((time.perf_counter() - t0) * 1000)
        filas.append(n)
    p50 = statistics.median(tiempos)
    p95 = statistics.quantiles(tiempos, n=20)[18]
    media = statistics.mean(tiempos)
    filas_prom = statistics.mean(filas)
    resultados.append([nombre, REPETICIONES, round(p50, 2), round(p95, 2),
                       round(media, 2), round(min(tiempos), 2), round(max(tiempos), 2),
                       round(filas_prom, 1)])
    aviso = "  (sin filas)" if sum(filas) == 0 else ""
    print(f"{nombre:<50}{p50:>8.2f}{p95:>8.2f}{media:>8.2f}{min(tiempos):>8.2f}"
          f"{max(tiempos):>8.2f}{filas_prom:>8.1f}{aviso}")

SALIDA.parent.mkdir(exist_ok=True)
with open(SALIDA, "w", newline="", encoding="utf-8") as archivo:
    escritor = csv.writer(archivo)
    escritor.writerow(["consulta", "repeticiones", "p50_ms", "p95_ms", "media_ms",
                       "min_ms", "max_ms", "filas_promedio"])
    escritor.writerows(resultados)
print(f"\nResultados guardados en {SALIDA}")
cluster.shutdown()
