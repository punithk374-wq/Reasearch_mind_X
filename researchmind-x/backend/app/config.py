from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440
    gemini_api_key: str
    gemini_model: str = "gemini-2.5-flash"
    openalex_api_key: str = ""
    semantic_scholar_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()