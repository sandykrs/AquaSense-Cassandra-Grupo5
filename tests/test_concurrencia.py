"""Pruebas de concurrencia en un keyspace aparte (aquasense_test).
No modifica los datos de aquasense.
Uso: python tests/test_concurrencia.py
"""
import datetime
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor

from cassandra.cluster import Cluster
from cassandra.io.asyncioreactor import AsyncioConnection

cluster = Cluster(["127.0.0.1"], port=9042, connection_class=AsyncioConnection)
setup = cluster.connect()
setup.execute(
    "CREATE KEYSPACE IF NOT EXISTS aquasense_test "
    "WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}")
session = cluster.connect("aquasense_test")
session.execute(
    "CREATE TABLE IF NOT EXISTS lecturas_test ("
    "sensor_id uuid, bucket date, fecha_hora timestamp, caudal double, "
    "PRIMARY KEY ((sensor_id, bucket), fecha_hora))")

FECHA = datetime.date(2026, 1, 1)
BASE = datetime.datetime(2026, 1, 1, 0, 0, 0)
INSERTAR = session.prepare(
    "INSERT INTO lecturas_test (sensor_id, bucket, fecha_hora, caudal) VALUES (?, ?, ?, ?)")
CONTAR = session.prepare(
    "SELECT COUNT(*) FROM lecturas_test WHERE sensor_id = ? AND bucket = ?")
LEER = session.prepare(
    "SELECT fecha_hora, caudal FROM lecturas_test WHERE sensor_id = ? AND bucket = ?")


def contar(sensor):
    return session.execute(CONTAR, [sensor, FECHA]).one()[0]


class PruebasConcurrencia(unittest.TestCase):

    def test_escrituras_concurrentes_no_pierden_filas(self):
        hilos, por_hilo = 8, 2000
        sensores = [uuid.uuid4() for _ in range(10)]

        def escribir(h):
            for j in range(por_hilo):
                momento = BASE + datetime.timedelta(seconds=h * por_hilo + j)
                session.execute(INSERTAR, [sensores[j % 10], FECHA, momento, float(h)])

        with ThreadPoolExecutor(max_workers=hilos) as pool:
            for futuro in [pool.submit(escribir, h) for h in range(hilos)]:
                futuro.result()
        self.assertEqual(sum(contar(s) for s in sensores), hilos * por_hilo)

    def test_misma_clave_queda_una_sola_fila(self):
        sensor = uuid.uuid4()
        hilos = 8

        def escribir(h):
            for _ in range(50):
                session.execute(INSERTAR, [sensor, FECHA, BASE, float(h)])

        with ThreadPoolExecutor(max_workers=hilos) as pool:
            for futuro in [pool.submit(escribir, h) for h in range(hilos)]:
                futuro.result()
        filas = list(session.execute(LEER, [sensor, FECHA]))
        self.assertEqual(len(filas), 1)
        self.assertIn(filas[0].caudal, [float(h) for h in range(hilos)])

    def test_lecturas_mientras_se_escribe(self):
        sensor = uuid.uuid4()
        escritores, por_escritor, lectores = 4, 1000, 4

        def escribir(h):
            for j in range(por_escritor):
                momento = BASE + datetime.timedelta(seconds=h * por_escritor + j)
                session.execute(INSERTAR, [sensor, FECHA, momento, float(h)])

        def leer(_):
            for _ in range(100):
                filas = list(session.execute(LEER, [sensor, FECHA]))
                assert len(filas) <= escritores * por_escritor

        with ThreadPoolExecutor(max_workers=escritores + lectores) as pool:
            futuros = [pool.submit(escribir, h) for h in range(escritores)]
            futuros += [pool.submit(leer, k) for k in range(lectores)]
            for futuro in futuros:
                futuro.result()
        self.assertEqual(contar(sensor), escritores * por_escritor)


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        setup.execute("DROP KEYSPACE IF EXISTS aquasense_test")
        cluster.shutdown()
