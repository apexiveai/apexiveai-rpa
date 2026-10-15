from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Apexive MPT RPA Platform"
    environment: str = "development"
    api_prefix: str = "/api"
    secret_key: str
    database_url: str
    redis_url: str
    cors_origins: str = "http://localhost:3030"
    access_token_minutes: int = 60
    robot_token: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
