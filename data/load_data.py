
"""
Carga de datos AquaSense CR a Apache Cassandra.
Requiere generate_data.py en la misma carpeta.

  python load_data.py                  # carga 1M mediciones
  python load_data.py --benchmark      # prueba configuraciones de batch
  python load_data.py --stress-profile # escribe perfiles cassandra-stress
"""
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

# Configuraciones que prueba --benchmark: (batch, concurrencia, buffer)
CONFIGS_BENCHMARK = [
    (1,   32, 20_000),    # base: casi sin agrupar
    (10,  32, 20_000),
    (25,  32, 20_000),
    (50,  32, 20_000),    # configuración por defecto
    (100, 32, 20_000),
    (50,  32, 50_000),    # buffer más grande
    (50,  32, 100_000),
    (50,  16, 20_000),    # menos concurrencia
    (50,  64, 20_000),    # más concurrencia
    (50, 128, 20_000),
]
LIMITE_BENCHMARK = 100_000


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


def cargar_mediciones(session, sensores, limite, verbose=True, registrar=True):
    """
    Carga las mediciones en Cassandra. Retorna un diccionario con el resultado.
    verbose=False silencia los prints (lo usa --benchmark).
    registrar=False no escribe en resultados_carga.csv.
    """
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
            if verbose:
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
    velocidad = total / duracion

    if verbose:
        print("-" * 50)
        print(f"Mediciones cargadas: {total:,}")
        print(f"Anomalías cargadas:  {total_anomalias:,}")
        print(f"Batches enviados:    {total_batches:,}")
        print(f"Tiempo:              {duracion:.1f} s")
        print(f"Velocidad:           {velocidad:,.0f} filas/s")

    if registrar:
        registrar_resultado(total, total_anomalias, total_batches, duracion)

    return {"filas": total, "anomalias": total_anomalias,
            "batches": total_batches, "duracion": duracion,
            "filas_por_seg": velocidad}


def benchmark(session, sensores, limite=LIMITE_BENCHMARK):
    """
    Prueba varias combinaciones de batch / concurrencia / buffer y muestra
    un ranking. Cada corrida queda registrada en resultados_carga.csv.
    """
    global TAMANO_BATCH, TAMANO_BUFFER, CONCURRENCIA
    original = (TAMANO_BATCH, TAMANO_BUFFER, CONCURRENCIA)
    resultados = []

    try:
        print("Calentamiento (no cuenta en el ranking)...")
        TAMANO_BATCH, TAMANO_BUFFER, CONCURRENCIA = 50, 20_000, 32
        cargar_mediciones(session, sensores, 20_000, verbose=False, registrar=False)

        for i, (b, c, buf) in enumerate(CONFIGS_BENCHMARK, 1):
            TAMANO_BATCH, CONCURRENCIA, TAMANO_BUFFER = b, c, buf
            print(f"Prueba {i}/{len(CONFIGS_BENCHMARK)}: batch={b} "
                  f"concurrencia={c} buffer={buf:,} ...")
            r = cargar_mediciones(session, sensores, limite, verbose=False)
            resultados.append((b, c, buf, r))
    finally:
        TAMANO_BATCH, TAMANO_BUFFER, CONCURRENCIA = original

    resultados.sort(key=lambda x: x[3]["filas_por_seg"], reverse=True)

    print("\n" + "=" * 62)
    print(f"{'batch':>6} {'concurr.':>9} {'buffer':>9} {'batches':>9} {'seg':>7} {'filas/s':>9}")
    print("=" * 62)
    for b, c, buf, r in resultados:
        print(f"{b:>6} {c:>9} {buf:>9,} {r['batches']:>9,} "
              f"{r['duracion']:>7.1f} {r['filas_por_seg']:>9,.0f}")
    print("=" * 62)
    b, c, buf, r = resultados[0]
    print(f"Mejor: batch={b} concurrencia={c} buffer={buf:,} "
          f"({r['filas_por_seg']:,.0f} filas/s)")



# ============================================================
# PERFILES cassandra-stress (se escriben con: --stress-profile)
# Van aquí dentro para mantener todo en generate_data.py + load_data.py
# ============================================================

PERFIL_STRESS_SENSOR = r"""# ============================================================================
# Perfil cassandra-stress - AquaSense CR  |  Tabla: lecturas_por_sensor
# Grupo 5 - XS0131 | Integrante B (Ingeniero de Datos)
#
# Usa un keyspace APARTE (aquasense_stress) para no mezclar los datos de
# prueba con el 1M real del keyspace "aquasense". La tabla es idéntica a
# lecturas_por_sensor de cql/schema.cql.
#
# Pasos (la fase de escritura va PRIMERO para que las lecturas encuentren datos):
#   1) Escritura:
#      cassandra-stress user profile=aquasense_sensor.yaml n=50000 "ops(insert=1)" -rate threads=16 -node 127.0.0.1
#   2) Lectura:
#      cassandra-stress user profile=aquasense_sensor.yaml duration=2m "ops(por_sensor_dia=3,ultimas_10=7)" -rate threads=16 -node 127.0.0.1
#   3) Mixto (escritura + lectura):
#      cassandra-stress user profile=aquasense_sensor.yaml duration=2m "ops(insert=2,por_sensor_dia=3,ultimas_10=5)" -rate threads=16 -node 127.0.0.1
#   Para comparar concurrencia, repetir cambiando threads=8 / 16 / 32 / 64.
# ============================================================================

keyspace: aquasense_stress

keyspace_definition: |
  CREATE KEYSPACE IF NOT EXISTS aquasense_stress
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

table: lecturas_por_sensor

table_definition: |
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

# Mismo tamaño que los datos reales: 1,000 sensores x 11 días = 11,000
# particiones, con 96 lecturas por partición (una cada 15 minutos).
columnspec:
  - name: sensor_id
    population: uniform(1..1000)
  - name: bucket
    population: uniform(1..11)
  - name: fecha_hora
    cluster: fixed(96)
  - name: zona
    size: fixed(10)
    population: uniform(1..20)
  - name: calidad
    size: fixed(6)

insert:
  partitions: fixed(1)        # una partición (sensor, día) por operación
  select: fixed(1)/1          # se insertan todas sus filas
  batchtype: UNLOGGED

queries:
  por_sensor_dia:             # todas las lecturas de un sensor en un día
    cql: SELECT * FROM lecturas_por_sensor WHERE sensor_id = ? AND bucket = ? LIMIT 96
    fields: samerow
  ultimas_10:                 # las 10 lecturas más recientes (orden DESC)
    cql: SELECT fecha_hora, caudal, presion, temperatura FROM lecturas_por_sensor WHERE sensor_id = ? AND bucket = ? LIMIT 10
    fields: samerow
"""

PERFIL_STRESS_ZONA = r"""# ============================================================================
# Perfil cassandra-stress - AquaSense CR  |  Tabla: lecturas_por_zona
# Grupo 5 - XS0131 | Integrante B (Ingeniero de Datos)
#
# Misma idea que aquasense_sensor.yaml, pero para la tabla por zona, cuyas
# particiones son MUCHO más grandes (todos los sensores de la zona en un día).
# En los datos reales una partición (zona, día) tiene ~4,600 filas (96 lecturas x ~48 sensores activos por zona); aquí se
# usan 96 x 48 = 4,608 filas por partición.
#
#   1) Escritura:
#      cassandra-stress user profile=aquasense_zona.yaml n=5000 "ops(insert=1)" -rate threads=16 -node 127.0.0.1
#   2) Lectura:
#      cassandra-stress user profile=aquasense_zona.yaml duration=2m "ops(por_zona_dia=3,ultimas_100=7)" -rate threads=16 -node 127.0.0.1
# ============================================================================

keyspace: aquasense_stress

keyspace_definition: |
  CREATE KEYSPACE IF NOT EXISTS aquasense_stress
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

table: lecturas_por_zona

table_definition: |
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

# 20 zonas x 11 días = 220 particiones
columnspec:
  - name: zona
    size: fixed(10)
    population: uniform(1..20)
  - name: bucket
    population: uniform(1..11)
  - name: fecha_hora
    cluster: fixed(96)
  - name: sensor_id
    cluster: fixed(48)
  - name: calidad
    size: fixed(6)

insert:
  partitions: fixed(1)
  select: fixed(1)/1
  batchtype: UNLOGGED

queries:
  por_zona_dia:               # lecturas de una zona en un día (limitado)
    cql: SELECT * FROM lecturas_por_zona WHERE zona = ? AND bucket = ? LIMIT 500
    fields: samerow
  ultimas_100:                # las 100 lecturas más recientes de la zona
    cql: SELECT fecha_hora, sensor_id, caudal, presion FROM lecturas_por_zona WHERE zona = ? AND bucket = ? LIMIT 100
    fields: samerow
"""


def escribir_perfiles_stress(carpeta="stress"):
    """Escribe los dos perfiles YAML de cassandra-stress en `carpeta`."""
    base = os.path.dirname(os.path.abspath(__file__))
    destino = os.path.join(base, carpeta)
    os.makedirs(destino, exist_ok=True)
    for nombre, texto in (("aquasense_sensor.yaml", PERFIL_STRESS_SENSOR),
                          ("aquasense_zona.yaml", PERFIL_STRESS_ZONA)):
        ruta = os.path.join(destino, nombre)
        with open(ruta, "w", encoding="utf-8", newline="\n") as f:
            f.write(texto)
        print(f"Perfil escrito: {ruta}")


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga de datos AquaSense CR")
    parser.add_argument("--limit", type=int, default=NUM_MEDICIONES,
                        help="cantidad de mediciones a cargar (default: 1,000,000)")
    parser.add_argument("--batch", type=int, default=TAMANO_BATCH,
                        help=f"filas por batch (default: {TAMANO_BATCH})")
    parser.add_argument("--concurrency", type=int, default=CONCURRENCIA,
                        help=f"operaciones en paralelo (default: {CONCURRENCIA})")
    parser.add_argument("--buffer", type=int, default=TAMANO_BUFFER,
                        help=f"filas acumuladas antes de enviar (default: {TAMANO_BUFFER})")
    parser.add_argument("--benchmark", action="store_true",
                        help="prueba varias configuraciones y muestra el ranking")
    parser.add_argument("--stress-profile", action="store_true",
                        help="escribe los perfiles de cassandra-stress (stress/*.yaml) y termina")
    args = parser.parse_args()

    if args.stress_profile:
        escribir_perfiles_stress()
        raise SystemExit(0)

    TAMANO_BATCH = args.batch
    CONCURRENCIA = args.concurrency
    TAMANO_BUFFER = args.buffer

    cluster, session = conectar()
    try:
        sensores = generar_sensores()
        cargar_sensores(session, sensores)

        if args.benchmark:
            benchmark(session, sensores)
        else:
            print(f"Config: batch={TAMANO_BATCH} | concurrencia={CONCURRENCIA} | "
                  f"buffer={TAMANO_BUFFER:,} | filas={args.limit:,}")
            cargar_mediciones(session, sensores, args.limit)
    finally:
        cluster.shutdown()