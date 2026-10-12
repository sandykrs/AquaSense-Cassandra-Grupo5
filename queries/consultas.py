# %%
#Importar las librerias necesarias para hacer la conexion a cassandra y ejecutar las consultas.

#Librerias del driver cassandra
from cassandra.cluster import Cluster
from cassandra.query import dict_factory 

#Utilizado para usar identificadores UUID de los sensores
from uuid import UUID

#datetime para fechas y tiempos
from datetime import datetime, date 


# %%
#Ahora que ya se descargaron las librerias, se realiza la conexion entre python apache cassandra.

#Realizar la conexion cassandra mediante el driver pyhton.
cluster=Cluster(['127.0.0.1'])
session=cluster.connect()

#definir el formato, este formato devuelve las consultas como diccionario.
session.row_factory =dict_factory

#definir el nombre del keyspace (el keyspace es como la base donde se guardan todas las tablas que hagamos)
keyspace_nombre ='aquasense'


session.set_keyspace(keyspace_nombre)


# %%
#Consultas por realizar: 

#1. Ultimas lecturas de un sensor (ultimas 10):
def ultimas_lecturas_sensor(sensor_id, bucket):
    consulta ="""
    SELECT *
    FROM lecturas_por_sensor
    WHERE sensor_id = %s 
    AND bucket = %s
   LIMIT 10  
   """
    rows = session.execute(consulta, (sensor_id, bucket))
    return list(rows)

# %%
#2. Lecturas por rango temporal

def lecturas_por_rango(sensor_id, bucket, ts_inicio, ts_fin):
    consulta = """
    SELECT *
    FROM lecturas_por_sensor
    WHERE sensor_id = %s 
    AND bucket = %s
    AND fecha_hora >= %s 
    AND fecha_hora <= %s
    """
    rows = session.execute(consulta, (sensor_id, bucket, ts_inicio, ts_fin))
    return list(rows)

# %%
#3. Consulta por zona y periodo
def lecturas_por_zona_periodo(zona, bucket, ts_inicio, ts_fin):
    consulta = """
    SELECT *
    FROM lecturas_por_zona
    WHERE zona = %s 
    AND bucket = %s
    AND fecha_hora >= %s 
    AND fecha_hora <= %s
    """
    rows = session.execute(consulta, (zona, bucket, ts_inicio, ts_fin))
    return list(rows)

# %%
#4. Identificar anomalias: 
def anomalias_sensor(sensor_id, bucket):
    consulta = """
    SELECT *
    FROM anomalias_por_sensor
    WHERE sensor_id = %s
    AND bucket = %s
    """
    rows = session.execute(consulta, (sensor_id, bucket))
    return list(rows)


# %%
#5. La consulta optimizada escogida es un resumen diario por zona

def resumen_diario (zona):
    consulta = """
    SELECT *
    FROM resumen_diario_zona
    WHERE zona = %s
    """
    rows = session.execute(consulta, (zona,))
    return list(rows)


#%%
#Prueba consulta 1: Ultimas lecturas de un sensor

resultado = ultimas_lecturas_sensor(
        UUID("81df62f4-5bc6-47ca-abff-9286f0cf9d73"),
        date(2026, 1, 3)
    )

print(resultado)

#%%
#Prueba consulta 2: Lecturas por rango temporal

resultado = lecturas_por_rango(
        UUID("81df62f4-5bc6-47ca-abff-9286f0cf9d73"),
        date(2026, 1, 3),
        datetime(2026, 1, 3, 0, 0, 0),
        datetime(2026, 1, 3, 23, 59, 59)
    )

print(resultado)

#%%
#Prueba consulta 3: Consulta por zona y periodo

resultado = lecturas_por_zona_periodo(
    "puntarenas",
    date(2026, 1, 3),
    datetime(2026, 1, 3, 0, 0, 0),
    datetime(2026, 1, 3, 23, 59, 59)
)

print(resultado)  

#%%
#Prueba consulta 4: Identificar anomalias

resultado = anomalias_sensor(
        UUID("81df62f4-5bc6-47ca-abff-9286f0cf9d73"),
        date(2026, 1, 3)
    )

print(resultado)
#%%
#Prueba consulta 5: Consulta resumen diario

resultado = resumen_diario("puntarenas")
print(resultado)


