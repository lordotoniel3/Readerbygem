from pydantic import BaseModel

from app.dto.process import DocType


class Log(BaseModel):
    name: str
    status: str
    format: DocType
    parent_file: str | None = None
    identified_format: str # Str and not Doctype due to being a gemini call
    invalid_format: bool
    # is_duplicate: bool TODO remake this on the quarkus side

class ValidationError(BaseModel):
    check_fields: dict | None = None
