from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "parksmartdb"
    DB_USER: str = "root"
    DB_PASSWORD: str  # required, no default
    DEBUG: bool = True
    GATEWAY_SECRET: str  # required, no default
    MEDIA_ROOT: str = "/app/media"
    ML_MODELS_DIR: str = "/app/ml/models"
    PARKING_SERVICE_URL: str = "http://parking-service:8000"
    BOOKING_SERVICE_URL: str = "http://booking-service:8000"
    REALTIME_SERVICE_URL: str = "http://realtime-service-go:8006"
    PLATE_MODEL_PATH: str = "/app/app/models/license-plate-finetune-v1m.pt"
    BANKNOTE_MODEL_PATH: str = ""
    YOLO_PARKING_MODEL_PATH: str = "/app/ml/models/yolo11n.pt"
    YOLO_PARKING_IOU_THRESHOLD: float = 0.15
    YOLO_PARKING_CONF_THRESHOLD: float = 0.25
    CAMERA_DROIDCAM_URL: str = "http://192.168.100.130:4747"
    CAMERA_RTSP_URL: str = "rtsp://user:password@192.168.1.100:554/H.264"
    CAMERA_HTTP_URL: str = "http://192.168.100.130:80"
    ESP32_DEVICE_TOKEN: str  # required — no default
    CORS_ALLOWED_ORIGINS: str = ""

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def cors_origins_list(self) -> list[str]:
        if not self.CORS_ALLOWED_ORIGINS:
            return [
                "http://localhost:5173",
                "http://localhost:3000",
                "http://localhost:8080",
            ]
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

    model_config = ConfigDict(env_file=".env")


settings = Settings()
