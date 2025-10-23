from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.dto.entity.base_entity import BaseEntity


class BuyOrder(BaseEntity, BaseModel):
    orderNumber: str | None = None
    issueDate: datetime | None = None
    currency: str | None = None
    buyerName: str | None = None
    buyerId: str | None = None
    buyerAddress: str | None = None
    buyerTel: str | None = None
    buyerEmail: str | None = None
    providerName: str | None = None
    providerId: str | None = None #TODO: Change to providerId in API
    providerAddress: str | None = None
    providerTel: str | None = None
    providerEmail: str | None = None

    subTotal: float | None = None
    taxes: float | None = None
    discounts: float | None = None
    total: float | None = None

    paymentMethod: str | None = None
    deliveryTime: str | None = None
    deliveryAddress: str | None = None
    observations: str | None = None

    items: list['BuyOrderItems'] = []

class BuyOrderItems(BaseModel):
    description: str | None = None
    quantity: float | None = None
    measureUnit: str | None = None
    unitaryPrice: float | None = None
    subTotal: float | None = None
