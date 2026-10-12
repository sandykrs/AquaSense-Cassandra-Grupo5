
# AquaSense CR - Monitoreo de Redes de Agua Potable

**Curso:** XS0131 Gestión de Bases de Datos y Análisis de Información  
**Universidad de Costa Rica - Escuela de Estadística**  
**Modelo NoSQL:** Columnas Anchas (Wide-Column)  
**Tecnología:** Apache Cassandra  

## Integrantes - Grupo 5
* Sandy Ruiz Salazar
* Jeferson Salazar Zambrana
* Estefanía Núñez Jimenéz
* keylor Gómez Jiménez
* Jimena Díaz González

## Descripción del Proyecto
AquaSense CR es un sistema diseñado para monitorear redes de agua potable mediante sensores de caudal, presión, temperatura y calidad. Este repositorio contiene la implementación de una capa de datos de alta velocidad en **Apache Cassandra** capaz de soportar la ingesta continua de datos de telemetría y consultar eficientemente series de tiempo por sensor y por intervalo.

## Guía de Ejecución Rápida 

### Prerrequisitos
1. Tener **Docker Desktop** instalado y abierto en segundo plano (verifica que el ícono esté en verde).
2. Tener instalado **VS Code** (recomendado) o cualquier terminal compatible.

---

### Paso 1: Obtener y abrir el proyecto
Tienes dos formas sencillas de preparar el entorno para la evaluación:

* **Opción A (Recomendada - Vía VS Code):**
  1. Descarga el repositorio como archivo ZIP desde GitHub y descomprímelo en tu computadora.
  2. Abre **VS Code**, haz clic en **File > Open Folder...** y selecciona la carpeta descomprimida del proyecto.
  3. Abre la terminal integrada de VS Code haciendo clic arriba en **Terminal > New Terminal**. (Esto te ubicará automáticamente en la ruta de acceso correcta del proyecto).

* **Opción B (Vía Terminal de comandos tradicional):**
  1. Abre tu terminal (PowerShell o CMD).
  2. Navega hasta la carpeta raíz del proyecto usando el comando `cd`:
     ```powershell
     cd ruta/a/la/carpeta/del/proyecto
     ```

---

### Pasos para el despliegue 
#### 1. Levantar el clúster de Cassandra
Si quieres empezar desde cero (esto **borra los datos** que tengas cargados), ejecuta primero:
  ```powershell
docker compose down -v
  ```
Inicia el contenedor de la base de datos:
  ```powershell
docker compose up -d
  ```
Verifica que el contenedor `aquasense` esté en ejecución. Cassandra tarda de 1 a 3 minutos en arrancar, así que repite este comando hasta que el estado diga `(healthy)`:
  ```powershell
docker ps
  ```
*(Mientras arranca se ve `(health: starting)`. Cuando termina se ve `Up ... (healthy)`).*

Confirma que el nodo está en buen estado:
  ```powershell
docker exec aquasense nodetool status
  ```
*(Al inicio de la línea del nodo debe aparecer `UN`, que significa Up/Normal. Si aparece `DN` o el comando da error de conexión, Cassandra aún está arrancando: espera un minuto y repite).*

#### 2. Cargar el esquema de la base de datos
El esquema ya queda montado dentro del contenedor, así que no hace falta copiarlo. Este comando crea el *keyspace* y las 8 tablas:
  ```powershell
docker exec -it aquasense cqlsh -f /schema.cql
  ```
*(Deben listarse las 8 tablas).*
#### 3. Ingerir el volumen de datos (1,000,000 de registros)
*Este comando levanta un contenedor temporal de Python aislado en Docker, instala el conector oficial y procesa los datos de forma automática:*

- **Si estás en Windows (PowerShell):**
  ```powershell
  docker run --rm --network container:aquasense -v "${PWD}:/app" -w /app python:3.10 sh -c "pip install cassandra-driver && python data/load_data.py"
  ```
- **Si estás en Mac o Linux:**
  ```bash
  docker run --rm --network container:aquasense -v "$(pwd):/app" -w /app python:3.10 sh -c "pip install cassandra-driver && python data/load_data.py"
  ```

#### 4. Validar la carga de datos
Para verificar ante los evaluadores que el millón de registros se cargó con éxito en Cassandra:
```powershell
pip install cassandra-driver
python performance/verificar_carga.py
```
### Consultas de Demostración y Pruebas

Para mostrar el funcionamiento del modelo de datos, puedes ejecutar directamente las siguientes consultas en la terminal:

- **1. Conteo total de registros (demuestra la ingesta masiva):**
  ```powershell
  python performance/verificar_carga.py
  ```

- **2. Ver la estructura completa de tablas creadas en el keyspace:**
  ```powershell
  docker exec -it aquasense cqlsh -e "USE aquasense; DESCRIBE TABLES;"
  ```

- **3. Ver las primeras 5 lecturas generales de la base de datos:**
  ```powershell
  docker exec -it aquasense cqlsh -e "USE aquasense; SELECT * FROM lecturas_por_sensor LIMIT 5;"
  ```

- **4. Consultar lecturas de un sensor en un día (con clave de partición completa):**
  ```powershell
  docker exec -it aquasense cqlsh -e "SELECT sensor_id, bucket FROM aquasense.lecturas_por_sensor LIMIT 1;"
  docker exec -it aquasense cqlsh -e "SELECT fecha_hora, caudal, presion, temperatura FROM aquasense.lecturas_por_sensor WHERE sensor_id = 1224cbd2-b7c4-43ee-9b1f-c6d1388149dc AND bucket = '2026-01-01' LIMIT 10;"
  ```

- **5. Ver la última lectura registrada de cada sensor:**
  ```powershell
  docker exec -it aquasense cqlsh -e "USE aquasense; SELECT * FROM ultima_lectura_sensor LIMIT 5;"
  ```

- **6. Consultar los resúmenes diarios por zona:**
  ```powershell
  docker exec -it aquasense cqlsh -e "USE aquasense; SELECT * FROM resumen_diario_zona LIMIT 5;"
  ```
