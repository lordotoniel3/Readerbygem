from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    MAX_THREADS: int = 5 #Max threads for executing parallel tasks
    region: str
    project_id: str
    __hash__ = object.__hash__
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

class RMQSettings(BaseSettings):
    rmq_user: str = "guest",
    rmq_pass: str = "guest",
    rmq_host: str
    rmq_port: int = 5672
    rmq_max_tasks: int = 7
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache()
def get_settings():
    return Settings()
