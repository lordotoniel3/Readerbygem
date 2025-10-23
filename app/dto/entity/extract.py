from datetime import datetime

from pydantic import BaseModel

from app.dto.entity.base_entity import BaseEntity


class Extract(BaseEntity, BaseModel):
    bankName: str | None = None
    bankAddress: str | None = None
    bankTel: str | None = None
    holderName: str | None = None
    clientNumber: str | None = None
    holderAddress: str | None = None
    accountType: str | None = None
    accountNumber: str | None = None
    currency: str | None = None
    startDatePeriod: datetime | None = None
    endDatePeriod: datetime | None = None
    previousBalance: float | None = None
    actualBalance: float | None = None
    totalDeposits: float | None = None
    totalWithdrawals: float | None = None
    totalCommissions: float | None = None
    interestRate: float | None = None
    interestEarned: float | None = None
    withholding: float | None = None
    nextCutOffDate: datetime | None = None
    statementIssueDate: datetime | None = None
    statementNumber: str | None = None
    movements: list['ExtractMovement'] = []
    trusts: list['ExtractTrust'] = []
    

class ExtractMovement(BaseModel):
    date: datetime | None = None
    description: str | None = None
    reference: str | None = None
    value: float | None = None
    type: str | None = None
    subsequentBalance: float | None = None

# TODO: Must be implemented in the Java API
class ExtractTrust(BaseModel):
    trustName: str | None = None
    trustDate: datetime | None = None
    trustValue: float | None = None
    concept: str | None = None
    movements: list['ExtractMovement'] = []