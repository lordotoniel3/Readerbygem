from typing import Union
from uuid import UUID

from pydantic import BaseModel

from app.dto.entity.balance import Balance
from app.dto.entity.bill import Bill
from app.dto.entity.buy_order import BuyOrder
from app.dto.entity.cc import CC
from app.dto.entity.cv import CV
from app.dto.entity.email import Email
from app.dto.entity.existence import Existence
from app.dto.entity.extract import Extract
from app.dto.entity.pay import Payment
from app.dto.entity.rub import RUB
from app.dto.entity.rut import RUT
from app.dto.log import Log, ValidationError


class EntityStore(BaseModel):
    load_id: UUID
    # Pydantic cant generate a schema for an abstract class, python is not java
    entity: Union[Balance, Bill, BuyOrder, CC, CV, Existence, Extract, RUB, RUT, Payment, Email, None] = None # None is something fails
    log: Log
    validation: ValidationError | None = None # None if there is no validation or error checking
