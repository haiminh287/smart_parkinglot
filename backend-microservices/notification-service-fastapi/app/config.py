"""
Configuration using Pydantic Settings
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DEBUG: bool = False
    DB_HOST: str = "mysql"
    DB_PORT: int = 3306
    DB_USER: str = "parksmartuser"
    DB_PASSWORD: str  # required, no default
    DB_NAME: str = "parksmartdb"
    GATEWAY_SECRET: str  # required, no default
    RABBITMQ_URL: str = "amqp://admin:admin@rabbitmq:5672/"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"


settings = Settings()
