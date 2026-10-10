
# AquaSense CR - Monitoreo de Redes de Agua Potable

**Curso:** XS0131 Gestión de Bases de Datos y Análisis de Información  
**Universidad de Costa Rica - Escuela de Estadística**  
**Modelo NoSQL:** Columnas Anchas (Wide-Column)  
**Tecnología:** Apache Cassandra  

## Integrantes - Grupo 5
* Sandy
* Keylor
* Jimena
* Jefferson
* Estefanía

## Descripción del Proyecto
AquaSense CR es un sistema diseñado para monitorear redes de agua potable mediante sensores de caudal, presión, temperatura y calidad. Este repositorio contiene la implementación de una capa de datos de alta velocidad en **Apache Cassandra** capaz de soportar la ingesta continua de datos de telemetría y consultar eficientemente series de tiempo por sensor y por intervalo.

## Guía de Ejecución Rápida para Evaluación (Sin instalaciones locales)

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
Ejecuta el siguiente comando para iniciar el contenedor de la base de datos:
```powershell
docker compose up -d
```
*(Confirma en la interfaz gráfica de Docker Desktop que el contenedor llamado `aquasense` aparezca activo).*

#### 2. Cargar el esquema de la base de datos
Copia y ejecuta estos dos comandos para copiar y crear el *keyspace* y las tablas automáticamente:
```powershell
docker cp database/schema/schema.cql aquasense:/schema.cql
docker exec -it aquasense cqlsh -f /schema.cql
```

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
docker exec -it aquasense cqlsh -e "USE aquasense; SELECT COUNT(*) FROM lecturas_por_sensor;"
```
*(Debe retornar exactamente un conteo de `1,000,000` registros).*

---

### Consultas de Demostración y Pruebas

Para mostrar el funcionamiento del modelo de datos, puedes ejecutar directamente las siguientes consultas en la terminal:

- **1. Conteo total de registros (demuestra la ingesta masiva):**
  ```powershell
  docker exec -it aquasense cqlsh -e "USE aquasense; SELECT COUNT(*) FROM lecturas_por_sensor;"
  ```

- **2. Ver la estructura completa de tablas creadas en el keyspace:**
  ```powershell
  docker exec -it aquasense cqlsh -e "USE aquasense; DESCRIBE TABLES;"
  ```

- **3. Ver las primeras 5 lecturas generales de la base de datos:**
  ```powershell
  docker exec -it aquasense cqlsh -e "USE aquasense; SELECT * FROM lecturas_por_sensor LIMIT 5;"
  ```

- **4. Consultar lecturas filtradas por un sensor específico (usando UUID y Allow Filtering):**
  ```powershell
  docker exec -it aquasense cqlsh -e "USE aquasense; SELECT * FROM lecturas_por_sensor WHERE sensor_id = 1224cbd2-b7c4-43ee-9b1f-c6d1388149dc LIMIT 5 ALLOW FILTERING;"
  ```

- **5. Ver la última lectura registrada de cada sensor:**
  ```powershell
  docker exec -it aquasense cqlsh -e "USE aquasense; SELECT * FROM ultima_lectura_sensor LIMIT 5;"
  ```

- **6. Consultar los resúmenes diarios por zona:**
  ```powershell
  docker exec -it aquasense cqlsh -e "USE aquasense; SELECT * FROM resumen_diario_zona LIMIT 5;"
  ```
