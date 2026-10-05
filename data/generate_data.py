import os
import csv
import time
import argparse
from collections import defaultdict
from datetime import datetime, date
from uuid import UUID

from cassandra.cluster import Cluster
from cassandra.query import BatchStatement, BatchType
from cassandra.concurrent import execute_concurrent

from generate_data import generar_sensores, generar_mediciones, NUM_MEDICIONES

# ============================================================
# CONFIGURACIÓN (se puede cambiar con variables de entorno
# o, para los 3 últimos, con --batch / --concurrency / --buffer)
# ============================================================
HOSTS = os.getenv("CASSANDRA_HOSTS", "127.0.0.1").split(",")
PORT = int(os.getenv("CASSANDRA_PORT", "9042"))
KEYSPACE = os.getenv("CASSANDRA_KEYSPACE", "aquasense")

TAMANO_BATCH = 50        # filas máximas por batch (misma partición)
TAMANO_BUFFER = 20_000   # filas que se acumulan antes de agrupar y enviar
CONCURRENCIA = 32        # operaciones en vuelo al mismo tiempo

# El generador usa 0/1/2; el schema usa texto
CALIDAD = {0: "buena", 1: "regular", 2: "mala"}


# ============================================================
# FUNCIONES
# ============================================================

def conectar():
    cluster = Cluster(HOSTS, port=PORT)
    session = cluster.connect(KEYSPACE)
    return cluster, session


def enviar_batches(session, stmt, filas, tamano_batch=None):
    """
    filas: lista de (clave_particion, parametros).
    Agrupa por partición y envía batches UNLOGGED en paralelo.
    Retorna la cantidad de batches enviados.
    """
    tamano_batch = tamano_batch or TAMANO_BATCH

    grupos = defaultdict(list)
    for clave, params in filas:
        grupos[clave].append(params)

    batches = []
    for lista in grupos.values():
        for i in range(0, len(lista), tamano_batch):
            batch = BatchStatement(batch_type=BatchType.UNLOGGED)
            for params in lista[i:i + tamano_batch]:
                batch.add(stmt, params)
            batches.append((batch, None))

    execute_concurrent(session, batches, concurrency=CONCURRENCIA,
                       raise_on_first_error=True)
    return len(batches)


def enviar_individuales(session, stmt, lista_params):
    """Para tablas donde cada fila es su propia partición (sin batch)."""
    execute_concurrent(session, [(stmt, p) for p in lista_params],
                       concurrency=CONCURRENCIA, raise_on_first_error=True)


def cargar_sensores(session, sensores):
    stmt_sensor = session.prepare("""
        INSERT INTO sensores (sensor_id, zona, tipo, activo, latitud, longitud)
        VALUES (?, ?, ?, ?, ?, ?)
    """)
    stmt_por_zona = session.prepare("""
        INSERT INTO sensores_por_zona (zona, sensor_id, tipo, activo)
        VALUES (?, ?, ?, ?)
    """)

    individuales = []
    por_zona = []
    for s in sensores:
        sid = UUID(s["sensor_id"])
        activo = s["status"] == "activo"
        individuales.append((sid, s["zone_id"], s["sensor_type"], activo,
                             s["latitude"], s["longitude"]))
        por_zona.append((s["zone_id"], (s["zone_id"], sid, s["sensor_type"], activo)))

    enviar_individuales(session, stmt_sensor, individuales)
    enviar_batches(session, stmt_por_zona, por_zona)
    print(f"Sensores cargados: {len(sensores)}")


def registrar_resultado(filas, anomalias, batches, duracion):
    """Agrega una línea a data/resultados_carga.csv para el benchmark."""
    carpeta = os.path.dirname(os.path.abspath(__file__))
    ruta = os.path.join(carpeta, "resultados_carga.csv")
    encabezado = ["fecha", "filas", "anomalias", "batches", "tamano_batch",
                  "tamano_buffer", "concurrencia", "segundos", "filas_por_seg"]

    # Si el CSV es de la versión anterior (sin tamano_buffer), se guarda aparte
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            primera = f.readline()
        if "tamano_buffer" not in primera:
            os.replace(ruta, os.path.join(carpeta, "resultados_carga_dia6.csv"))

    nuevo = not os.path.exists(ruta)
    with open(ruta, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(encabezado)
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), filas,
                    anomalias, batches, TAMANO_BATCH, TAMANO_BUFFER,
                    CONCURRENCIA, round(duracion, 1), round(filas / duracion)])


def cargar_mediciones(session, sensores, limite):
    stmt_lec_sensor = session.prepare("""
        INSERT INTO lecturas_por_sensor
        (sensor_id, bucket, fecha_hora, zona, caudal, presion,
         temperatura, calidad, anomalia)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)
    stmt_lec_zona = session.prepare("""
        INSERT INTO lecturas_por_zona
        (zona, bucket, fecha_hora, sensor_id, caudal, presion,
         temperatura, calidad, anomalia)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)
    stmt_anom_sensor = session.prepare("""
        INSERT INTO anomalias_por_sensor
        (sensor_id, bucket, fecha_hora, zona, caudal, presion,
         temperatura, calidad, motivo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)
    stmt_anom_zona = session.prepare("""
        INSERT INTO anomalias_por_zona
        (zona, bucket, fecha_hora, sensor_id, motivo, caudal, presion,
         temperatura, calidad)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)
    stmt_resumen = session.prepare("""
        INSERT INTO resumen_diario_zona
        (zona, dia, total_sensores, total_lecturas, promedio_caudal,
         promedio_presion, promedio_temperatura, total_anomalias)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """)
    stmt_ultima = session.prepare("""
        INSERT INTO ultima_lectura_sensor
        (sensor_id, zona, fecha_hora, caudal, presion, temperatura,
         calidad, anomalia)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """)

    lec_sensor, lec_zona, anom_sensor, anom_zona = [], [], [], []
    resumen = {}   # (zona, dia) -> [n, sum_caudal, sum_presion, sum_temp, anomalias, sensores]
    ultima = {}    # sensor_id -> params de la última lectura
    total = 0
    total_anomalias = 0
    total_batches = 0
    inicio = time.time()

    def vaciar():
        nonlocal lec_sensor, lec_zona, anom_sensor, anom_zona, total_batches
        total_batches +=