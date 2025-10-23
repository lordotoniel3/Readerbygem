from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.dto.entity.base_entity import BaseEntity


class RUT(BaseEntity, BaseModel):
    formNumber: str | None = None
    expeditionDate: datetime | None = None
    lastUpdateDate: datetime | None = None
    documentType: str | None = None
    documentNumber: str | None = None
    dv: str | None = None
    companyName: str | None = None
    firstSurname: str | None = None
    firstName: str | None = None
    birthday: datetime | None = None
    birthCountry: str | None = None
    birthDepartment: str | None = None
    birthCity: str | None = None
    address: str | None = None
    country: str | None = None
    department: str | None = None
    city: str | None = None
    email: str | None = None
    phone: str | None = None
    cellphone: str | None = None
    electronicNotification: str | None = None
    contributorType: str | None = None
    regime: str | None = None
    activityStartDate: datetime | None = None
    rutStatus: str | None = None

    activities: list["RUTActivity"] = []
    establishments: list["RUTEstablishments"] = []
    representatives: list["RUTRepresentative"] = []
    responsibilities: list["RUTResponsibilities"] = []


class RUTActivity(BaseModel):
    id: int | None = None
    ciiuCode: int | None = None
    description: str | None = None
    mainActivity: str | None = None
    startDate: datetime | None = None


class RUTEstablishments(BaseModel):
    id: int | None = None
    name: str | None = None
    address: str | None = None
    city: str | None = None
    department: str | None = None
    mainActivity: str | None = None
    openingDate: datetime | None = None


class RUTRepresentative(BaseModel):
    documentType: str | None = None
    documentNumber: str | None = None
    fullName: str | None = None
    position: str | None = None


class RUTResponsibilities(BaseModel):
    id: int | None = None
    code: str | None = None
    description: str | None = None
    startDate: datetime | None = None
    endDate: datetime | None = None
