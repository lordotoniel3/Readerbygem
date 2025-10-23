from typing import Optional, Dict
from pydantic import BaseModel

class ValidationErrorResponse(BaseModel):
    content_id: str  
    check_fields: Optional[Dict[str, Optional[str]]]
