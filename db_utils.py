# db_utils.py

import os
import logging
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from tenacity import retry, stop_after_attempt, wait_exponential

# Configuración de la conexión a PostgreSQL
POSTGRES_CONFIG: Dict[str, Optional[str]] = {
    'dbname':     os.getenv("POSTGRES_DB"),
    'user':       os.getenv("POSTGRES_USER", "postgres"),
    'password':   os.getenv("POSTGRES_PASSWORD", ""),
    'host':       os.getenv("POSTGRES_HOST", ""),
    'port':       os.getenv("POSTGRES_PORT", "5432"),
}

""" ----------------- Funciones de Base de Datos (PostgreSQL) ----------------- """
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def update_row_by_id(table_name: str, row_id: Any, column_values: Dict[str, Any], column_id_name: str = 'id_archivo') -> None:
    """Actualiza una fila en la base de datos PostgreSQL por su ID."""
    try:
        with psycopg2.connect(**POSTGRES_CONFIG) as conn:
            with conn.cursor() as cur:
                set_clause: str = ", ".join([f"{col} = %s" for col in column_values.keys()])
                values: List[Any] = list(column_values.values())
                values.append(row_id) 

                query: str = f"""
                UPDATE {table_name}
                SET {set_clause}
                WHERE {column_id_name} = %s
                """
                cur.execute(query, values)
                conn.commit()
    except Exception as e:
        logging.error(f"Error actualizando tabla {table_name} en PostgreSQL para ID {row_id}: {e}", exc_info=True)
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def insert_rows(table_name: str, rows: List[Dict[str, Any]]) -> None:
    """Inserta múltiples filas en una tabla de PostgreSQL."""
    if not rows:
        logging.warning(f"No hay filas para insertar en la tabla {table_name}.")
        return
    try:
        with psycopg2.connect(**POSTGRES_CONFIG) as conn:
            with conn.cursor() as cur:
                columns: List[str] = list(rows[0].keys())
                column_names: str = ", ".join(columns)
                query: str = f"""
                    INSERT INTO {table_name} ({column_names})
                    VALUES %s
                """
                values_to_insert: List[Tuple[Any, ...]] = [
                    tuple(row.get(col) for col in columns)
                    for row in rows
                ]
                execute_values(cur, query, values_to_insert)
                conn.commit()
    except Exception as e:
        logging.error(f"Error insertando filas en tabla {table_name} PostgreSQL: {e}", exc_info=True)
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def insert_log_to_postgres(log_rows: List[Dict[str, Any]]) -> None:
    """Inserta entradas de log en la tabla 'logs' de PostgreSQL."""
    if not log_rows:
        logging.warning("No hay filas de log para insertar.")
        return
    try:
        with psycopg2.connect(**POSTGRES_CONFIG) as conn:
            with conn.cursor() as cur:
                query: str = """
                INSERT INTO logs (
                    id_contenido,
                    id_carga,
                    name,
                    date,
                    status,
                    format,
                    parent_file,
                    identified_format,
                    invalid_format,
                    is_duplicate
                ) VALUES %s
                """
                values: List[Tuple[Any, ...]] = [
                    (
                        row.get("id_contenido"),
                        row.get("id_carga"),
                        row.get("name"),
                        row.get("date"),
                        row.get("status"),
                        row.get("format"),
                        row.get("parent_file"),
                        row.get("identified_format"),
                        row.get("invalid_format"),
                        row.get("is_duplicate", False)
                    )
                    for row in log_rows
                ]
                execute_values(cur, query, values)
                conn.commit()
    except Exception as e:
        logging.error(f"Error insertando logs en PostgreSQL: {e}", exc_info=True)
        raise

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def update_log_in_postgres(file_id: int, new_status: str) -> None:
    """Actualiza el estado y la fecha de un registro de log en PostgreSQL."""
    try:
        with psycopg2.connect(**POSTGRES_CONFIG) as conn:
            with conn.cursor() as cur:
                query: str = """
                UPDATE logs
                SET status = %s, date = %s
                WHERE id_contenido = %s
                """
                current_date: datetime = datetime.now()
                cur.execute(query, (new_status, current_date, str(file_id)))
                conn.commit()
                logging.info(f"Log actualizado para id_contenido {file_id} a estado {new_status}")
    except Exception as e:
        logging.error(f"Error actualizando log en PostgreSQL para id_contenido {file_id}: {e}", exc_info=True)
        raise

def _execute_insert(cursor: psycopg2.extensions.cursor, table_name: str, df_table: pd.DataFrame, columns: List[str], filename: str) -> None:
    """Función auxiliar para ejecutar una inserción de datos de un DataFrame en una tabla."""
    if df_table.empty:
        logging.info(f"DataFrame para la tabla {table_name} está vacío. No se insertarán datos.")
        return

    # Filtrar y preparar columnas
    df_to_insert = pd.DataFrame()
    for col in columns:
        df_to_insert[col] = df_table[col] if col in df_table.columns else pd.NA

    # Preparar valores
    values = [
        tuple(None if pd.isna(x) else x for x in row)
        for row in df_to_insert.itertuples(index=False, name=None)
    ]

    if not values:
        logging.info(f"{filename}: No hay valores para insertar en {table_name}.")
        return

    cols_str: str = ', '.join(f'"{c}"' for c in columns)
    query: str = f"INSERT INTO {table_name} ({cols_str}) VALUES %s"
    
    try:
        execute_values(cursor, query, values)
        logging.info(f"{filename}: {len(values)} filas insertadas en {table_name}.")
    except Exception as e:
        logging.error(f"{filename}: Error en execute_values para {table_name}: {e}", exc_info=True)
        raise