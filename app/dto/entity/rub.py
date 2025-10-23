from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.dto.entity.base_entity import BaseEntity


class RUB(BaseEntity, BaseModel):
    formNumber: str | None = None
    reportingDate: datetime | None = None
    reportType: str | None = None
    companyName: str | None = None
    nit: str | None = None
    dv: str | None = None
    entityType: str | None = None
    address: str | None = None
    department: str | None = None
    tel: str | None = None
    email: str | None = None
    legalRepresentativeName: str | None = None
    legalRepresentativeSurname: str | None = None
    legalRepresentativeDocumentType: str | None = None
    legalRepresentativeDocumentNumber: str | None = None
    legalRepresentativeCellPhone: str | None = None
    legalRepresentativeEmail: str | None = None
    declarant: str | None = None
    position: str | None = None
    declarationDate: datetime | None = None

    beneficiaries: list["RUBBeneficiaries"] = []

class RUBBeneficiaries(BaseModel):
    personType: str | None = None
    name: str | None = None
    surname: str | None = None
    companyName: str | None = None
    documentType: str | None = None
    documentNumber: str | None = None
    dv: str | None = None
    documentCountry: str | None = None
    birthday: datetime | None = None
    birthCountry: str | None = None
    nationality: str | None = None
    residenceCountry: str | None = None
    address: str | None = None
    town: str | None = None
    department: str | None = None
    tel: str | None = None
    email: str | None = None
    beneficiaryType: str | None = None
    determinationCriteria: str | None = None
    participationPercentage: str | None = None
    startDate: datetime | None = None
    endDate: datetime | None = None