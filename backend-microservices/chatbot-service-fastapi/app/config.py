from pydantic import Field, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_HOST: str = "localhost"
    DB_PORT: int = 3307  # 3307 = Docker host port; inside Docker set DB_PORT=3306 via env
    DB_NAME: str = "parksmartdb"
    DB_USER: str = Field(..., min_length=1)
    DB_PASSWORD: str = Field(..., min_length=1)
    DEBUG: bool = True
    GATEWAY_SECRET: str = Field(..., min_length=1)

    BOOKING_SERVICE_URL: str = "http://booking-service:8000"
    PARKING_SERVICE_URL: str = "http://parking-service:8000"
    VEHICLE_SERVICE_URL: str = "http://vehicle-service:8000"
    PAYMENT_SERVICE_URL: str = "http://payment-service-fastapi:8007"
    REALTIME_SERVICE_URL: str = "http://realtime-service-go:8006"
    GEMINI_API_KEY: str = "AIzaSyC6NTItetrCfK0TrY6DY6-u4YQ1GqYSD3E"
    GEMINI_MODEL: str = "gemini-3-flash-preview"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 3 
    RABBITMQ_URL: str = "amqp://guest:guest@rabbitmq:5672/"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
