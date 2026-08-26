from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="/workspace/backend/.env", extra="ignore")

    app_env: str = "prod"
    app_debug: bool = False

    database_host: str = "127.0.0.1"
    database_port: int = 3306
    database_name: str = ""
    database_user: str = ""
    database_password: str = ""

    jwt_secret: str = "dev-secret"
    jwt_expires_min: int = 86400

    llm_api_key: str = ""
    llm_base_url: str = "https://llm.drytis.ai"
    llm_model: str = "gpt-5"

    upload_dir: str = "/workspace/storage/uploads"
    analysis_concurrency: int = 4
    cors_origins: str = "*"

    max_upload_bytes: int = 10 * 1024 * 1024

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
