"""Benchmark de escritura: carga de 1 000 000 de mediciones con dos motores de conexion.

Uso:  python performance/benchmark_escritura.py --corridas 3
Cada corrida vacia las tablas, carga el millon con data/load_data.py y verifica el total.
Los motores se alternan (asyncio, asyncore, asyncio, ...) para que el orden no favorezca a uno.
Genera performance/resultados/benchmark_escritura.csv
"""
import argparse
import csv
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path

from cassandra.cluster import Cluster
from cassandra.io.asyncioreactor import AsyncioConnection

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "performance" / "resultados" / "benchmark_escritura.csv"
TABLAS = ["lecturas_por_sensor", "lecturas_por_zona", "ultima_lectura_sensor",
          "anomalias_por_sensor", "anomalias_por_zona", "resumen_diario_zona",
          "sensores", "sensores_por_zona"]

# Ejecuta data/load_data.py cambiando solo el motor de conexion del driver.
CODIGO_ASYNCIO = (
    "import sys, runpy\n"
    "sys.path.insert(0, 'data')\n"
    "from cassandra.cluster import Cluster\n"
    "from cassandra.io.asyncioreactor import AsyncioConnection\n"
    "_orig = Cluster.__init__\n"
    "def _init(self, *a, **k):\n"
    "    k.setdefault('connection_class', AsyncioConnection)\n"
    "    _orig(self, *a, **k)\n"
    "Cluster.__init__ = _init\n"
    "sys.argv = ['load_data.py']\n"
    "runpy.run_path('data/load_data.py', run_name='__main__')\n"
)


def ejecutar(cmd):
    entorno = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run(cmd, cwd=RAIZ, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=entorno)
    if r.returncode != 0:
        print(r.stdout[-1500:])
        print(r.stderr[-1500:])
        raise SystemExit("El comando fallo, revisa el mensaje de arriba.")
    return r.stdout


def vaciar():
    cluster = Cluster(["127.0.0.1"], port=9042, connection_class=AsyncioConnection)
    session = cluster.connect("aquasense")
    for tabla in TABLAS:
        session.execute(f"TRUNCATE {tabla}", timeout=120)
    cluster.shutdown()


def cargar(motor):
    if motor == "asyncio":
        salida = ejecutar([sys.executable, "-c", CODIGO_ASYNCIO])
    else:
        salida = ejecutar([sys.executable, "data/load_data.py"])
    tiempo = re.search(r"Tiempo:\s+([\d.]+)", salida)
    velocidad = re.search(r"Velocidad:\s+([\d,]+)", salida)
    if not tiempo or not velocidad:
        print(salida[-1500:])
        raise SystemExit("No pude leer el tiempo del cargador.")
    return float(tiempo.group(1)), float(velocidad.group(1).replace(",", ""))


def verificar():
    salida = ejecutar([sys.executable, "performance/verificar_carga.py"])
    total = re.search(r"Filas totales:\s+([\d,]+)", salida)
    return int(total.group(1).replace(",", "")) if total else -1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corridas", type=int, default=3)
    parser.add_argument("--motores", default="asyncio,asyncore")
    args = parser.parse_args()
    motores = args.motores.split(",")

    filas = []
    for n in range(1, args.corridas + 1):
        for motor in motores:
            print(f"Corrida {n} con {motor}: vaciando tablas y cargando...", flush=True)
            vaciar()
            segundos, velocidad = cargar(motor)
            total = verificar()
            estado = "OK" if total == 1_000_000 else "REVISAR"
            print(f"  {segundos:.1f} s | {velocidad:,.0f} filas/s | verificadas: {total:,} [{estado}]",
                  flush=True)
            filas.append([motor, n, segundos, velocidad, total])

    SALIDA.parent.mkdir(exist_ok=True)
    with open(SALIDA, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["motor", "corrida", "segundos", "filas_por_s", "filas_verificadas"])
        escritor.writerows(filas)

    print("\nResumen por motor")
    for motor in motores:
        tiempos = [f[2] for f in filas if f[0] == motor]
        vel = [f[3] for f in filas if f[0] == motor]
        de = statistics.stdev(tiempos) if len(tiempos) > 1 else 0.0
        print(f"  {motor:<8} tiempo medio {statistics.mean(tiempos):.1f} s (desv. {de:.1f}) | "
              f"velocidad media {statistics.mean(vel):,.0f} filas/s")
    print(f"\nResultados guardados en {SALIDA}")


main()
