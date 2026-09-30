import os
import csv
import random
import uuid
from datetime import datetime, timedelta

try:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
except NameError:
    # Estamos en Jupyter: asumimos que el notebook está en la raíz del proyecto
    BASE_DIR = os.getcwd()

DATA_DIR = os.path.join(BASE_DIR, "data")
SAMPLE_DIR = os.path.join(DATA_DIR, "sample")

# Crear carpetas si no existen
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SAMPLE_DIR, exist_ok=True)

# ============================================================
# CONFIGURACIÓN
# ============================================================

NUM_SENSORES = 1000
NUM_ZONAS = 20
NUM_MEDICIONES = 1_000_000
PROPORCION_ANOMALIAS = 0.015  # 1.5%

# Rangos normales de las mediciones
RANGOS_NORMALES = {
    "flow": (10.0, 100.0),          # L/s
    "pressure": (1.5, 5.0),         # bar
    "temperature": (15.0, 30.0),    # °C
    "quality": (0, 2)               # 0=buena, 1=regular, 2=mala
}

# Tipos de anomalías
TIPOS_ANOMALIA = ["flow_high", "flow_low", "pressure_high", "pressure_low", "temp_high"]

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
ESTADOS_SENSOR = ["activo", "activo", "activo", "activo", "mantenimiento"]  # ~80% activos


# ============================================================
# FUNCIONES
# ============================================================

def generar_sensores():
    """
    Genera 1,000 sensores distribuidos en 20 zonas (50 por zona).
    Retorna una lista de diccionarios.
    """
    rng = random.Random(42)  # semilla fija -> datos reproducibles
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


def generar_mediciones(sensores):
    """
    Genera 1,000,000 de mediciones para los sensores dados.
    Retorna una lista de diccionarios.
    """
    # TODO (Día 3)
    pass


def detectar_anomalia(medicion):
    """
    Determina si una medición es anómala según umbrales.
    Retorna (is_anomaly, anomaly_type).
    """
    # TODO
    pass


def exportar_muestra(mediciones, num_filas=100):
    """
    Exporta una muestra pequeña a CSV para pruebas.
    """
    # TODO (Día 4)
    pass


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Generador de datos - AquaSense CR")
    print("=" * 60)
    print(f"Sensores a generar: {NUM_SENSORES}")
    print(f"Zonas: {NUM_ZONAS}")
    print(f"Mediciones: {NUM_MEDICIONES:,}")
    print(f"Proporción de anomalías: {PROPORCION_ANOMALIAS * 100}%")
    print(f"Directorio base detectado: {BASE_DIR}")
    print("=" * 60)

    sensores = generar_sensores()
    print(f"Sensores generados: {len(sensores)}")
    print(f"Zonas distintas: {len({s['zone_id'] for s in sensores})}")
    print(sensores[0])