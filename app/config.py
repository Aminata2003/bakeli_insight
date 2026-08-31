from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    api_keys: str = "admin-secret:admin,analyst-secret:analyst,moderator-secret:moderator"


settings = Settings()