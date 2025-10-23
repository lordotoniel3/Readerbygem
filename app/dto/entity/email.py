from pydantic import BaseModel
from datetime import datetime

from app.dto.entity.base_entity import BaseEntity


class Email(BaseEntity, BaseModel):
    email: str | None = None
    subject: str | None = None
    body: str | None = None
    date: datetime | None = None
    attachmentCount: int | None = None
