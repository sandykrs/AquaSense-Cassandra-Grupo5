
"""Pruebas funcionales de las consultas de AquaSense (requiere los datos cargados).
Uso: python tests/test_consultas.py
"""
import unittest

from cassandra import InvalidRequest
from cassandra.cluster import Cluster
from cassandra.io.asyncioreactor import AsyncioConnection

cluster = Cluster(["127.0.0.1"], port=9042, connection_class=AsyncioConnection)
session = cluster.connect("aquasense")

TABLAS = {"sensores", "sensores_por_zona", "lecturas_por_sensor", "lecturas_por_zona",
          "anomalias_por_sensor", "anomalias_por_zona", "resumen_diario_zona",
          "ultima_lectura_sensor"}

# Dias (buckets) disponibles por sensor
BUCKETS = {}
for f in session.execute("SELECT DISTINCT sensor_id, bucket FROM lecturas_por_sensor", timeout=300):
    BUCKETS.setdefault(f.sensor_id, []).append(f.bucket)
for lista in BUCKETS.values():
    lista.sort(key=lambda d: d.days_from_epoch)

LECTURAS_DIA = session.prepare(
    "SELECT * FROM lecturas_por_sensor WHERE sensor_id = ? AND bucket = ?")
LECTURAS_DIAS = session.prepare(
    "SELECT * FROM lecturas_por_sensor WHERE sensor_id = ? AND bucket IN ?")
LECTURAS_ZONA = session.prepare(
    "SELECT * FROM lecturas_por_zona WHERE zona = ? AND bucket = ?")
ANOMALIAS_SENSOR = session.prepare(
    "SELECT * FROM anomalias_por_sensor WHERE sensor_id = ? AND bucket = ?")
RESUMEN_ZONA = session.prepare(
    "SELECT * FROM resumen_diario_zona WHERE zona = ? LIMIT 7")
MAS_RECIENTE = session.prepare(
    "SELECT fecha_hora FROM lecturas_por_sensor WHERE sensor_id = ? AND bucket = ? LIMIT 1")
ULTIMA = session.prepare(
    "SELECT fecha_hora FROM ultima_lectura_sensor WHERE sensor_id = ?")


class PruebasConsultas(unittest.TestCase):

    def test_tablas_existen(self):
        filas = session.execute(
            "SELECT table_name FROM system_schema.tables WHERE keyspace_name = 'aquasense'")
        self.assertTrue(TABLAS.issubset({f.table_name for f in filas}))

    def test_cantidad_de_sensores_y_zonas(self):
        sensores = list(session.execute("SELECT sensor_id, zona FROM sensores"))
        self.assertEqual(len(sensores), 1000)
        self.assertEqual(len({s.zona for s in sensores}), 20)

    def test_lecturas_de_un_sensor_ordenadas_por_tiempo(self):
        sensor = next(iter(BUCKETS))
        filas = list(session.execute(LECTURAS_DIA, [sensor, BUCKETS[sensor][0]]))
        self.assertGreater(len(filas), 0)
        self.assertTrue(all(f.sensor_id == sensor for f in filas))
        tiempos = [f.fecha_hora for f in filas]
        self.assertEqual(tiempos, sorted(tiempos, reverse=True))

    def test_rango_de_siete_dias(self):
        sensor = next(iter(BUCKETS))
        dias = BUCKETS[sensor][:7]
        filas = list(session.execute(LECTURAS_DIAS, [sensor, dias]))
        esperado = sum(len(list(session.execute(LECTURAS_DIA, [sensor, d]))) for d in dias)
        self.assertEqual({f.sensor_id for f in filas}, {sensor})
        self.assertEqual(len(filas), esperado)

    def test_lecturas_por_zona_y_dia(self):
        sensor = next(iter(BUCKETS))
        zona = session.execute("SELECT zona FROM sensores WHERE sensor_id = %s", [sensor]).one().zona
        filas = list(session.execute(LECTURAS_ZONA, [zona, BUCKETS[sensor][0]]))
        self.assertGreater(len(filas), 0)
        tiempos = [f.fecha_hora for f in filas]
        self.assertEqual(tiempos, sorted(tiempos, reverse=True))

    def test_no_se_permite_escaneo_sin_clave_de_particion(self):
        with self.assertRaises(InvalidRequest):
            session.execute("SELECT * FROM lecturas_por_sensor WHERE zona = 'Z01'")

    def test_anomalias_coinciden_con_lecturas(self):
        f = session.execute("SELECT sensor_id, bucket FROM anomalias_por_sensor LIMIT 1").one()
        anomalias = list(session.execute(ANOMALIAS_SENSOR, [f.sensor_id, f.bucket]))
        lecturas = {r.fecha_hora: r.anomalia
                    for r in session.execute(LECTURAS_DIA, [f.sensor_id, f.bucket])}
        self.assertGreater(len(anomalias), 0)
        for a in anomalias:
            self.assertTrue(lecturas.get(a.fecha_hora))

    def test_ultima_lectura_es_la_mas_reciente(self):
        sensor = next(iter(BUCKETS))
        reciente = session.execute(MAS_RECIENTE, [sensor, BUCKETS[sensor][-1]]).one()
        ultima = session.execute(ULTIMA, [sensor]).one()
        self.assertEqual(ultima.fecha_hora, reciente.fecha_hora)

    def test_resumen_diario_de_una_zona(self):
        zona = session.execute("SELECT zona FROM sensores_por_zona LIMIT 1").one().zona
        filas = list(session.execute(RESUMEN_ZONA, [zona]))
        self.assertGreater(len(filas), 0)
        self.assertTrue(all(f.total_lecturas > 0 for f in filas))


if __name__ == "__main__":
    try:
        unittest.main(verbosity=2)
    finally:
        cluster.shutdown()