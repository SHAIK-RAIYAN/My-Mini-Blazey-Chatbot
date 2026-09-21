from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_ENV: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    GOOGLE_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    JWT_TOKEN: str = ""
    PROJECT_API_BASE_URL: str = "http://api.stg.blazeup.ai/project-api"
    EMPLOYEE_API_BASE_URL: str = "http://api.stg.blazeup.ai/employees-api"
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "blazeup_agent_db"

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
