from abc import ABC


class BaseEntity(ABC):
    filename: str
    score: float
    score_explaining: str | None = None