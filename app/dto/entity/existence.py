from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.dto.entity.base_entity import BaseEntity


class Existence(BaseEntity, BaseModel):
    expeditionDate: datetime | None = None
    receiptNumber: str | None = None
    verificationCode: str | None = None
    social: str | None = None
    acronym: str | None = None
    nit: str | None = None
    legalOrganization: str | None = None
    category: str | None = None
    commercialRegistration: str | None = None
    enrollmentDate: datetime | None = None
    address: str | None = None
    mainAddress: str | None = None
    commercialTel: str | None = None
    commercialEmail: str | None = None
    web: str | None = None
    constitutionDate: datetime | None = None
    deed: str | None = None
    notary: str | None = None
    effectiveDate: str | None = None
    socialObject: str | None = None
    ciiu: str | None = None
    ciiuDescription: str | None = None
    economicSector: str | None = None
    totalAssets: float | None = None
    companySize: str | None = None
    ordinaryActivityIncome: float | None = None
    capitalType: str | None = None
    capitalValue: float | None = None
    representativePowers: str | None = None
    representativeLimits: str | None = None
    fiscalReviewer: str | None = None
    enrollmentStatus: str | None = None

    establishments: list["ExistenceEstablishments"] = []
    legalRepresentatives: list["ExistenceLegalRepresentative"] = []
    partners: list["ExistencePartners"] = []


class ExistenceEstablishments(BaseModel):
    name: str | None = None
    registration: str | None = None
    registrationDate: datetime | None = None
    address: str | None = None
    city: str | None = None
    tel_1: str | None = None
    tel_2: str | None = None
    email: str | None = None
    mainActivity: str | None = None
    activityDescription: str | None = None #TODO:change in api
    establishmentValue: float | None = None


class ExistenceLegalRepresentative(BaseModel):
    name: str | None = None
    position: str | None = None
    idType: str | None = None
    idNumber: str | None = None
    isSubstitute: str | None = None #TODO: Maybe change to bool
    namingDate: datetime | None = None
    namingDoc: str | None = None


class ExistencePartners(BaseModel):
    name: str | None = None
    idType: str | None = None
    idNumber: str | None = None
    sharesNumber: str | None = None #TODO: Maybe change to int or float
    participationValue: float | None = None
    participationPercent: float | None = None