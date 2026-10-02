import os
import csv
import time
import random
import uuid
from datetime import datetime, timedelta
from itertools import islice

try:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    BASE_DIR = os.getcwd()

DATA_DIR = os.path.join(BASE_DIR, "data")
SAMPLE_DIR = os.path.join(DATA_DIR, "sample")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SAMPLE_DIR, exist_ok=True)

# ============================================================
# CONFIGURACIÓN
# ============================================================

NUM_SENSORES = 1000
NUM_ZONAS = 20
NUM_MEDICIONES = 1_000_000
PROPORCION_ANOMALIAS = 0.015  # 1.5%

RANGOS_NORMALES = {
    "flow": (10.0, 100.0),          # L/s
    "pressure": (1.5, 5.0),         # bar
    "temperature": (15.0, 30.0),    # °C
    "quality": (0, 2)               # 0=buena, 1=regular, 2=mala
}

TIPOS_ANOMALIA = ["flow_high", "flow_low", "pressure_high", "pressure_low", "temp_high"]

# Ventana de tiempo de las mediciones (30 días)
FECHA_INICIO_MEDICIONES = datetime(2026, 9, 1)
DIAS_MEDICIONES = 30

# Columnas del CSV de muestra (en este orden)
COLUMNAS_MEDICION = [
    "sensor_id", "zone_id", "day", "event_ts",
    "flow", "pressure", "temperature", "quality",
    "is_anomaly", "anomaly_type",
]

# ============================================================
# ZONAS (20 zonas de Costa Rica con coordenadas aproximadas)
# ============================================================
ZONAS = [
    ("Z01", "San José", 9.9281, -84.0907),
    ("Z02", "Cartago", 9.8644, -83.9194),
    ("Z03", "Heredia", 9.9986, -84.1165),
    ("Z04", "Alajuela", 10.0162, -84.2116),
    ("Z05", "Liberia", 10.6346, -85.4407),
    ("Z06", "Puntarenas", 9.9763, -84.8384),
    ("Z07", "Limón", 9.9907, -83.0360),
    ("Z08", "San Carlos", 10.3237, -84.4302),
    ("Z09", "Pérez Zeledón", 9.3735, -83.7020),
    ("Z10", "Nicoya", 10.1483, -85.4520),
    ("Z11", "Quepos", 9.4316, -84.1620),
    ("Z12", "Golfito", 8.6396, -83.1646),
    ("Z13", "Turrialba", 9.9047, -83.6836),
    ("Z14", "Grecia", 10.0725, -84.3106),
    ("Z15", "Upala", 10.8975, -85.0157),
    ("Z16", "Sarapiquí", 10.4667, -84.0167),
    ("Z17", "Santa Cruz", 10.2606, -85.5878),
    ("Z18", "Jacó", 9.6150, -84.6290),
    ("Z19", "Cañas", 10.4300, -85.0980),
    ("Z20", "Ciudad Neily", 8.6519, -82.9394),
]

TIPOS_SENSOR = ["caudal", "presion", "temperatura", "calidad"]
ESTADOS_SENSOR = ["activo", "activo", "activo", "activo", "mantenimiento"]


# ============================================================
# FUNCIONES
# ============================================================

def generar_sensores():
    """
    Genera 1,000 sensores distribuidos en 20 zonas (50 por zona).
    Retorna una lista de diccionarios.
    """
    rng = random.Random(42)
    sensores_por_zona = NUM_SENSORES // NUM_ZONAS
    fecha_base = datetime(2022, 1, 1)
    sensores = []
    contador = 1

    for zone_id, zone_name, lat, lon in ZONAS[:NUM_ZONAS]:
        for _ in range(sensores_por_zona):
            sensores.append({
                "sensor_id": str(uuid.UUID(int=rng.getrandbits(128), version=4)),
                "sensor_name": f"SENS-{contador:04d}",
                "zone_id": zone_id,
                "zone_name": zone_name,
                "sensor_type": rng.choice(TIPOS_SENSOR),
                "latitude": round(lat + rng.uniform(-0.05, 0.05), 6),
                "longitude": round(lon + rng.uniform(-0.05, 0.05), 6),
                "install_date": (fecha_base + timedelta(days=rng.randint(0, 1400))).date().isoformat(),
                "status": rng.choice(ESTADOS_SENSOR),
            })
            contador += 1

    return sensores


def detectar_anomalia(medicion):
    """
    Determina si una medición es anómala según umbrales.
    Retorna (is_anomaly, anomaly_type).
    """
    flow_min, flow_max = RANGOS_NORMALES["flow"]
    pres_min, pres_max = RANGOS_NORMALES["pressure"]
    _, temp_max = RANGOS_NORMALES["temperature"]

    if medicion["flow"] > flow_max:
        return True, "flow_high"
    if medicion["flow"] < flow_min:
        return True, "flow_low"
    if medicion["pressure"] > pres_max:
        return True, "pressure_high"
    if medicion["pressure"] < pres_min:
        return True, "pressure_low"
    if medicion["temperature"] > temp_max:
        return True, "temp_high"
    return False, None


def generar_mediciones(sensores):
    """
    Genera 1,000,000 de mediciones para los sensores dados.
    Es un generador: devuelve una medición (diccionario) a la vez,
    así no se carga todo en memoria.
    """
    rng = random.Random(123)
    n_sensores = len(sensores)
    segundos_totales = DIAS_MEDICIONES * 24 * 3600
    lecturas_por_sensor = NUM_MEDICIONES // n_sensores
    paso_seg = segundos_totales // lecturas_por_sensor

    def valor_anomalo(tipo, m):
        if tipo == "flow_high":
            m["flow"] = round(rng.uniform(100.5, 150.0), 2)
        elif tipo == "flow_low":
            m["flow"] = round(rng.uniform(0.5, 9.5), 2)
        elif tipo == "pressure_high":
            m["pressure"] = round(rng.uniform(5.2, 7.0), 2)
        elif tipo == "pressure_low":
            m["pressure"] = round(rng.uniform(0.2, 1.4), 2)
        elif tipo == "temp_high":
            m["temperature"] = round(rng.uniform(31.0, 40.0), 1)

    for i in range(NUM_MEDICIONES):
        sensor = sensores[i % n_sensores]
        ronda = i // n_sensores
        ts = FECHA_INICIO_MEDICIONES + timedelta(
            seconds=ronda * paso_seg + rng.randint(0, 59)
        )

        medicion = {
            "sensor_id": sensor["sensor_id"],
            "zone_id": sensor["zone_id"],
            "day": ts.date().isoformat(),
            "event_ts": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "flow": round(rng.uniform(*RANGOS_NORMALES["flow"]), 2),
            "pressure": round(rng.uniform(*RANGOS_NORMALES["pressure"]), 2),
            "temperature": round(rng.uniform(*RANGOS_NORMALES["temperature"]), 1),
            "quality": rng.choices([0, 1, 2], weights=[80, 15, 5])[0],
        }

        if rng.random() < PROPORCION_ANOMALIAS:
            valor_anomalo(rng.choice(TIPOS_ANOMALIA), medicion)

        es_anomalia, tipo = detectar_anomalia(medicion)
        medicion["is_anomaly"] = es_anomalia
        medicion["anomaly_type"] = tipo

        yield medicion


def exportar_muestra(mediciones, num_filas=100):
    """
    Exporta una muestra pequeña a CSV para pruebas.
    Recibe el generador de mediciones y toma una fila cada ~10,000,
    para que la muestra tenga sensores y zonas variados.
    Retorna la ruta del archivo creado.
    """
    # Paso que NO es múltiplo de 1000, así no se repite siempre el mismo sensor
    paso = (NUM_MEDICIONES // num_filas) + 7
    muestra = list(islice(islice(mediciones, 0, None, paso), num_filas))

    ruta = os.path.join(SAMPLE_DIR, "sample_mediciones.csv")
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS_MEDICION)
        escritor.writeheader()
        escritor.writerows(muestra)

    return ruta


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Generador de datos - AquaSense CR")
    print("=" * 60)

    sensores = generar_sensores()
    print(f"Sensores generados: {len(sensores)}")

    inicio = time.time()
    ruta = exportar_muestra(generar_mediciones(sensores), num_filas=100)
    duracion = time.time() - inicio

    with open(ruta, encoding="utf-8") as f:
        filas = sum(1 for _ in f) - 1  # menos el encabezado

    print(f"Muestra exportada: {ruta}")
    print(f"Filas en el CSV: {filas}")
    print(f"Tiempo: {duracion:.1f} segundos")