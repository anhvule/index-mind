from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, read from INDEXMIND_* environment variables or a .env file."""

    model_config = SettingsConfigDict(env_prefix="INDEXMIND_", env_file=".env", extra="ignore")

    docs_dir: Path = Path("../documents")
    data_dir: Path = Path(".indexmind")

    ollama_url: str = "http://127.0.0.1:11434"
    chat_model: str = "llama3.2"
    embed_model: str = "nomic-embed-text"

    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 6


@lru_cache
def get_settings() -> Settings:
    return Settings()
