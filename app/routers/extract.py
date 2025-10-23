from typing import Annotated

#import magic
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.params import Depends
from google.genai.types import Part

from app.dto.process import DocType
from app.services.model_service import ModelService, get_model_service

extract_info_router = APIRouter(prefix="/api/v1")
MAX_FILE_SIZE = 10 * 1024 * 1024

@extract_info_router.post("/extract")
async def extract_info_from_doc(
        model_service: Annotated[ModelService, Depends(get_model_service)],
        file: UploadFile = File(media_type="application/pdf"),
        doc_type: DocType = Form(...)
):
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail=f"File too large, MAX: {MAX_FILE_SIZE/100000} MB")

    buffer = await file.read()
    if not magic.from_buffer(buffer, mime=True) == 'application/pdf':
        raise HTTPException(status_code=422, detail=f"File must be a valid pdf")

    part = Part.from_bytes(data=buffer, mime_type="application/pdf")
    checked_doc_type = await model_service.get_doc_type(part)
    if checked_doc_type != doc_type:
        raise HTTPException(status_code=400, detail=f"File was not recognized as a {doc_type} instead it is recognized as {checked_doc_type}")

    extracted = await model_service.extract_info(part, doc_type)
    # Publish to rabbit if flag
    return extracted
