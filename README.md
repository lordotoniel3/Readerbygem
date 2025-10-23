# Bloocheck Backend 🚀

**Bloocheck** es un servicio backend diseñado para procesar y analizar documentos mediante técnicas de extracción y validación de datos. Proporciona una API RESTful que permite integrar fácilmente su funcionalidad en aplicaciones frontend.

---

## Características 

- Extracción de datos clave de ditintos tipos de documentos (CVs, Facturas, Extractos bacnarios, etc..)
- Validación y normalización de formatos.
- API RESTful con autenticación mediante tokens.
- Arquitectura modular y escalable para adaptarse a distintos flujos de trabajo.

---

## Requisitos

- Python 3.10+
- Cuenta de servicio en Google Cloud con permisos para:
  - PostgreSQL
  - Cloud Storage
  - Vertex AI
- PostgreSQL 13+
- Dependencias listadas en `requirements.txt`

---

## Configuración Local 💻

Sigue estos pasos para ejecutar Bloocheck localmente:

### 1. Variables de Entorno (`.env`)

Crea un archivo `.env` en la raíz del proyecto con el siguiente contenido:

```ini
# Configuración de Bloocheck
# Google Cloud

PROJECT_ID=id-del-proyecto
SERVICE_ACCOUNT_FILE=ubicacion-service-account

# PostgreSQL
POSTGRES_HOST=host-postgresql
POSTGRES_PORT=puerto-postgresql
POSTGRES_DB=nombre-db-postgresql
POSTGRES_USER=nombre-usuario-postgresql
POSTGRES_PASSWORD=contraseña-postgresql
PROCESSED_BUCKET_NAME=nombre-bucket-documentos-procesados
IN_PROCESS_BUCKET_NAME=nombre-bucket-documentos-en-proceso
SOURCE_BUCKET_NAME=nombre-bucket-documentos-fuente
```

### 2. Cuenta de Servicio

Descarga el archivo JSON de la cuenta de servicio desde la consola de GCP y guárdalo como `./service-account.json`.

### 3. Ejecución

Instala las dependencias y arranca el servidor:

```bash
python -m venv venv
source venv/bin/activate  # En Linux/Mac
venv\Scripts\activate     # En Windows
pip install uv
uv sync
uv run fastapi run app/main.py
pip install -r requirements.txt
python main.py
```


Si se desplego correctamente debera ver {"status":"El servicio está en ejecución"} en `http://0.0.0.0:8000`
La documentacion estará disponible en `http://0.0.0.0:8000/docs`.

---

## Despliegue en Google Cloud Platform (GCP) ☁️

### 1. Secretos y Variables de Entorno

- **Service Account**: Sube el archivo JSON de la cuenta de servicio a Secret Manager.
- **Variables de entorno**: Configúralas en Cloud Run.

### 2. Buckets de Cloud Storage

Crear 3 buckets para documentos fuente, en proceso y procesados.

### 3. Configuración de Postgresql

En la DB de PostgreSQL ejecuta las queries del archivo 'db_schema.sql' para crear las tablas necesarias para almacenamiento de información, logs y buscador vectorial.

---

## Estructura del Proyecto 🗂️

```
bloocheck-back/
├── db_utils.py            # Funciones de base de datos
├── analyzers/analyzer.py  # Análisis de documentos
├── main.py                # Punto de entrada y servidor API
├── Dockerfile             # Imagen Docker del proyecto
├── requirements.txt       # Requerimientos de Python
├── prompts/               # Plantillas de IA
├── samples/               # Archivos de prueba
├── db_schema.sql          # Queries SQL para generar tablas de almacenamiento
├── .env                   # Variables de entorno (solo local)
├── service-account.json   # Credenciales (solo local)
```

