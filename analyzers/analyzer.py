# analyzers/analyzer.py

"""
TODO this is a legacy file, the last work of Andres
remove when migrating all, contains errors due to old imports
"""


from google.oauth2 import service_account
import base64
import json
import re
import os
import logging
from typing import Dict, Any, List, Optional, Callable, Tuple

import pandas as pd

# ====================== CONFIGURACIONES DE DOCUMENTOS ====================== #
# Define la estructura de configuración para cada tipo de documento.
# Esto centraliza la información específica del documento como rutas de prompts,
# nombres de funciones de cálculo de score, columnas base y tablas relacionadas.
CATEGORY_PROMPT_PATH = "prompts/prompt_categorias.txt"
DOCUMENT_CONFIG: Dict[str, Dict[str, Any]] = {
    "CV": {
        "description": "Hoja de vida o currículum vitae que contiene información personal, académica y laboral de una persona.",
        "prompt_path": "prompts/cv_prompt.txt", 
        "audit_path": "prompts/cv_audit.txt",   
        "score_calculator": "calculate_cv_score",
        "base_table_name": "hoja_de_vida",
        "base_columns": [ 
            "id_contenido", "id_archivo", "nombre_completo", "tipo_documento",
            "documento_identidad", "email", "telefono", "descripcion_perfil",
            "direccion_completa", "score", "explicacion_score", "filename", "is_duplicate"
        ],
        "related_tables": { 
            "idioma": ["id_contenido", "nombre", "nivel", "examen"],
            "experiencia": ["id_contenido", "puesto", "empresa", "fecha_inicio", "fecha_fin", "total_meses", "descripcion"],
            "educacion": ["id_contenido", "titulo", "institucion", "fecha_inicio", "fecha_fin", "semestres_cursados", "tipo"],
            "habilidad": ["id_contenido", "nombre_habilidad"]
        },
        "duplicate_check_columns": ["full_name", "email"],
    },
    "Factura": {
        "description": "Documento emitido por el proveedor tras la entrega de bienes o servicios, con detalle de ítems, montos a pagar, impuestos y condiciones de pago.",
        "prompt_path": "prompts/bill_prompt.txt",
        "audit_path": "prompts/bill_audit.txt",
        "score_calculator": "calculate_bill_score",
        "base_table_name": "facturas_invoice",
        "base_columns": [
            "id_contenido", "id_archivo", "invoice_id", "nit", "invoice_date",
            "supplier_name", "total_amount", "total_tax_amount", "net_amount",
            "score", "explicacion_score", "filename", "is_duplicate"
        ],
        "duplicate_check_columns": ["nit", "invoice_id"],
        "related_tables": {
            "facturas_product": ["id_contenido", "product_id", "description", "quantity", "unit_price", "amount"]
        }
    },
    "CC": {
        "description": "Cédula de ciudadanía que contiene información personal de un ciudadano.",
        "prompt_path": "prompts/cc_prompt.txt",
        "audit_path": "prompts/cc_audit.txt",
        "score_calculator": "calculate_cc_score",
        "base_table_name": "cc",
        "duplicate_check_columns": ["document_type", "number", "issue_date"],
        "base_columns": [
            "id_contenido", "id_archivo", "tipo_documento", "numero_cedula",
            "apellidos", "nombres", "fecha_nacimiento", "lugar_nacimiento",
            "fecha_expedicion", "lugar_expedicion", "estatura",
            "grupo_sanguineo", "sexo", "score", "explicacion_score", "filename", "is_duplicate"
        ],
        "related_tables": {} 
    },
    "Compra": {
        "description": "Orden de compra generada por el comprador para solicitar formalmente productos o servicios, incluye especificaciones, cantidades, precios acordados y plazos de entrega.",
        "prompt_path": "prompts/compra_prompt.txt",
        "audit_path": "prompts/compra_audit.txt",
        "score_calculator": "calculate_compra_score",
        "base_table_name": "orden_compra",
        "duplicate_check_columns": ["numero_orden", "fecha_emision", "nombre_proveedor", "nombre_comprador"],
        "base_columns": [
            "id_contenido", "id_archivo", "numero_orden", "fecha_emision", "moneda",
            "nombre_comprador", "identificacion_comprador", "direccion_comprador",
            "telefono_comprador", "email_comprador", "nombre_proveedor",
            "identificacion_proveedor", "direccion_proveedor", "telefono_proveedor",
            "email_proveedor", "subtotal", "impuestos", "descuentos", "total",
            "forma_pago", "plazo_entrega", "lugar_entrega", "observaciones",
            "score", "explicacion_score", "filename", "is_duplicate"
        ],
        "related_tables": {
            "orden_compra_items": ["id_contenido", "descripcion", "cantidad", "unidad_medida", "precio_unitario", "subtotal"]
        }
    },
    "Extracto": {
        "description": "Extracto bancario o fiduciario que resume las transacciones y saldo de una cuenta en un periodo específico.",
        "prompt_path": "prompts/extractos_prompt.txt",
        "audit_path": "prompts/extractos_audit.txt",
        "score_calculator": "calculate_extracto_score",
        "base_table_name": "extracto_bancario",
        "duplicate_check_columns": ["statement_number", "issue_date_statement", "bank_name", "account_number"],
        "base_columns": [
            "id_contenido", "id_archivo", "nombre_banco", "direccion_banco", "telefono_banco",
            "nombre_titular", "numero_cliente", "direccion_titular", "tipo_cuenta", "numero_cuenta",
            "moneda", "fecha_inicial_periodo", "fecha_final_periodo", "saldo_anterior", "saldo_actual",
            "total_depositos", "total_retiros", "total_comisiones", "tasa_interes",
            "intereses_generados", "retenciones", "fecha_corte_siguiente", "fecha_emision_extracto",
            "numero_extracto", "score", "explicacion_score", "filename", "is_duplicate"
        ],
        "related_tables": {
            "extracto_bancario_movimientos": [
                "id_contenido", "fecha", "descripcion", "referencia", "valor", "tipo", "saldo_posterior"
            ],
            "extracto_bancario_encargos": [
                "id", "extract_id", "numero_encargo", "fecha_encargo", "valor_encargo", "concepto"
            ]
        }
    },
    "RUB": {
        "description": "Registro Único de Beneficiarios (RUB) que contiene información sobre entidades y sus beneficiarios.",
        "prompt_path": "prompts/rub_prompt.txt",
        "audit_path": "prompts/rub_audit.txt",
        "score_calculator": "calculate_rub_score",
        "base_table_name": "rub",
        "duplicate_check_columns": ["nit", "numero_formulario", "fecha_reporte"],
        "base_columns": [
            "id_contenido", "id_archivo", "numero_formulario", "fecha_reporte", "tipo_reporte",
            "razon_social", "nit", "dv", "tipo_entidad", "direccion", "municipio", "departamento",
            "telefono", "email", "nombre_representante_legal", "apellido_representante_legal",
            "tipo_documento_representante_legal", "numero_documento_representante_legal",
            "telefono_representante_legal", "email_representante_legal",
            "declarante", "cargo", "fecha_declaracion", "score", "explicacion_score", "filename", "is_duplicate"
        ],
        "related_tables": {
            "rub_beneficiarios": [
                "id_contenido", "tipo_persona", "nombre", "apellido", "razon_social",
                "tipo_documento", "numero_documento", "dv", "pais_documento", "fecha_nacimiento",
                "pais_nacimiento", "nacionalidad", "pais_residencia", "direccion", "municipio",
                "departamento", "telefono", "email", "tipo_beneficiario", "criterio_determinacion",
                "porcentaje_participacion", "fecha_inicio", "fecha_fin"
            ]
        }
    },
    "RUT": {
        "description": "Registro Único Tributario (RUT) que contiene información sobre contribuyentes y sus actividades económicas.",
        "prompt_path": "prompts/rut_prompt.txt",
        "audit_path": "prompts/rut_audit.txt",
        "score_calculator": "calculate_rut_score",
        "base_table_name": "rut",
        "duplicate_check_columns": ["form_number", "issue_date", "document_type", "document_number"],
        "base_columns": [
            "id_contenido", "id_archivo", "numero_formulario", "fecha_expedicion",
            "fecha_ultima_actualizacion", "tipo_documento", "numero_documento", "dv",
            "razon_social", "primer_apellido", "primer_nombre", "fecha_nacimiento",
            "pais_nacimiento", "departamento_nacimiento", "ciudad_nacimiento", "direccion",
            "pais", "departamento", "ciudad", "email", "telefono_fijo", "telefono_movil",
            "notificacion_electronica", "tipo_contribuyente", "regimen",
            "fecha_inicio_actividades", "estado_rut",
            "score", "explicacion_score", "filename", "is_duplicate"
        ],
        "related_tables": {
            "rut_actividades": ["id_contenido", "codigo_ciiu", "descripcion",
                               "actividad_principal", "fecha_inicio"],
            "rut_responsabilidades": ["id_contenido", "codigo", "descripcion",
                                     "fecha_inicio", "fecha_fin"],
            "rut_establecimientos": ["id_contenido", "nombre", "direccion", "ciudad",
                                    "departamento", "actividad_principal", "fecha_apertura"],
            "rut_representante": ["id_contenido", "tipo_documento", "numero_documento",
                                 "nombre_completo", "cargo"]
        }
    },
    "Existencia": {
        "description": "Certificado de Existencia y Representación Legal que contiene información detallada sobre empresas registradas en la Cámara de Comercio.",
        "prompt_path": "prompts/existencia_prompt.txt",
        "audit_path": "prompts/existencia_audit.txt",
        "score_calculator": "calculate_existencia_score",
        "base_table_name": "existencia",
        "duplicate_check_columns": ["expedition_date", "nit", "social"],
        "base_columns": [
            "id_contenido", "id_archivo", "fecha_expedicion", "codigo_verificacion",
            "numero_recibo", "razon_social", "sigla", "nit", "organizacion_juridica",
            "categoria", "matricula_mercantil", "fecha_matricula","domicilio", "direccion_principal", "telefono_comercial",
            "email_comercial", "sitio_web", "fecha_constitucion", "escritura_constitucion",
            "notaria_constitucion", "fecha_vigencia", "objeto_social", "codigo_ciiu",
            "descripcion_ciiu", "sector_economico", "activo_total", "tamano_empresa",
            "ingresos_actividad_ordinaria", "tipo_capital", "valor_capital",
            "facultades_representante", "limitaciones_representante", "revisor_fiscal",
            "estado_matricula", "score", "explicacion_score", "filename", "is_duplicate"
        ],
        "related_tables": {
            "existencia_socios": [
                "id_contenido", "nombre", "tipo_identificacion", "numero_identificacion",
                "numero_cuotas_acciones", "valor_participacion", "porcentaje_participacion"
            ],
            "existencia_representantes_legales": [
                "id_contenido", "cargo", "nombre", "tipo_identificacion",
                "numero_identificacion", "es_suplente", "fecha_nombramiento",
                "documento_nombramiento"
            ],
            "existencia_establecimientos": [
                "id_contenido", "nombre", "matricula", "fecha_matricula", "direccion",
                "ciudad", "telefono_1", "telefono_2", "email", "actividad_principal",
                "descripcion_actividad", "valor_establecimiento"
            ]
        }
    },
    "Pago": {
    "description": "Documento que reporta información de pagos realizados, generalmente anexado o incluido en el cuerpo de un correo.",
    "prompt_path": "prompts/pago_prompt.txt",
    "audit_path": "prompts/pago_audit.txt",
    "score_calculator": "calculate_pago_score",
    "base_table_name": "pago",
    "duplicate_check_columns": ["fecha_pago", "valor_pago", "referencia_pago"],
    "base_columns": [
        "id_contenido", "id_archivo", "fecha_pago", "valor_pago", "referencia_pago",
        "nombre_receptor", "tipo_documento", "numero_documento", "banco_origen", "cuenta_origen",
        "banco_destino", "cuenta_destino", "medio_pago", "concepto", 
        "score", "explicacion_score", "filename", "is_duplicate"
    ],
    "related_tables": {
        "pago_detalles": [
            "id_contenido", "descripcion_detalle", "valor_detalle"
            ]
        }
    },
    "Email": {
        "description": "Correo electrónico con asunto, cuerpo, fecha y adjuntos",
        "prompt_path": "prompts/email_prompt.txt",
        "audit_path": "prompts/email_audit.txt",
        "score_calculator": "calculate_email_score",
        "base_table_name": "email",
        "base_columns": [
            "id_contenido", "email", "subject", "body", "date", "attachment_count",
            "score", "explicacion_score", "filename", "is_duplicate"
        ],
        "related_tables": {},
        "duplicate_check_columns": ["email", "subject"],  # <-- Usa 'subject', no 'asunto'
    },

"Saldo_Fiduciario": {
    "description": "Saldo fiduciario a la fecha indicada de una compañia en diferentes encargos agrupado por proyectos y fases",
    "prompt_path": "prompts/fiduciary_balance_prompt.txt",
    "audit_path": "prompts/fiduciary_balance_audit.txt",
    "score_calculator": "calculate_fiduciary_balance_score",
    "base_table_name": "saldo_fiduciario",
    "base_columns": [
        "id_contenido", "id_archivo", "bank_name", "bank_nit", "account_holder", 
        "currency", "balance_date", "total_orders", "total_orders_exchange", 
        "total_orders_available", "total_accounts", "total_accounts_exchange", 
        "total_accounts_available", "score", "explicacion_score", "filename", "is_duplicate"
    ],
    "related_tables": {
        "saldo_fiduciario_detail": [
            "id_contenido", "account_number", "account_type", "total_balance", 
            "exchange_balance", "available_balance", "participation", "fund", "date"
        ]
    },
    "duplicate_check_columns": ["balance_date", "bank_name", "account_holder"]
}



}

#
# ====================== FUNCIONES UTILITARIAS ====================== #
def process_file_with_vlm(file_path: str, prompt: str, vlm, doc_type: str) -> Optional[pd.DataFrame]:
    """ Procesa un archivo PDF o imagen utilizando un LLM para extraer datos estructurados y retorna como DF. """
    try:
        encoded_doc: Dict[str, str] = encode_file_to_base64_parts(file_path)
        response_text: str = vlm.generate_content([encoded_doc, prompt]).text
        extracted_data: Any = parse_json_from_text(response_text)
        if not extracted_data:
            logging.warning(f"No se pudo extraer JSON válido de la respuesta del VLM para {doc_type} {file_path}.")
            return pd.DataFrame()
    
        # Si es un diccionario simple y se espera una lista (ej. para normalizar a una fila)
        if isinstance(extracted_data, dict) and not any(isinstance(v, list) for v in extracted_data.values()):
             df = pd.json_normalize([extracted_data]) # Envolver en lista si es un solo objeto JSON
        else:
             df = pd.json_normalize(extracted_data)
        logging.info(f"Datos extraídos exitosamente para {doc_type} {os.path.basename(file_path)}. {len(df)} fila(s) generadas.")
        return df
            
    except FileNotFoundError:
        logging.error(f"Archivo no encontrado: {file_path}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f'Error procesando {doc_type} {file_path} con VLM: {e}', exc_info=True)
        if 'response_text' in locals() and response_text:
            logging.error(f"Respuesta del VLM (primeros 500 chars): {response_text[:500]}")
        return None

def generate_text_response_from_vlm(prompt: str, vlm) -> str:
    """
    Genera una respuesta de texto desde el VLM solo con un prompt (sin documento adjunto).
    """
    try:
        return vlm.generate_content(prompt).text
    except Exception as e:
        logging.error(f"Error generando respuesta de texto desde VLM: {e}", exc_info=True)
        raise # Re-lanzar para que el llamador maneje el error

def encode_file_to_base64_parts(file_path: str) -> Dict[str, str]:
    """ Codifica un archivo (PDF o imagen) a una parte base64 para la API de Gemini. """
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        mime = "application/pdf"
    elif ext in (".jpg", ".jpeg"):
        mime = "image/jpeg"
    elif ext == ".png":
        mime = "image/png"
    else:
        raise ValueError(f"Unsupported file type for VLM: {ext}")

    with open(file_path, "rb") as f:
        data_b64 = base64.b64encode(f.read()).decode("utf-8")
    return {"mime_type": mime, "data": data_b64}

def parse_json_from_text(text_response: str) -> Any:
    """
    Intenta extraer JSON usando:
    1. Bloques ```json ... ```
    2. Bloques ``` ... ```
    3. Busca { o [ como último recurso
    """
    if not text_response:
        logging.warning("Respuesta de texto vacía, no se puede extraer JSON.")
        return None

    # Intentar encontrar bloques de código JSON
    match_json_block = re.search(r'```json\s*(\{.*?\}|\[.*?\])\s*```', text_response, re.DOTALL | re.IGNORECASE)
    if not match_json_block: # Si no hay bloque ```json, buscar bloque ``` genérico
        match_json_block = re.search(r'```\s*(\{.*?\}|\[.*?\])\s*```', text_response, re.DOTALL)

    json_str: Optional[str] = None
    if match_json_block:
        json_str = match_json_block.group(1).strip()
    else:
        # Si no hay bloques ```, intentar asumir que toda la respuesta es JSON (o al menos la parte relevante)
        first_brace = text_response.find('{')
        first_bracket = text_response.find('[')

        start_index = -1
        if first_brace != -1 and first_bracket != -1:
            start_index = min(first_brace, first_bracket)
        elif first_brace != -1:
            start_index = first_brace
        elif first_bracket != -1:
            start_index = first_bracket
        
        if start_index != -1:
            potential_json_str = text_response[start_index:]
            last_brace = potential_json_str.rfind('}')
            last_bracket = potential_json_str.rfind(']')
            end_index = -1
            if last_brace != -1 and last_bracket != -1:
                 end_index = max(last_brace, last_bracket) +1
            elif last_brace != -1:
                 end_index = last_brace +1
            elif last_bracket != -1:
                 end_index = last_bracket +1
            
            if end_index != -1:
                 json_str = potential_json_str[:end_index].strip()
            else:
                 json_str = potential_json_str.strip() # Tomar todo desde el inicio del JSON
        else:
            logging.warning("No se encontraron delimitadores JSON (```) ni caracteres de inicio JSON ({, [) en la respuesta.")
            # Como último recurso, intentar parsear toda la respuesta si parece JSON.
            if text_response.strip().startswith(("{", "[")):
                json_str = text_response.strip()
            else:
                logging.error(f"La respuesta no parece ser JSON y no tiene delimitadores. Respuesta: {text_response[:200]}")
                raise json.JSONDecodeError("No se pudo identificar un string JSON en la respuesta.", text_response, 0)


    if not json_str:
        logging.error(f"No se pudo extraer un string JSON de la respuesta. Respuesta: {text_response[:200]}")
        raise json.JSONDecodeError("String JSON extraído está vacío o nulo.", text_response, 0)
        
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logging.error(f"Error decodificando JSON extraído: '{json_str[:1000]}...'. Error: {e}", exc_info=True)
        raise # Re-lanzar para que el llamador sepa que el parseo falló

def expand_list_of_dicts(
    df: pd.DataFrame,
    list_column_name: str,
    target_columns: List[str],
    id_column_name: str = "id_contenido"
) -> Optional[pd.DataFrame]:
    """
    Expande una columna de un DataFrame que contiene listas de diccionarios.
    Cada diccionario en la lista se convierte en una nueva fila, asociada
    con el `id_column_name` de la fila original.
    """
    if list_column_name not in df.columns:
        logging.warning(f"La columna '{list_column_name}' no existe en el DataFrame.")
        return None
    if id_column_name not in df.columns:
        logging.error(f"La columna ID '{id_column_name}' no existe en el DataFrame para expansión.")
        return None

    all_expanded_items: List[Dict[str, Any]] = []

    # Iterar sobre cada fila del DataFrame original
    for _, row in df.iterrows():
        items_list: Any = row[list_column_name]
        current_id: Any = row[id_column_name]

        if isinstance(items_list, list):
            for item_dict in items_list:
                if isinstance(item_dict, dict):
                    # Crear una copia para no modificar el original y añadir el ID
                    expanded_item = item_dict.copy()
                    expanded_item[id_column_name] = current_id
                    all_expanded_items.append(expanded_item)
                else:
                    logging.warning(f"Item en '{list_column_name}' no es un diccionario para ID {current_id}: {type(item_dict)}")
        elif items_list is not None and not pd.isna(items_list):
            logging.warning(f"Contenido de '{list_column_name}' no es una lista para ID {current_id}: {type(items_list)}. Valor: {str(items_list)[:100]}")


    if not all_expanded_items:
        logging.info(f"No hay items para expandir en la columna '{list_column_name}'.")
        return pd.DataFrame(columns=target_columns) # Devolver DF vacío con columnas esperadas

    # Convertir la lista de diccionarios expandidos a un DataFrame
    expanded_df = pd.DataFrame(all_expanded_items)

    # Asegurar que todas las `target_columns` existan, rellenando con None si es necesario
    final_df_columns: Dict[str, pd.Series] = {}
    for col in target_columns:
        if col in expanded_df.columns:
            final_df_columns[col] = expanded_df[col]
        else:
            # Si una columna objetivo no está en los datos expandidos, añadirla con Nones/NaNs
            final_df_columns[col] = pd.Series([None] * len(expanded_df), name=col, dtype=object)

    final_df = pd.DataFrame(final_df_columns)
    final_df = final_df[target_columns]

    return final_df


# ====================== FUNCIONES DE CÁLCULO DE SCORE ====================== #
# Estas funciones calculan un score ponderado basado en la presencia y calidad
# de ciertos campos extraídos del documento. Los pesos son definidos internamente.
# El input `scores_from_auditor` es un diccionario donde las claves son nombres de campos
# y los valores son scores (ej. 0 o 1, o un float) asignados por el VLM auditor.

def _calculate_weighted_score(scores_from_auditor: Dict[str, float], weights: Dict[str, float]) -> float:
    """ Calculadora de score ponderado genérica. """
    total_score: float = 0.0
    total_weight: float = 0.0

    if not isinstance(scores_from_auditor, dict):
        logging.warning(f"Se esperaba un diccionario para 'scores_from_auditor', se recibió {type(scores_from_auditor)}. Retornando score 0.")
        return 0.0

    # Campos estándar
    for field_name, weight in weights.items():
        score_value = scores_from_auditor.get(field_name, 0.0) # Default a 0 si el campo no fue auditado o no existe
        if not isinstance(score_value, (int, float)):
            logging.warning(f"Valor de score para '{field_name}' no es numérico ({score_value}). Usando 0.")
            score_value = 0.0
        
        total_score += score_value * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0  # Evitar división por cero si no hay pesos o campos

    final_score = total_score / total_weight
    return max(0.0, min(final_score, 1.0))

def calculate_cv_score(scores_from_auditor: Dict[str, float]) -> float:
    """Calcula el score ponderado para documentos CV."""
    weights: Dict[str, float] = {
        "nombre_completo": 2, "contacto_info": 2, "descripcion_perfil": 2, "educacion_list": 2, # 'contacto_info' y 'educacion_list' son ejemplos de campos agrupados
        "tipo_documento": 1, "documento_identidad": 1, "direccion_completa": 1,
        "experiencia_list": 1, "habilidades_list": 1, "idiomas_list": 1 # _list para indicar que vienen de una lista en el JSON
    }
    return _calculate_weighted_score(scores_from_auditor, weights)


def calculate_bill_score(scores_from_auditor: Dict[str, float]) -> float:
    """Calcula el score ponderado para facturas."""
    weights: Dict[str, float] = {
        "nit": 4, "billExpeditionDate": 2, "billExpirationDate": 1,
        "supplierName": 1, "totalAmount": 1, "totalTaxAmount": 1, "netAmount": 1
    }
    return _calculate_weighted_score(scores_from_auditor, weights)


def calculate_cc_score(scores_from_auditor: Dict[str, float]) -> float:
    """Calcula el score ponderado para documentos CC (Cédula de Ciudadanía)."""
    weights: Dict[str, float] = {
        "tipo_documento": 4, "numero_cedula": 4, "apellidos": 3, "nombres": 3,
        "fecha_nacimiento": 3, "lugar_nacimiento": 3, "sexo": 2,
        "fecha_expedicion": 1, "lugar_expedicion": 1, "estatura": 1, "grupo_sanguineo": 1
    }
    return _calculate_weighted_score(scores_from_auditor, weights)


def calculate_compra_score(scores_from_auditor: Dict[str, float]) -> float:
    """Calcula el score ponderado para órdenes de compra."""
    weights: Dict[str, float] = {
        "numero_orden": 4, "fecha_emision": 3, "nombre_comprador": 3,
        "nombre_proveedor": 3, "total": 3, "items_list": 2, # items_list para los productos/servicios
        "moneda": 2, "identificacion_comprador": 2, "identificacion_proveedor": 2,
        "subtotal": 1, "impuestos": 1, "descuentos": 1
    }
    return _calculate_weighted_score(scores_from_auditor, weights)


def calculate_extracto_score(scores_from_auditor: Dict[str, float]) -> float:
    """Calcula el score ponderado para extractos bancarios."""
    weights: Dict[str, float] = {
        "nombre_banco": 4, "nombre_titular": 4, "numero_cuenta": 4,
        "fecha_inicial_periodo": 3, "fecha_final_periodo": 3, "saldo_actual": 3,
        "movimientos_list": 2, "moneda": 2, "tipo_cuenta": 2, # movimientos_list para transacciones
        "saldo_anterior": 2, "total_depositos": 2, "total_retiros": 2,
        "numero_cliente": 1, "total_comisiones": 1, "fecha_emision_extracto": 1
    }
    return _calculate_weighted_score(scores_from_auditor, weights)


def calculate_rub_score(scores_from_auditor: Dict[str, float]) -> float:
    """Calcula el score ponderado para documentos RUB."""
    weights: Dict[str, float] = {
        "razon_social": 4, "nit": 4, "fecha_reporte": 3,
        "nombre_representante_legal": 3, "apellido_representante_legal": 3,
        "tipo_documento_representante_legal": 3, "numero_documento_representante_legal": 3,
        "beneficiarios_list": 3, "dv": 2, "tipo_entidad": 2,
        "direccion": 2,
        "fecha_declaracion": 1, "declarante": 1, "cargo": 1
    }
    return _calculate_weighted_score(scores_from_auditor, weights)


def calculate_rut_score(scores_from_auditor: Dict[str, float]) -> float:
    """Calcula el score ponderado para documentos RUT."""
    weights: Dict[str, float] = {
        "tipo_documento": 4, "numero_documento": 4, "dv": 3,
        "fecha_expedicion": 3, "estado_rut": 3, "actividades_economicas_list": 3,
        "razon_social_o_nombre": 2,
        "direccion": 2, "fecha_inicio_actividades": 2, "responsabilidades_list": 2,
        "representante_legal_info": 2, "regimen": 1, "tipo_contribuyente": 1
    }
    
    return _calculate_weighted_score(scores_from_auditor, weights)

def calculate_existence_score(scores_from_auditor: Dict[str, float]):
    """
    TODO rewrite the function when implemented
    """
    return 0.0

def calculate_pago_score(data: dict) -> tuple[int, str]:
    """
    Calcula el puntaje de calidad del documento de tipo 'Pago'.
    Evalúa la presencia de campos clave y genera un puntaje de 0 a 100,
    junto con una explicación textual del resultado.

    Retorna:
        - score: int (0 a 100)
        - explanation: str
    """
    required_fields = [
        "fecha_pago", "valor_pago", "referencia_pago",
        "nombre_receptor", "tipo_documento", "numero_documento",
        "banco_origen", "cuenta_origen",
        "banco_destino", "cuenta_destino",
        "medio_pago", "concepto"
    ]

    score = 0
    max_score = len(required_fields)
    missing_fields = []

    for field in required_fields:
        if field in data and data[field]:
            score += 1
        else:
            missing_fields.append(field)

    final_score = int((score / max_score) * 100)

    if final_score == 100:
        explanation = "Todos los campos clave del documento de pago están completos."
    else:
        explanation = f"Faltan los siguientes campos: {', '.join(missing_fields)}."

    return final_score, explanation

def email_score_calculator(extracted: dict) -> tuple[float, str]:
    required_fields = ["email", "asunto", "cuerpo", "fecha", "nro_adjuntos"]
    missing = [f for f in required_fields if not extracted.get(f)]
    if missing:
        return 0.0, f"Faltan los siguientes campos: {', '.join(missing)}"
    return 1.0, ""

def calculate_fiduciary_balance_score(extracted: dict) -> tuple[float, str]:
    """
    Calcula el puntaje de calidad del documento de tipo 'Saldo Fiduciario'.
    Evalúa la presencia de campos clave y genera un puntaje de 0 a 100,
    junto con una explicación textual del resultado.

    Retorna:
        - score: float (0 a 100)
        - explanation: str
    """
    required_fields = [
        "bank_name", "balance_date", "total_orders", "total_orders_exchange",
        "total_orders_available", "total_accounts", "total_accounts_exchange",
        "total_accounts_available"
    ]

    score = 0
    max_score = len(required_fields)
    missing_fields = []

    for field in required_fields:
        if field in extracted and extracted[field]:
            score += 1
        else:
            missing_fields.append(field)

    final_score = int((score / max_score) * 100)

    if final_score == 100:
        explanation = "Todos los campos clave del saldo fiduciario están completos."
    else:
        explanation = f"Faltan los siguientes campos: {', '.join(missing_fields)}."

    return final_score, explanation
#Function that is supposed to replace the current one as this one does not need the gemini model
"""
def calculate_balance_score(extracted: dict) -> tuple[float, str]:
    Calculates score and gives a generic explanation

    Args:
        extracted (dict): dictionary with extracted balance

    Returns:
        tuple[float,str]: score out of 100 and a brief explanation
    

    score = 100  # Start with a perfect score
    required_fields = ["bank_name", "balance_date"]  # Fields that should always be present
    description = []  # List to accumulate explanation messages

    try:
        # Check for required fields and penalize if missing
        for required_field in required_fields:
            if not (required_field in extracted and extracted[required_field]):
                score -= 20
                description.append(f"Falta el campo requerido: {required_field}")

        # Get orders and accounts lists from extracted data
        orders = extracted.get("orders", [])
        accounts = extracted.get("accounts", [])

        # Validate that 'orders' is a list
        if not isinstance(orders, list):
            logging.warning("El campo 'orders' no es una lista.")
            orders = []
            score -= 10
            description.append("El campo 'orders' no es una lista válida.")

        # Validate that 'accounts' is a list
        if not isinstance(accounts, list):
            logging.warning("El campo 'accounts' no es una lista.")
            accounts = []
            score -= 10
            description.append("El campo 'accounts' no es una lista válida.")

        # Penalize if both lists are empty
        if len(orders) == 0 and len(accounts) == 0:
            score -= 50
            description.append("No se encontraron órdenes ni cuentas en el balance.")
        else:
            # Check that the sum of balances in the lists matches the reported totals
            try:
                # Sum balances for accounts
                total_balance = sum(float(a.get('total_balance', 0) or 0) for a in accounts)
                exchange_balance = sum(float(a.get('exchange_balance', 0) or 0) for a in accounts)
                available_balance = sum(float(a.get('available_balance', 0) or 0) for a in accounts)
                # Compare with extracted totals, penalize if mismatch
                if abs(total_balance - float(extracted.get("total_accounts", 0) or 0)) > .1:
                    score -= 20
                    description.append("El balance total no coincide con la suma del balance total de las cuentas")
                if abs(exchange_balance - float(extracted.get("total_accounts_exchange", 0) or 0)) > .1:
                    score -= 20
                    description.append("El canje total no coincide con la suma del canje total de las cuentas")
                if abs(available_balance - float(extracted.get("total_accounts_available", 0) or 0)) > .1:
                    score -= 20
                    description.append("El balance disponible no coincide con la suma del balance disponible de las cuentas")
            except Exception as e:
                logging.error(f"Error al verificar totales de cuentas: {e}", exc_info=True)
                score -= 20
                description.append("Error al verificar totales de cuentas.")

            try:
                # Sum balances for orders
                total_balance = sum(float(o.get('total_balance', 0) or 0) for o in orders)
                exchange_balance = sum(float(o.get('exchange_balance', 0) or 0) for o in orders)
                available_balance = sum(float(o.get('available_balance', 0) or 0) for o in orders)
                # Compare with extracted totals, penalize if mismatch
                if abs(total_balance - float(extracted.get("total_orders", 0) or 0)) > .1:
                    score -= 20
                    description.append("El balance total no coincide con la suma del balance total de las órdenes")
                if abs(exchange_balance - float(extracted.get("total_orders_exchange", 0) or 0)) > .1:
                    score -= 20
                    description.append("El canje total no coincide con la suma del canje total de las órdenes")
                if abs(available_balance - float(extracted.get("total_orders_available", 0) or 0)) > .1:
                    score -= 20
                    description.append("El balance disponible no coincide con la suma del balance disponible de las órdenes")
            except Exception as e:
                logging.error(f"Error al verificar totales de órdenes: {e}", exc_info=True)
                score -= 20
                description.append("Error al verificar totales de órdenes.")

    except Exception as e:
        # Catch any unexpected error and penalize score completely
        logging.error(f"Error general en calculate_balance_score: {e}", exc_info=True)
        score = 0
        description.append("Error crítico al calcular el score del balance.")

    # Ensure score is not negative
    if score < 0:
        score = 0
    # If no errors were found, add a default message
    if len(description) == 0:
        description.append("No se encontraron errores")
    return float(score), " ".join(description)

"""

## Added to avoid globals()
DOCUMENT_CONFIG['CV']['score_calculator'] = calculate_cv_score
DOCUMENT_CONFIG['Factura']['score_calculator'] = calculate_bill_score
DOCUMENT_CONFIG['Extracto']['score_calculator'] = calculate_extracto_score
DOCUMENT_CONFIG['Compra']['score_calculator'] = calculate_compra_score
DOCUMENT_CONFIG['RUT']['score_calculator'] = calculate_rut_score
DOCUMENT_CONFIG['RUB']['score_calculator'] = calculate_rub_score
DOCUMENT_CONFIG['CC']['score_calculator'] = calculate_cc_score
DOCUMENT_CONFIG['Existencia']['score_calculator'] = calculate_existence_score
DOCUMENT_CONFIG['Pago']['score_calculator'] = calculate_pago_score
DOCUMENT_CONFIG['Email']['score_calculator'] = email_score_calculator
DOCUMENT_CONFIG['Saldo_Fiduciario']['score_calculator'] = calculate_fiduciary_balance_score