

import os
import csv
import math
import random
import argparse
from uuid import UUID
from datetime import datetime, timedelta

# ============================================================
# CONFIGURACIÓN
# ============================================================
SEED = 42                      # mismo seed = mismos datos (reproducible)
NUM_SENSORES = 1_000
NUM_MEDICIONES = 1_000_000
FECHA_INICIO = datetime(2026, 1, 1, 0, 0, 0)
INTERVALO_MIN = 15             # cada sensor activo mide cada 15 minutos
PROB_INACTIVO = 0.05           # 5% de sensores inactivos (no generan lecturas)
PROB_ANOMALIA = 0.02           # 2% de las lecturas son anomalías

# zona -> (latitud, longitud) del centro de la zona (Costa Rica)
ZONAS = {
    "sanjose":    (9.9281, -84.0907),
    "alajuela":   (10.0162, -84.2116),
    "cartago":    (9.8644, -83.9194),
    "heredia":    (9.9981, -84.1198),
    "guanacaste": (10.6346, -85.4407),
    "puntarenas": (9.9763, -84.8384),
    "limon":      (9.9907, -83.0360),
}

TIPOS_SENSOR = ["multiparametro", "ultrasonico", "electromagnetico"]

# Tipos de anomalía (se guardan en el campo "motivo" de las tablas anomalias_*)
TIPOS_ANOMALIA = [
    "fuga",               # caudal alto + presión baja
    "presion_baja",
    "presion_alta",
    "temperatura_alta",
    "caudal_anomalo",
    "calidad_mala",
]

# Calidad: 0 = buena, 1 = regular, 2 = mala (cargar_datos.py lo traduce a texto)


# ============================================================
# SENSORES
# ============================================================

def generar_sensores(cantidad=NUM_SENSORES):
    """
    Retorna una lista de diccionarios, uno por sensor:
      sensor_id, zone_id, sensor_type, status ('activo'/'inactivo'),
      latitude, longitude, base_flow, base_pressure, base_temperature
    Los campos base_* son la "línea base" de cada sensor y NO se guardan
    en Cassandra; solo los usa generar_mediciones().
    """
    rng = random.Random(SEED)
    zonas = list(ZONAS.keys())
    sensores = []

    for i in range(cantidad):
        zona = zonas[i % len(zonas)]
        lat0, lon0 = ZONAS[zona]
        sensores.append({
            "sensor_id": str(UUID(int=rng.getrandbits(128), version=4)),
            "zone_id": zona,
            "sensor_type": rng.choice(TIPOS_SENSOR),
            "status": "inactivo" if rng.random() < PROB_INACTIVO else "activo",
            "latitude": round(lat0 + rng.uniform(-0.05, 0.05), 6),
            "longitude": round(lon0 + rng.uniform(-0.05, 0.05), 6),
            "base_flow": rng.uniform(20.0, 120.0),         # L/s
            "base_pressure": rng.uniform(40.0, 80.0),      # PSI
            "base_temperature": rng.uniform(18.0, 26.0),   # °C
        })
    return sensores


# ============================================================
# MEDICIONES
# ============================================================

def _aplicar_anomalia(rng, tipo, caudal, presion, temp):
    """Modifica los valores según el tipo de anomalía. Retorna (caudal, presion, temp, calidad)."""
    calidad = rng.choice([1, 2])
    if tipo == "fuga":
        caudal *= rng.uniform(1.6, 2.5)
        presion *= rng.uniform(0.4, 0.7)
    elif tipo == "presion_baja":
        presion *= rng.uniform(0.3, 0.6)
    elif tipo == "presion_alta":
        presion *= rng.uniform(1.5, 2.0)
    elif tipo == "temperatura_alta":
        temp += rng.uniform(8.0, 15.0)
    elif tipo == "caudal_anomalo":
        caudal *= rng.choice([rng.uniform(0.0, 0.3), rng.uniform(2.0, 3.0)])
    elif tipo == "calidad_mala":
        calidad = 2
    return caudal, presion, temp, calidad


def generar_mediciones(sensores, total=NUM_MEDICIONES):
    """
    Generador (yield) de mediciones en ORDEN DE TIEMPO.
    Cada ronda, todos los sensores activos miden una vez; se repite
    hasta completar `total` mediciones.

    Cada medición es un diccionario con:
      sensor_id, zone_id, day (YYYY-MM-DD), event_ts (YYYY-MM-DD HH:MM:SS),
      flow, pressure, temperature, quality (0/1/2),
      is_anomaly (bool), anomaly_type (str o None)
    """
    rng = random.Random(SEED + 1)
    activos = [s for s in sensores if s["status"] == "activo"]
    if not activos:
        return

    # Desfase fijo (segundos) por sensor, para que no midan todos al mismo instante
    desfase = {s["sensor_id"]: rng.randint(0, 59) for s in activos}

    generadas = 0
    ronda = 0
    while generadas < total:
        base_ts = FECHA_INICIO + timedelta(minutes=INTERVALO_MIN * ronda)
        # Ciclo diario: más consumo de día que de madrugada
        hora = base_ts.hour + base_ts.minute / 60
        factor_dia = 1.0 + 0.3 * math.sin((hora - 6) / 24 * 2 * math.pi)

        for s in activos:
            if generadas >= total:
                return
            ts = base_ts + timedelta(seconds=desfase[s["sensor_id"]])

            caudal = s["base_flow"] * factor_dia * rng.gauss(1.0, 0.05)
            presion = s["base_pressure"] * rng.gauss(1.0, 0.03)
            temp = s["base_temperature"] + rng.gauss(0.0, 0.8)
            calidad = 0 if rng.random() < 0.92 else 1

            es_anomalia = rng.random() < PROB_ANOMALIA
            tipo = None
            if es_anomalia:
                tipo = rng.choice(TIPOS_ANOMALIA)
                caudal, presion, temp, calidad = _aplicar_anomalia(
                    rng, tipo, caudal, presion, temp)

            yield {
                "sensor_id": s["sensor_id"],
                "zone_id": s["zone_id"],
                "day": ts.strftime("%Y-%m-%d"),
                "event_ts": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "flow": round(max(caudal, 0.0), 2),
                "pressure": round(max(presion, 0.0), 2),
                "temperature": round(temp, 2),
                "quality": calidad,
                "is_anomaly": es_anomalia,
                "anomaly_type": tipo,
            }
            generadas += 1
        ronda += 1


# ============================================================
# MUESTRA CSV (Día 4 del calendario: "Muestra 100 filas CSV")
# ============================================================

def guardar_muestra(filas=100):
    sensores = generar_sensores()
    carpeta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, f"muestra_{filas}.csv")

    campos = ["sensor_id", "zone_id", "day", "event_ts", "flow", "pressure",
              "temperature", "quality", "is_anomaly", "anomaly_type"]
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for m in generar_mediciones(sensores, total=filas):
            w.writerow(m)
    return ruta


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generador de datos AquaSense CR")
    parser.add_argument("--filas", type=int, default=100,
                        help="filas de la muestra CSV (default: 100)")
    args = parser.parse_args()

    sensores = generar_sensores()
    activos = sum(1 for s in sensores if s["status"] == "activo")
    print(f"Sensores: {len(sensores)} ({activos} activos) en {len(ZONAS)} zonas")
    print(f"Muestra guardada en: {guardar_muestra(args.filas)}")