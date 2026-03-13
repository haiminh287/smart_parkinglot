import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "parksmartdb"
    DB_USER: str = "root"
    DB_PASSWORD: str = "rootpassword"
    DEBUG: bool = True
    GATEWAY_SECRET: str = "gateway-internal-secret-key"
    MEDIA_ROOT: str = "/app/media"
    ML_MODELS_DIR: str = "/app/ml/models"
    PARKING_SERVICE_URL: str = "http://parking-service:8000"
    BOOKING_SERVICE_URL: str = "http://booking-service:8000"
    REALTIME_SERVICE_URL: str = "http://realtime-service-go:8006"
    PLATE_MODEL_PATH: str = "/app/app/models/license-plate-finetune-v1m.pt"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure media directory exists
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
