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

    # ─── Internal service URLs ────────────────────
    BOOKING_SERVICE_URL: str = "http://booking-service:8000"
    PARKING_SERVICE_URL: str = "http://parking-service:8000"
    VEHICLE_SERVICE_URL: str = "http://vehicle-service:8000"
    PAYMENT_SERVICE_URL: str = "http://payment-service-fastapi:8007"
    REALTIME_SERVICE_URL: str = "http://realtime-service-go:8006"

    # ─── LLM (🔥 2.1 / 2.2) ─────────────────────
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # ─── Redis cache ─────────────────────────────
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 3  # separate from other services

    # ─── RabbitMQ (proactive events 🔥 2.5) ──────
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
