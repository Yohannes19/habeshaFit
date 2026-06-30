from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
    app_env: str = "development"
    app_secret_key: str = "dev-secret"

    @property
    def is_dev(self): return self.app_env == "development"

@lru_cache
def get_settings(): return Settings()
settings = get_settings()
