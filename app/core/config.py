from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database (default SQLite for local dev without Docker)
    DATABASE_URL: str = "postgresql://ncfu:ncfu_password@db:5432/ncfu_attendance"

    # Face recognition
    FACE_RECOGNITION_TOLERANCE: float = 0.6

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
