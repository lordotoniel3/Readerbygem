from datetime import datetime
from pydantic import BaseModel
from app.dto.entity.base_entity import BaseEntity

class CC(BaseEntity, BaseModel):
    documentType: str | None = None
    number: str | None = None
    lastNames: str | None = None
    names: str | None = None
    birthday: datetime | None = None
    birthPlace: str | None = None
    expeditionDate: datetime | None = None
    expeditionPlace: str | None = None
    height: float | None = None
    bloodType: str | None = None
    sex: str | None = None