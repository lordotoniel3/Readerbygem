# main.py
import os
import logging
from datetime import timedelta, datetime
from io import BytesIO
from zipfile import ZipFile
from threading import Thread
from typing import List, Dict, Any, Tuple, Optional

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from google.cloud import storage
from google.cloud import logging as cloud_logging
from google.oauth2 import service_account
from google.api_core.retry import Retry
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

from analyzers.analyzer import analyze_document, upload_data, get_document_category
from db_utils import (
    POSTGRES_CONFIG,
    update_row_by_id,
    insert_rows,
    insert_log_to_postgres,
    update_log_in_postgres
)

load_dotenv()

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": [
            "http://localhost:3000",
            "http://34.23.132.0:8080",
            "https://bloocheck-679213647489.us-east1.run.app"
        ],
        "allow_headers": ["Content-Type", "Authorization"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "supports_credentials": True
    }
})

# Configuración del cliente de logging de Google Cloud
logging_client: cloud_logging.Client = cloud_logging.Client()
logging_client.setup_logging()

""" ----------------- Variables Globales y Constantes ----------------- """
BATCH_SIZE: int = 3000 # Cantidad máxima de archivos a procesar por lote
WORKER_NUM: int = 10  # Número de hilos para procesamiento principal
INNER_WORKER_NUM: int = 7  # Número de hilos para procesamiento de archivos dentro de ZIPs
PROJECT_ID: Optional[str] = os.getenv("PROJECT_ID") # ID del proyecto de Google Cloud
LOCATION: str = 'us'  # Ubicación para servicios de Google Cloud
DESTINATION_FOLDER: str = '/tmp'  # Carpeta temporal para descargar archivos
PROCESSED_BUCKET_NAME: Optional[str] = os.getenv("PROCESSED_BUCKET_NAME") # Nombre del bucket donde se subirán los archivos procesados
IN_PROCESS_BUCKET_NAME: Optional[str] = os.getenv("IN_PROCESS_BUCKET_NAME") # Nombre del bucket donde se subirán los archivos en proceso
SOURCE_BUCKET_NAME: Optional[str] = os.getenv("SOURCE_BUCKET_NAME") # Nombre del bucket de origen donde se encuentran los archivos a procesar
SERVICE_ACCOUNT_FILE: Optional[str] = os.getenv("SERVICE_ACCOUNT_FILE") # Ruta al archivo de credenciales del servicio de Google Cloud

# Credenciales para Google Cloud Storage
credentials: service_account.Credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
storage_client: storage.Client = storage.Client(credentials=credentials)

# Política de reintentos para operaciones de Google Cloud
retry_policy: Retry = Retry(
        initial=1.0,         # Retraso inicial en segundos
        maximum=60.0,        # Retraso máximo entre reintentos
        multiplier=2.0,      # Factor de retroceso exponencial
        deadline=120.0,      # Tiempo total de reintentos
        )

""" ----------------- Funciones de Google Cloud Storage (Bucket) ----------------- """
def upload_to_bucket(bucket_name: str, local_file_path: str, destination_blob_name: str) -> None:
    """Sube un archivo a un bucket de Google Cloud Storage."""
    if not storage_client:
        logging.error("Cliente de Storage no inicializado. No se puede subir al bucket.")
        return
    try:
        bucket: storage.Bucket = storage_client.bucket(bucket_name)
        blob: storage.Blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(local_file_path, retry=retry_policy)
    except Exception as e:
        logging.error(f"Error subiendo {local_file_path} a bucket {bucket_name}: {e}", exc_info=True)
        raise

def delete_from_bucket(bucket_name: str, blob_name: str) -> None:
    """Elimina un blob de un bucket de Google Cloud Storage."""
    if not storage_client:
        logging.error("Cliente de Storage no inicializado. No se puede eliminar del bucket.")
        return
    try:
        bucket: storage.Bucket = storage_client.bucket(bucket_name)
        blob: storage.Blob = bucket.blob(blob_name)
        blob.delete(retry=retry_policy)
    except Exception as e:
        logging.error(f"Error eliminando {blob_name} del bucket {bucket_name}: {e}", exc_info=True)
        raise

def extract_zip_in_bucket(source_bucket_name_str: str, zip_file_name: str, target_bucket_name_str: str) -> Tuple[List[str], bool]:
    """
    Extrae SOLO archivos PDF/imágenes (ignora otros).
    Elimina el ZIP original tras extraer.
    Retorna lista de archivos extraídos o error.
    """
    if not storage_client:
        logging.error("Cliente de Storage no inicializado. No se puede extraer el ZIP.")
        return [], True # Devuelve lista vacía y error=True

    extracted_files: List[str] = []
    error_occurred: bool = False
    try:
        source_bucket: storage.Bucket = storage_client.bucket(source_bucket_name_str)
        target_bucket: storage.Bucket = storage_client.bucket(target_bucket_name_str)
        blob: storage.Blob = source_bucket.blob(zip_file_name)

        zip_bytes: bytes = blob.download_as_bytes(retry=retry_policy)
        with ZipFile(BytesIO(zip_bytes)) as zip_ref:
            for file_name_in_zip in zip_ref.namelist():
                # Asegurarse de que el nombre del archivo no contenga rutas problemáticas (ej. ../)
                safe_file_name: str = os.path.basename(file_name_in_zip)
                if not safe_file_name: # Si el nombre es vacío o solo una ruta (ej. carpeta/)
                    logging.warning(f"Ignorando entrada de ZIP inválida o vacía: '{file_name_in_zip}'")
                    continue

                if safe_file_name.lower().endswith(('.pdf', '.jpg', '.jpeg', '.png')):
                    # Usar safe_file_name para el blob de destino para evitar problemas de ruta
                    extracted_blob: storage.Blob = target_bucket.blob(safe_file_name)
                    extracted_blob.upload_from_string(zip_ref.read(file_name_in_zip))
                    extracted_files.append(safe_file_name)
                    logging.info(f"Archivo '{safe_file_name}' extraído y subido a {target_bucket_name_str}")
                else:
                    logging.warning(f'Ignorando archivo no soportado dentro del ZIP: {safe_file_name}')

        delete_from_bucket(source_bucket_name_str, zip_file_name)
        logging.info(f"Archivo ZIP {zip_file_name} procesado y eliminado de {source_bucket_name_str}")

    except Exception as e:
        logging.error(f"Error extrayendo ZIP {zip_file_name} de {source_bucket_name_str} a {target_bucket_name_str}: {e}", exc_info=True)
        error_occurred = True
    return extracted_files, error_occurred

""" ----------------- Funciones de Procesamiento de Documentos ----------------- """
def process_document(bucket_name: str, file_name: str, now: datetime, file_id: str, content_id: str, doc_type: str, load_id: int, parent_zip_name: Optional[str] = None ) -> None:
    """Descarga, analiza un documento y sube los resultados y el archivo procesado."""
    if not storage_client:
        logging.error("Cliente de Storage no inicializado. No se puede procesar el documento.")
        return

    base_file_name: str = os.path.basename(file_name)
    local_file_path: str = os.path.join(DESTINATION_FOLDER, base_file_name)
    os.makedirs(DESTINATION_FOLDER, exist_ok=True)

    try:
        bucket: storage.Bucket = storage_client.bucket(bucket_name)
        blob: storage.Blob = bucket.blob(file_name)
        blob.download_to_filename(local_file_path, retry=retry_policy)

        timestamp: str = now.strftime('%Y%m%d%H%M%S')
        gemini_doc_type = get_document_category(local_file_path, doc_type)
        
        is_invalid = (gemini_doc_type != doc_type and doc_type != "batch-indefinido")
        doc_status = 'processing'
        if gemini_doc_type == "uncategorized":
            is_invalid = True
            doc_status = "error_categorizacion"
        
        log_record = {
                'id_contenido': int(content_id),
                'id_carga': load_id,
                'name': os.path.basename(file_name),
                'date': now,
                'status': doc_status,
                'format': doc_type,
                'parent_file': parent_zip_name,
                'identified_format': gemini_doc_type,
                'invalid_format': is_invalid,
                'is_duplicate': False
            }
        try:
            insert_log_to_postgres([log_record])
            logging.info(f"Log insertado para {base_file_name} con id_contenido {content_id}.")
        except Exception as log_e:
            logging.error(f"Error insertando log para {base_file_name}: {log_e}", exc_info=True)
            raise
        if gemini_doc_type == "uncategorized":
            os.remove(local_file_path)
            delete_from_bucket(bucket_name, file_name)
            return
        
        doc_type = gemini_doc_type
        destination_blob_name: str = f"{doc_type}/{os.path.splitext(base_file_name)[0]}_{timestamp}{os.path.splitext(base_file_name)[1]}"
        
        # Extracción de datos usando el módulo analizador
        dataframe: Optional[pd.DataFrame] = analyze_document(local_file_path, int(file_id), int(content_id), doc_type) # file_id y content_id se esperan como int

        # Subida de datos y archivo procesado
        if PROCESSED_BUCKET_NAME:
            upload_to_bucket(PROCESSED_BUCKET_NAME, local_file_path, destination_blob_name)
        else:
            logging.warning("PROCESSED_BUCKET_NAME no está configurado. No se subirá el archivo procesado.")

        delete_from_bucket(bucket_name, file_name) # Eliminar el archivo original del bucket de proceso
        os.remove(local_file_path)

        if dataframe is not None and not dataframe.empty:
            dataframe["filename"] = destination_blob_name # Asignar el nombre del archivo en el bucket de procesados
            try:
                upload_data(dataframe, base_file_name, doc_type)
            except Exception as e:
                logging.error(f"Error al cargar datos a PostgreSQL para {base_file_name}: {e}", exc_info=True)
        elif dataframe is None:
             logging.warning(f"El análisis del documento {base_file_name} no produjo DataFrame (retornó None).")
        else:
            logging.warning(f"No se encontraron datos válidos en {base_file_name} para cargar.")

    except Exception as e:
        logging.error(f"Error procesando el documento {file_name}: {e}", exc_info=True)
        if os.path.exists(local_file_path):
            try:
                os.remove(local_file_path)
                logging.info(f"Archivo local {local_file_path} eliminado después de un error.")
            except OSError as oe:
                logging.error(f"Error eliminando archivo local {local_file_path} después de un error: {oe}")
        raise

@app.route('/process', methods=['POST'])
def process_file_endpoint() -> Tuple[Response, int]:
    """Endpoint Flask para iniciar el procesamiento de archivos desde el front."""
    if not request.is_json:
        logging.error("Error: El contenido de la solicitud no es JSON")
        return jsonify({"error": "Content-Type debe ser application/json"}), 400
    try:
        data: Dict[str, Any] = request.get_json()
    except Exception as e:
        logging.error(f"Error parseando JSON de la solicitud: {e}", exc_info=True)
        return jsonify({"error": "JSON de la solicitud inválido"}), 400

    names: Optional[List[str]] = data.get('name')
    doc_type: Optional[str] = data.get('type') 
    load_id: Optional[str] = data.get('id') 

    if not load_id:
        logging.error("El campo 'id' (id de carga) es requerido en la solicitud.")
        return jsonify({"error": "El campo 'id' (id de carga) es requerido"}), 400
    if not names or not isinstance(names, list):
        logging.error("El campo 'name' (lista de nombres de archivo) es requerido o no es una lista.")
        return jsonify({"error": "El campo 'name' (lista de nombres de archivo) es requerido"}), 400
    if not doc_type:
        logging.error("El campo 'type' (tipo de documento) es requerido en la solicitud.")
        return jsonify({"error": "El campo 'type' (tipo de documento) es requerido"}), 400
    
    allowed_doc_types: List[str] = ["Factura", "CV", "CC", "Compra", "Extracto", "RUB", "RUT", "Existencia","Saldo"]
    if doc_type not in allowed_doc_types:
        logging.error(f"El tipo de documento '{doc_type}' no es válido.")
        return jsonify({"error": f"Tipo de archivo inválido: {doc_type}. Permitidos: {', '.join(allowed_doc_types)}"}), 400


    if SOURCE_BUCKET_NAME:
        thread = Thread(target=background_process_files, args=(SOURCE_BUCKET_NAME, names, doc_type, str(load_id)))
        thread.start()
        return jsonify({
            "status": "Aceptado",
            "message": f"Procesando {len(names)} archivo(s) de tipo {doc_type}",
            "load_id": load_id
        }), 202
    else:
        logging.error("SOURCE_BUCKET_NAME no está configurado. No se puede iniciar el procesamiento.")
        return jsonify({"error": "Configuración del servidor incompleta para procesar archivos."}), 500

@app.route('/process-batch', methods=['POST'])
def process_files_batch_endpoint():
    """Endpoint Flask para iniciar el procesamiento de archivos en batch desde un scheduler."""
    try:
        data: Dict[str, Any] = request.get_json()
    except Exception as e:
        logging.error(f"Error parseando JSON de la solicitud: {e}", exc_info=True)
        return jsonify({"error": "JSON de la solicitud inválido"}), 400
    
    SOURCE: Optional[str] = data.get('bucket')

    bucket = storage_client.bucket(SOURCE)
    blobs = bucket.list_blobs() 
    names = []
    for blob in blobs:
        names.append(blob.name)
        if len(names) >= BATCH_SIZE:
            break
    if not names:
        logging.info("No hay archivos para procesar en el bucket.")
        return jsonify({"message": "No hay archivos a procesar"}), 200
    load_id = '999' + ''.join(random.choices('0123456789', k=10))
    doc_type = "batch-indefinido"

    thread = Thread(target=background_process_files, args=(SOURCE, names, doc_type, str(load_id)))
    thread.start()
    return jsonify({
        "status": "Aceptado",
        "message": f"Procesando {len(names)} archivo(s) de tipo {doc_type}",
        "load_id": load_id
    }), 202 

def background_process_files(bucket_name: str, names: List[str], doc_type: str, load_id: str) -> None:
    """Procesa una lista de archivos en segundo plano utilizando un ThreadPoolExecutor."""
    logging.info(f"Procesamiento en segundo plano iniciado para id de carga {load_id}. Analizando archivos de tipo '{doc_type}'.")
    processing_start_time: datetime = datetime.now() # UTC-5 para Colombi

    # Limitar el número de workers concurrentes
    max_workers: int = min(WORKER_NUM, len(names))
    logging.info('=' * 150)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures: Dict[Any, Tuple[str, str]] = {} # Future -> (nombre_archivo, file_id_str)

        for file_index, name in enumerate(names):
            # Generar un file_id único para cada archivo dentro de la carga
            file_id_str: str = f"{load_id}{file_index}"
            logging.info(f"- PROCESANDO ARCHIVO: {name} (Tipo: {doc_type}) con file_id: {file_id_str}")

            dataload_record: Dict[str, Any] = {
                'id_archivo': int(file_id_str), # Convertir a int para la BD
                'id_carga': int(load_id),     # Convertir a int para la BD
                'name': name,
                'date': processing_start_time.isoformat(),
                'status': 'processing',
                'format': doc_type
            }
            try:
                insert_rows('DataLoad', [dataload_record])
            except Exception as e:
                logging.error(f"Error insertando registro en DataLoad para {name} (file_id: {file_id_str}): {e}", exc_info=True)
                continue

            # Enviar la tarea de procesamiento al executor
            future = executor.submit(
                process_single_file,
                bucket_name, name, processing_start_time, file_id_str, load_id, doc_type
            )
            futures[future] = (name, file_id_str)

        # Procesar los resultados a medida que se completan
        for future in as_completed(futures):
            name, file_id_str = futures[future]
            try:
                future.result() # Obtener el resultado o levantar la excepción si la tarea falló
                logging.info(f"Procesamiento del archivo {name} (file_id: {file_id_str}) completado exitosamente.")
            except Exception as e:
                logging.error(f"Error al procesar el archivo {name} (file_id: {file_id_str}) en el hilo: {e}", exc_info=True)
                try:
                    update_row_by_id('DataLoad', int(file_id_str), {"status": "error"})
                    logging.info(f"Archivo {name} (file_id: {file_id_str}) actualizado en DataLoad con estado 'error' debido a fallo en el hilo.")
                except Exception as db_e:
                    logging.error(f"Error actualizando DataLoad para {name} (file_id: {file_id_str}) tras fallo en hilo: {db_e}", exc_info=True)
    logging.info(f"Todos los archivos para la carga {load_id} (tipo: {doc_type}) han sido enviados a procesamiento.")


def process_single_file(bucket_name: str, name: str, now: datetime, file_id_str: str, load_id_str: str, doc_type: str) -> None:
    """Procesa un solo archivo, manejando ZIPs y archivos individuales."""
    file_id_int: int = int(file_id_str)
    load_id_int: int = int(load_id_str)

    try:
        if name.lower().endswith('.zip'):
            # El nombre del archivo en el bucket el tipo como prefijo de carpeta si viene del front
            zip_full_name_in_bucket: str = f'{doc_type}/{name}' if not name.startswith(f"{doc_type}/") and doc_type != "batch-indefinido" else name
            
            if not IN_PROCESS_BUCKET_NAME or not bucket_name:
                logging.error("Nombres de bucket de origen o en proceso no configurados. Saltando extracción de ZIP.")
                update_row_by_id('DataLoad', file_id_int, {"status": "error_config"})
                return

            extracted_files, error_extracting = extract_zip_in_bucket(bucket_name, zip_full_name_in_bucket, IN_PROCESS_BUCKET_NAME)

            if error_extracting or not extracted_files:
                logging.error(f'Error extrayendo ZIP {zip_full_name_in_bucket} o ZIP vacío. Marcando como error.')
                update_row_by_id('DataLoad', file_id_int, {"status": "error"})
                return

            logging.info(f"ZIP {name} extraído. Archivos encontrados: {extracted_files}")

            max_inner_workers: int = min(INNER_WORKER_NUM, len(extracted_files))
            inner_futures: Dict[Any, int] = {} # Future -> content_id_int
            zip_processing_failed: bool = False

            with ThreadPoolExecutor(max_workers=max_inner_workers) as inner_executor:
                for content_index, extracted_file_name in enumerate(extracted_files):
                    content_id_int: int = int(f"{file_id_str}{content_index}") # ID único para el contenido del ZIP

                    # Enviar la tarea de procesamiento del archivo individual
                    fut = inner_executor.submit(
                        process_and_log_single_file,
                        IN_PROCESS_BUCKET_NAME, # Bucket donde están los archivos extraídos
                        extracted_file_name,    # Nombre del archivo en ese bucket
                        now,                    # Timestamp de inicio del proceso padre
                        str(file_id_int),       # ID del archivo ZIP padre (como string)
                        str(content_id_int),    # ID del contenido específico (como string)
                        doc_type,               # Tipo de documento del archivo extraído    
                        name,                   # Nombre del archivo ZIP padre
                        load_id_int             # ID de carga (load_id)
                    )
                    inner_futures[fut] = content_id_int

                # Recolectar resultados
                for fut in as_completed(inner_futures):
                    content_id_processed = inner_futures[fut]
                    try:
                        fut.result()
                        logging.info(f"Archivo con id_contenido {content_id_processed} (del ZIP {name}) procesado exitosamente.")
                    except Exception as e_file:
                        logging.error(f"Archivo con id_contenido {content_id_processed} (del ZIP {name}) falló en su procesamiento: {e_file}", exc_info=True)
                        zip_processing_failed = True

            # Actualizar estado del ZIP en DataLoad
            final_zip_status: str = "error" if zip_processing_failed else "processed"
            update_row_by_id('DataLoad', file_id_int, {"status": final_zip_status})
            logging.info(f"Archivo ZIP {name} (file_id: {file_id_int}) actualizado en DataLoad con estado '{final_zip_status}'.")

        elif name.lower().endswith((".pdf", ".jpg", ".jpeg", ".png")):
            content_id_for_file: int = file_id_int
            
            # Mover del bucket fuente al bucket en proceso
            file_name_in_source_bucket: str = f'{doc_type}/{name}' if not name.startswith(f"{doc_type}/") and doc_type != "batch-indefinido" else name
            
            if not IN_PROCESS_BUCKET_NAME or not bucket_name or not storage_client:
                logging.error("Nombres de bucket o cliente de storage no configurados. Saltando copia de archivo.")
                update_row_by_id('DataLoad', file_id_int, {"status": "error_config"})
                return

            try:
                source_bucket_obj: storage.Bucket = storage_client.bucket(bucket_name)
                target_bucket_obj: storage.Bucket = storage_client.bucket(IN_PROCESS_BUCKET_NAME)
                source_blob: storage.Blob = source_bucket_obj.blob(file_name_in_source_bucket)
                
                target_blob_name = name
                source_bucket_obj.copy_blob(source_blob, target_bucket_obj, target_blob_name, retry=retry_policy)
                delete_from_bucket(bucket_name, file_name_in_source_bucket)
            except Exception as move_e:
                logging.error(f"Error moviendo archivo {file_name_in_source_bucket} a {IN_PROCESS_BUCKET_NAME}: {move_e}", exc_info=True)
                update_row_by_id('DataLoad', file_id_int, {"status": "error_moving_file"})
                update_log_in_postgres(content_id_for_file, "error")
                return

            file_processing_failed: bool = False
            try:
                process_and_log_single_file(
                    IN_PROCESS_BUCKET_NAME,     # Bucket donde reside el archivo ahora
                    target_blob_name,           # Nombre del archivo en ese bucket
                    now,                        # Timestamp de inicio del proceso padre
                    str(file_id_int),           # ID del "archivo" padre (él mismo en este caso)
                    str(content_id_for_file),   # ID del contenido (él mismo)
                    doc_type,                   # Tipo de documento del archivo
                    None,                       # No hay ZIP padre
                    load_id_int                 # ID de carga 
                )
            except Exception as e_file_single:
                logging.error(f"Error procesando archivo individual {name}: {e_file_single}", exc_info=True)
                file_processing_failed = True
            
            final_file_status: str = "error" if file_processing_failed else "processed"
            update_row_by_id('DataLoad', file_id_int, {"status": final_file_status})
            logging.info(f"Archivo {name} (file_id: {file_id_int}) actualizado en DataLoad con estado '{final_file_status}'.")

        else:
            logging.error(f'Archivo con extensión no válida o no soportada: {name}. Se esperaba alguna de estas extensiones: ".pdf", ".jpg", ".jpeg", ".png", ".zip".')
            update_row_by_id('DataLoad', file_id_int, {"status": "error_extension"})

    except Exception as e_outer:
        logging.error(f"Error general procesando el archivo {name} (file_id: {file_id_str}): {e_outer}", exc_info=True)
        try:
            update_row_by_id('DataLoad', file_id_int, {"status": "error_processing"})
            logging.info(f"Archivo {name} (file_id: {file_id_int}) actualizado en DataLoad con estado 'error_processing' debido a una excepción general.")
        except Exception as db_e_outer:
            logging.error(f"Error actualizando DataLoad para {name} (file_id: {file_id_int}) tras excepción general: {db_e_outer}", exc_info=True)
        raise # Re-lanzar la excepción para que sea capturada por el ThreadPoolExecutor y marcada como fallida

def process_and_log_single_file(
    bucket_name: str, # Nombre del bucket donde se encuentra el archivo
    file_name: str, # Nombre del archivo en el bucket_name
    now: datetime, # Timestamp de inicio del proceso padre
    parent_file_id_str: str, # ID del archivo ZIP padre, o el ID del archivo si no está en un ZIP
    content_id_str: str,     # ID único del contenido
    doc_type: str, # Tipo de documento del archivo
    parent_zip_name: Optional[str], # Nombre del archivo ZIP padre, si existe
    load_id: int # ID de carga
) -> None:
    """
    Ayudante para procesar un solo archivo y actualizar su log en PostgreSQL.
    Esta función es llamada tanto para archivos individuales como para archivos extraídos de un ZIP.
    """
    content_id_int: int = int(content_id_str)

    try:
        process_document(
            bucket_name, file_name, now, 
            parent_file_id_str, content_id_str, doc_type,
            load_id, parent_zip_name 
        )
        update_log_in_postgres(content_id_int, "processed")
        logging.info(f"Archivo {file_name} (content_id: {content_id_int}) procesado y log actualizado a 'processed'.")
    except Exception as e:
        logging.error(f"Error procesando archivo {file_name} (content_id: {content_id_int}): {e}", exc_info=True) 
        update_log_in_postgres(content_id_int, "error")
        raise


@app.route('/status', methods=['GET'])
def status() -> Tuple[Response, int]:
    """Endpoint Flask para verificar el estado del servicio."""
    return jsonify({"status": "El servicio está en ejecución"}), 200

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
