from pydantic import BaseModel
from datetime import date

from app.dto.entity.base_entity import BaseEntity


class Payment(BaseEntity, BaseModel):
    fechaPago: date | None = None
    identificacionBeneficiario: str | None = None
    medioPago: str | None = None
    valorPago: float | None = None
    numeroReferencia: str | None = None
    entidadBancaria: str | None = None
    cuentaBeneficiario: str | None = None
