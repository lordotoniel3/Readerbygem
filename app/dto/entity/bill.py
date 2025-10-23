from datetime import date
from pydantic import BaseModel

from app.dto.entity.base_entity import BaseEntity
#It is refered to as factura and invoice throughout the code

class Bill(BaseEntity, BaseModel):
    nit: str | None = None
    billExpeditionDate: date | None = None #This MUST be implemented in the Java API
    billExpirationDate: date | None = None #This MUST be implemented in the Java API
    supplierName: str | None = None
    totalAmount: float | None = None
    totalTaxAmount: float | None = None
    netAmount: float | None = None
    products: list['Product'] = []


class Product(BaseModel):
    description: str | None = None
    quantity: float | None = None
    unitPrice: float | None = None
    productId: str | None = None