from datetime import  datetime
from pydantic import BaseModel, ConfigDict

from app.dto.entity.base_entity import BaseEntity


class CV(BaseEntity, BaseModel):
    fullName: str | None = None
    description: str | None = None
    email: str | None = None
    tel: str | None = None
    fullAddress: str | None = None

    abilities: list["Ability"] = []
    education: list["Education"] = []
    experiences: list["Experience"] = []
    languages: list["Language"] = []
    
class Ability(BaseModel):
    name: str | None = None

class Language(BaseModel):
    name: str | None = None
    level: str | None = None
    test: str | None = None

class Education(BaseModel):
    title: str | None = None  #TODO: This name must be kept in the api
    place: str | None = None # TODO: This name must be kept in the api
    startDate: datetime | None = None #TODO: In the API this must be type date
    endDate: datetime | None = None #TODO: In the API this must be type date
    type: str | None = None #TODO: This must be implemented in the api

class Experience(BaseModel):
    jobPosition: str | None = None
    company: str | None = None
    startDate: datetime | None = None #TODO: In the API this must be implemented
    endDate: datetime | None = None #TODO: In the API this must be implemented
    description: str | None = None








