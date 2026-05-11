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

    # ─── Email (Gmail SMTP) ───────────────────────────────────────────────
    # Setup: bật 2FA cho Gmail → tạo App Password 16 ký tự tại
    # https://myaccount.google.com/apppasswords → set EMAIL_HOST_PASSWORD.
    EMAIL_HOST: str = "smtp.gmail.com"
    EMAIL_PORT: int = 587
    EMAIL_HOST_USER: str = ""        # e.g. minhht2k4@gmail.com
    EMAIL_HOST_PASSWORD: str = ""    # Gmail App Password (16 chars)
    EMAIL_FROM_NAME: str = "ParkSmart"
    ADMIN_EMAIL: str = "minhht2k4@gmail.com"  # fallback nếu user không có email

    # ─── Realtime push ────────────────────────────────────────────────────
    REALTIME_SERVICE_URL: str = "http://realtime-service-go:8006"

    # ─── Auth-service (lookup user email khi cần) ─────────────────────────
    AUTH_SERVICE_URL: str = "http://auth-service:8000"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"


settings = Settings()
