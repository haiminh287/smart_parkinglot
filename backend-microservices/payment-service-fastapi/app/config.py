from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "parksmartdb"
    DB_USER: str = Field(..., min_length=1)
    DB_PASSWORD: str = Field(..., min_length=1)
    DEBUG: bool = True
    GATEWAY_SECRET: str = Field(..., min_length=1)
    BOOKING_SERVICE_URL: str = "http://booking-service:8000"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service-fastapi:8005"
    REALTIME_SERVICE_URL: str = "http://realtime-service-go:8006"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
