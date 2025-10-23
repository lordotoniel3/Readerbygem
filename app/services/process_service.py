import asyncio
import logging
import re
from typing import Annotated, Dict, Any, Callable, Optional
from datetime import datetime, date

import pandas as pd
from fastapi import Depends
from google.cloud.storage import Blob
from google.genai.errors import ClientError

from analyzers.analyzer import DOCUMENT_CONFIG, CATEGORY_PROMPT_PATH
from app.dto.entity.bill import Bill
from app.dto.entity.buy_order import BuyOrder
from app.dto.entity.cc import CC
from app.dto.entity.cv import CV
from app.dto.entity.email import Email
from app.dto.entity.existence import Existence
from app.dto.entity.extract import Extract
from app.dto.entity.pay import Payment
from app.dto.entity.rub import RUB
from app.dto.entity.rut import RUT
from app.dto.entity_store import EntityStore
from app.dto.entity.balance import Balance
from app.dto.log import Log, ValidationError
from app.dto.process import ProcessRequest
from app.services.balance_reprocess_service import BalanceReprocessService
from app.services.extract_reprocess_service import ExtractReprocessService
from app.services.bucket_service import BucketService, get_bucket_service
from app.services.model_service import get_model_service, ModelService
from app.utils.file import PartFile
from app.utils.get_blob_file import get_file_from_storage
from app.utils.json_parse import gemini_json_parse
from app.services.analytical_helper_service import AnalyticalHelperService
import json

logger = logging.getLogger("uvicorn.error")
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MBs


def get_process_service(bucket_service: Annotated[BucketService, Depends(get_bucket_service)],
                        model_service: Annotated[ModelService, Depends(get_model_service)]):
    return ProcessService(
        bucket_service=bucket_service,
        model_service=model_service
    )

class ProcessService:

    def __init__(self, bucket_service: BucketService, model_service: ModelService):
        self.bucket_service = bucket_service
        self.model_service = model_service
    
    async def process_files(self, request: ProcessRequest):
        logger.info(f"Starting batch processing with id: {request.load_id}")
        await self._preprocess(request.gs_path)
        logger.info("Preprocessing ended, starting batch processing")
        blobs = self.bucket_service.list_files(request.gs_path)
        if len(blobs) == 0:
            logger.warning("WARNING, the bucket is empty or no compatible files were found")
            return

        # INIT SEMAPHORES HERE: asyncio semaphores are not thread safe and the fastapi thread should not create them
        self.download_semaphore = asyncio.Semaphore(50)
        self.processing_semaphore = asyncio.Semaphore(50)

        tasks = []
        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(self.__process_file(request, blob)) for blob in blobs]
        logger.info(f"Processing files ended")
        
        return [t.result() for t in tasks]

    async def _preprocess(self, gs_path: str):
        """
        Preprocess the batch of files, this method is in charge of preparing the gs path so
        the all the files there could be processed in batch, right now the only preprocess
        to be done is to flatten the zips
        """
        await self.bucket_service.flatten_bucket(gs_path)

    async def __process_file(self, request: ProcessRequest, blob: Blob):
        """
        Process a single file manages the possible exceptions, etc
        """
        
        # Initialize log variable to avoid UnboundLocalError in exception handler
        log = None

        try:
            if blob.size > MAX_FILE_SIZE:
                logger.warning(f"Blob exceed max file size {blob.name}, ignoring")
                raise

            # GCP bucket api is blocking, avoid blocking the main thread
            async with self.download_semaphore:
                try:
                    file = await asyncio.get_running_loop().run_in_executor(None, get_file_from_storage, blob)
                except ValueError as ve:
                    logger.warning(f"File validation error for {blob.name}: {ve}")
                    raise ve
                except Exception as e:
                    logger.error(f"Error downloading/processing file {blob.name}: {e}")
                    raise e

            # gemini and the db provide async interfaces but limit them to avoid killing the main thread
            async with self.processing_semaphore:
                try:
                    gemini_doc_type = await self.__get_doc_type(file, request.doc_type)
                except ClientError as ce:
                    logger.error(f"Gemini API error for file {file.original_filename}: {ce.status_code} {ce.message}")
                    logger.error(f"File details - name: {file.original_filename}, size: {blob.size}, mime_type: {file.part.mime_type}")
                    raise ce
                except Exception as e:
                    logger.error(f"Unexpected error during document type detection for {file.original_filename}: {e}")
                    raise e
                is_invalid = gemini_doc_type == "uncategorized"
                if is_invalid:
                    # In the original code an invalid doc stopped the execution but a mismatched one didn't
                    logger.warning(f"The file {file.original_filename} could not be categorized, ignoring...")
                    raise
                temp_gemini_doc_type = gemini_doc_type
                if (temp_gemini_doc_type[:5]== 'Saldo'): #To parse saldo fiduciario and saldo bancario
                    temp_gemini_doc_type = 'Saldo'
                log = Log(
                    name=file.original_filename,
                    status="PROCESSING",
                    # processing pass to be an inner state here, due to the front not being able to check the 'loading status in this state'
                    format=request.doc_type,
                    parent_file=file.parent_file,
                    identified_format=temp_gemini_doc_type,
                    invalid_format=is_invalid
                )
                entity, validation = await self.__analyze_document(file=file, doc_type=gemini_doc_type)
                log.status = "PROCESSED"
                return EntityStore(load_id=request.load_id, entity=entity, validation=ValidationError(check_fields=validation) if validation else None, log=log)
        except Exception as e:
            logger.exception(f"Error processing file {blob.name}")
            # Create log entry if it doesn't exist yet
            if log is None:
                log = Log(
                    name=blob.name,
                    status="ERROR",
                    format=request.doc_type,
                    parent_file=getattr(file, 'parent_file', None) if 'file' in locals() else None,
                    identified_format=None,
                    invalid_format=True
                )
            else:
                log.status = "ERROR"
            return EntityStore(load_id=request.load_id, log=log)


    async def __analyze_document(self, file: PartFile, doc_type: str):

        """
        original code by Andres from its last commit, moved here so it can use DI,
        removed SA need and other improvements, base data analysis untouched
        """
        config: Dict[str, Any] = DOCUMENT_CONFIG[doc_type]
        try:
            with open(config['prompt_path'], "r", encoding='utf-8') as f:
                extraction_prompt: str = f.read()
            with open(config['audit_path'], "r", encoding='utf-8') as f:
                audit_prompt_template: str = f.read()

        except FileNotFoundError as e:
            logger.error(f"No se encontró el archivo de prompt: {e}", exc_info=True)
            raise RuntimeError
        except Exception as e:
            logger.error(f"Error leyendo archivos de prompt: {e}", exc_info=True)
            raise RuntimeError

        extracted_data_df = await self.__extract_info_from_doc(file=file, prompt=extraction_prompt, doc_type=doc_type)
        if extracted_data_df is None or extracted_data_df.empty:
            logger.warning(
                f"No se pudieron extraer datos o el DataFrame está vacío para {file.original_filename}.")
            raise RuntimeError("")
        try:
            df_json_text: str = extracted_data_df.to_json(orient='records', indent=2, date_format="iso", force_ascii=False)
            full_audit_prompt: str = audit_prompt_template.format(df_data=df_json_text)
            audit_response_text = await self.model_service.make_prompt(full_audit_prompt)
            audit_result: Dict[str, Any] = gemini_json_parse(audit_response_text.text)
            # Construir diccionario de validación con campos que tengan score < 1
            validation_data = {}
            scores = audit_result.get("scores", {})
            explanation_text = audit_result.get("explicacion", "")

            for field, score in scores.items():
                if isinstance(score, (int, float)) and score < 1:
                    field_msg = None
                    match = re.search(rf"({field}[^.,;\n]*)", explanation_text, re.IGNORECASE)
                    if match:
                        field_msg = match.group(1).strip()
                    validation_data[field] = field_msg  # None si no se encontró explicación
    

            score_calculator_func: Optional[Callable[[Dict[str, float]], float]] = config['score_calculator']
            scores_dict: Dict[str, float] = audit_result.get('scores', {})

            result = score_calculator_func(scores_dict)
        except:
            logger.info("JSON muy largo para auditar, asignando score 70")
            result: tuple = 0.7, "JSON muy largo para auditar, score asignado automaticamente"
            validation_data = None
        if isinstance(result, tuple) and len(result) == 2:
            score_val, score_expl = result
        else:
            score_val = result
            score_expl = ''

        extracted_data_df['score'] = [score_val]  
        try:
            extracted_data_df['score_explaining'] = audit_result.get('explicacion', '') + " | " + score_expl
        except:
            extracted_data_df['score_explaining'] = score_expl

        
        for col in config['base_columns']:
            if col not in extracted_data_df.columns:
                extracted_data_df[col] = None

        # non data columns
        extracted_data_df['doc_type'] = doc_type

        if (doc_type == 'Saldo_Fiduciario') or (doc_type == 'Saldo_Bancario'):
            extracted_data_df['doc_type'] = 'Saldo'
            doc_type='Saldo'

        extracted_data_df['filename'] = file.path
        extracted_data_df['parent_file'] = file.parent_file

        d = extracted_data_df.iloc[0].to_dict()
        def _coerce_date_min(s):
            if isinstance(s, date):
                return s
            if not isinstance(s, str) or not s.strip():
                return None
            s = s.strip()
            s = re.sub(r"[./]", "-", s)  
            for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%m-%d-%Y"):  
                try:
                    return datetime.strptime(s, fmt).date()
                except ValueError:
                    pass
            return None  
        if isinstance(d.get("trusts"), list):
            for t in d["trusts"]:
                if "trustDate" in t:
                    t["trustDate"] = _coerce_date_min(t.get("trustDate"))
                if isinstance(t.get("movements"), list):
                    for m in t["movements"]:
                        if "date" in m:
                            m["date"] = _coerce_date_min(m.get("date"))
        preview = json.dumps(d, ensure_ascii=False, indent=2, default=str)
        print(f"[Entity payload -> {doc_type}]")
        print(preview[:2000] + ("… [truncated]" if len(preview) > 2000 else ""))
        entity = None
        match doc_type:
            case 'CV':
                entity = CV(**d)
            case 'Factura':
                entity = Bill(**d)
            case 'Extracto':
                entity = Extract(**d)
            case 'Compra':
                entity = BuyOrder(**d)
            case 'RUT':
                entity = RUT(**d)
            case 'RUB':
                entity = RUB(**d)
            case 'CC':
                entity = CC(**d)
            case 'Existencia':
                entity = Existence(**d)
            case 'Pago':
                entity = Payment(**d)
            case 'Email':
                entity = Email(**d)
            case 'Saldo':
                # If balanceDate is empty, try to extract it from the filename using analytical_helper_service
                if not d.get("balanceDate"):
                    helper = AnalyticalHelperService()
                    extracted_date = helper.extract_date_from_filename(file)
                    if extracted_date:
                        d["balanceDate"] = extracted_date
                entity = Balance(**d)
        return entity, validation_data if validation_data else None

    async def __get_doc_type(self, file: PartFile, doc_type: str):
        """
        Original code by Andres on its last commit
        """
        known_categories = DOCUMENT_CONFIG.keys()
        try:
            with open(CATEGORY_PROMPT_PATH, "r", encoding="utf-8") as f:
                prompt_template = f.read()
        except FileNotFoundError:
            logger.exception(f"No se encontró el archivo de prompt de categorías en {CATEGORY_PROMPT_PATH}")

        category_descriptions = "\n".join(
            f"- {cat}: {conf.get('description', '—sin descripción—')}"
            for cat, conf in DOCUMENT_CONFIG.items()
        )
        prompt = prompt_template.format(category_descriptions=category_descriptions)
        response = await self.model_service.make_prompt_with_file(prompt, file.part)
        determined_category = response.text.strip()
        for valid_cat in known_categories:
            if determined_category.upper() == valid_cat.upper():
                if valid_cat != doc_type and doc_type != "batch-indefinido":
                    if not (valid_cat[:5]== doc_type): #Avoids warning with Saldos
                        logger.warning(f'Categoría inconsistente: Gemini={valid_cat} vs Request={doc_type}')
                return valid_cat

        return "uncategorized"


    async def __extract_info_from_doc(self, file: PartFile, prompt: str, doc_type: str) -> pd.DataFrame:
        """
        Based on the original code by Andres
        """
        mres = await self.model_service.make_prompt_with_file(prompt, file.part)
        res = mres.text
        try:
            extracted_data = gemini_json_parse(res)
        except ValueError:
            logger.info("Iniciando metodo de recuperacion de datos extraidos de saldo")
            reprocess=None
            match doc_type:
                case 'Saldo_Fiduciario':
                    reprocess_service = BalanceReprocessService(self.model_service, file)
                    reprocess=6
                case 'Extracto':
                    reprocess_service = ExtractReprocessService(self.model_service, file)
                    reprocess=4
            if not reprocess:
                raise ValueError(f"Unable to extract data from {doc_type} document")
            extracted_data = None
            for i in range(reprocess): #Try n times to reprocess the balance
                logger.info(f"Reintento {i+1} para reprocesar el {doc_type}")
                reprocess_res = await reprocess_service.reprocess(res)
                res = reprocess_res
                try:
                    
                    if reprocess_res is not None:
                        
                        extracted_data = gemini_json_parse(reprocess_res)
                        break
                except ValueError:
                    logger.info(f"Reintento {i+1} fallido para reprocesar el {doc_type}")

            # If all reprocessing attempts failed, raise an error
            if extracted_data is None:
                logger.error(f"Failed to reprocess {doc_type} after 3 attempts")
                raise ValueError(f"Unable to extract data from {doc_type} document after reprocessing attempts")
        # Si es un diccionario simple y se espera una lista (ej. para normalizar a una fila)
        if isinstance(extracted_data, dict) and not any(isinstance(v, list) for v in extracted_data.values()):
            df = pd.json_normalize([extracted_data])  # Envolver en lista si es un solo objeto JSON
        else:
            df = pd.json_normalize(extracted_data)
        return df
   