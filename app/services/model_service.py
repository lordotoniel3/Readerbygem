import logging
import uuid
from typing import Annotated, Dict, Any, Optional, Callable
from fastapi import Depends
from google import genai
from google.genai.types import Part
import re

from analyzers.analyzer import DOCUMENT_CONFIG, CATEGORY_PROMPT_PATH
from app.dependencies import Settings, get_settings
from app.dto.process import DocType
from app.utils.json_parse import gemini_json_parse

logger = logging.getLogger("uvicorn.error")
GEMINI_MODEL = "gemini-2.0-flash"


def get_model_service(config: Annotated[Settings, Depends(get_settings)]):
    return ModelService(
        config=config
    )


class ModelService:
    """
    This service unifies the genai calls across the internal processing,
    and the API sync request, some more generic methods, like direct prompting
    and some specific like infer doctype
    """

    def __init__(self, config: Settings):
        self.__genai_client = genai.Client(vertexai=True, project=config.project_id, location=config.region)

    async def extract_info(self, file: Part, doc_type: DocType):
        config: Dict[str, Any] = DOCUMENT_CONFIG[doc_type]
        try:
            with open(config['prompt_path'], "r", encoding='utf-8') as f:
                extraction_prompt: str = f.read()

        except FileNotFoundError as e:
            logger.error(f"No se encontró el archivo de prompt: {e}", exc_info=True)
            raise RuntimeError
        except Exception as e:
            logger.error(f"Error leyendo archivos de prompt: {e}", exc_info=True)
            raise RuntimeError

        mres = await self.__genai_client.aio.models.generate_content(model=GEMINI_MODEL,
                                                                     contents=[file, extraction_prompt])
        score_info = await self.get_score_info(doc_type, gemini_json_parse(mres.text))
        
        return { "data" : gemini_json_parse(mres.text),
                 "score_info": score_info 
                }

    async def get_doc_type(self, file: Part):
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
        response = await self.__genai_client.aio.models.generate_content(model=GEMINI_MODEL, contents=[file, prompt])
        determined_category = response.text.strip()
        for valid_cat in known_categories:
            if determined_category.upper() == valid_cat.upper():
                return valid_cat

        return "uncategorized"

    async def make_prompt(self, prompt: str):
        return await self.__genai_client.aio.models.generate_content(model=GEMINI_MODEL, contents=[prompt])


    async def make_prompt_with_file(self, prompt: str, file: Part):
        return await self.__genai_client.aio.models.generate_content(model=GEMINI_MODEL, contents=[file, prompt])

    async def get_score_info(self,doc_type: DocType, df_json_text ):

        config: Dict[str, Any] = DOCUMENT_CONFIG[doc_type]
        try:
            with open(config['audit_path'], "r", encoding='utf-8') as f:
                audit_prompt_template: str = f.read()
        except FileNotFoundError as e:
            logger.error(f"No se encontró el archivo de prompt: {e}", exc_info=True)
            raise RuntimeError
        except Exception as e:
            logger.error(f"Error leyendo archivos de prompt: {e}", exc_info=True)
            raise RuntimeError
        
        full_audit_prompt: str = audit_prompt_template.format(df_data=df_json_text)
        audit_response_text: str = (await self.__genai_client.aio.models.generate_content(model=GEMINI_MODEL, contents=[full_audit_prompt])).text
        audit_result: Dict[str, Any] = gemini_json_parse(audit_response_text)
        validation_data = {}
        scores = audit_result.get("scores", {})
        explanation_text = audit_result.get("explicacion", "")

        for field, score in scores.items():
            if isinstance(score, (int, float)) and score < 1:
                field_msg = None
                match = re.search(rf"({field}[^.,;\n]*)", explanation_text, re.IGNORECASE)
                if match:
                    field_msg = match.group(1).strip()
                validation_data[field] = field_msg 

        score_calculator_func: Optional[Callable[[Dict[str, float]], float]] = config['score_calculator']
        scores_dict: Dict[str, float] = audit_result.get('scores', {})

        result = score_calculator_func(scores_dict) if score_calculator_func else None
        if isinstance(result, tuple) and len(result) == 2:
            score_val, score_expl = result
        else:
            score_val = result
            score_expl = ''

        df_audit_result = {}
        df_audit_result['score'] = [score_val]  
        df_audit_result['score_explaining'] = audit_result.get('explicacion', '') + " | " + score_expl
        df_audit_result['check_fields'] = validation_data # viene un json con dos campos, los campos con error, y la descripcion de los errores
        
        return df_audit_result