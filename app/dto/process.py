import uuid
from typing import Literal

from pydantic import BaseModel, field_validator

DocType = Literal['CV', 'Factura', 'CC', 'Extracto', 'Compra', 'RUB', 'RUT', 'Existencia' ,'Pago', 'Email','Saldo']

class ProcessRequest(BaseModel):
    load_id: uuid.UUID # Process id sent by the broker
    gs_path: str # valid storage path
    doc_type: DocType

    @field_validator('gs_path', mode="after")
    @classmethod
    def validate_gs_path(cls, v: str):
        if not v.startswith("gs://"):
            raise ValueError("gs_path is not a valid gcp bucket path")
        return v