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
# CONFIGURACIÓN (se puede cambiar con variables de entorno)
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


def enviar_batches(session, stmt, filas, tamano_batch=TAMANO_BATCH):
    """
    filas: lista de (clave_particion, parametros).
    Agrupa por partición y envía batches UNLOGGED en paralelo.
    Retorna la cantidad de batches enviados.
    """
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
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "resultados_carga.csv")
    nuevo = not os.path.exists(ruta)
    with open(ruta, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha", "filas", "anomalias", "batches",
                        "tamano_batch", "concurrencia", "segundos", "filas_por_seg"])
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), filas,
                    anomalias, batches, TAMANO_BATCH, CONCURRENCIA,
                    round(duracion, 1), round(filas / duracion)])


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
        total_batches += enviar_batches(session, stmt_lec_sensor, lec_sensor)
        total_batches += enviar_batches(session, stmt_lec_zona, lec_zona)
        total_batches += enviar_batches(session, stmt_anom_sensor, anom_sensor)
        total_batches += enviar_batches(session, stmt_anom_zona, anom_zona)
        lec_sensor, lec_zona, anom_sensor, anom_zona = [], [], [], []

    for m in generar_mediciones(sensores):
        if total >= limite:
            break

        sid = UUID(m["sensor_id"])
        zona = m["zone_id"]
        bucket = date.fromisoformat(m["day"])
        ts = datetime.strptime(m["event_ts"], "%Y-%m-%d %H:%M:%S")
        calidad = CALIDAD[m["quality"]]
        caudal, presion, temp = m["flow"], m["pressure"], m["temperature"]
        anomalia = m["is_anomaly"]

        lec_sensor.append(((m["sensor_id"], m["day"]), (
            sid, bucket, ts, zona, caudal, presion, temp, calidad, anomalia)))
        lec_zona.append(((zona, m["day"]), (
            zona, bucket, ts, sid, caudal, presion, temp, calidad, anomalia)))

        if anomalia:
            total_anomalias += 1
            anom_sensor.append(((m["sensor_id"], m["day"]), (
                sid, bucket, ts, zona, caudal, presion, temp, calidad,
                m["anomaly_type"])))
            anom_zona.append(((zona, m["day"]), (
                zona, bucket, ts, sid, m["anomaly_type"],
                caudal, presion, temp, calidad)))

        # Acumuladores para resumen_diario_zona
        r = resumen.setdefault((zona, bucket), [0, 0.0, 0.0, 0.0, 0, set()])
        r[0] += 1
        r[1] += caudal
        r[2] += presion
        r[3] += temp
        r[4] += 1 if anomalia else 0
        r[5].add(sid)

        # Última lectura por sensor (el generador va en orden de tiempo)
        ultima[sid] = (sid, zona, ts, caudal, presion, temp, calidad, anomalia)

        total += 1
        if len(lec_sensor) >= TAMANO_BUFFER:
            vaciar()
            seg = time.time() - inicio
            print(f"  {total:,} filas | {total / seg:,.0f} filas/s")

    if lec_sensor:
        vaciar()

    # Tablas resumen (se escriben al final, ya con los totales)
    filas_resumen = [
        (zona, (zona, dia, len(r[5]), r[0], r[1] / r[0], r[2] / r[0],
                r[3] / r[0], r[4]))
        for (zona, dia), r in resumen.items()
    ]
    total_batches += enviar_batches(session, stmt_resumen, filas_resumen)
    enviar_individuales(session, stmt_ultima, list(ultima.values()))

    duracion = time.time() - inicio
    print("-" * 50)
    print(f"Mediciones cargadas: {total:,}")
    print(f"Anomalías cargadas:  {total_anomalias:,}")
    print(f"Batches enviados:    {total_batches:,}")
    print(f"Tiempo:              {duracion:.1f} s")
    print(f"Velocidad:           {total / duracion:,.0f} filas/s")

    registrar_resultado(total, total_anomalias, total_batches, duracion)


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga de datos AquaSense CR")
    parser.add_argument("--limit", type=int, default=NUM_MEDICIONES,
                        help="cantidad de mediciones a cargar (default: 1,000,000)")
    args = parser.parse_args()

    cluster, session = conectar()
    try:
        sensores = generar_sensores()
        cargar_sensores(session, sensores)
        cargar_mediciones(session, sensores, args.limit)
    finally:
        cluster.shutdown()