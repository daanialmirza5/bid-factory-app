from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BidFactory API"
    frontend_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    max_upload_size_bytes: int = 25 * 1024 * 1024
    knowledge_base_dir: str = "data/knowledge_base"
    vector_store_dir: str = "data/vector_store"
    embedding_model: str = "all-MiniLM-L6-v2"
    retrieval_top_k: int = 5
    retrieval_min_score: float = 0.25
    # When RocketRide is unreachable or fails, extract requirements by calling Groq
    # directly instead. Off by default so pipeline failures surface as errors.
    ai_fallback_direct_groq: bool = False
    rocketride_timeout_seconds: float = 120.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()