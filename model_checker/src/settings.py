from functools import lru_cache
from uuid import UUID

from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    nats_url: str

    class Config:
        env_file = ".env"


@lru_cache
def get_settings():
    return Settings()
