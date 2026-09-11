import os
from pathlib import Path
from typing import Optional
from pydantic import ConfigDict
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "CacheMind"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Storage Paths
    BASE_DIR: Path = BASE_DIR
    STORAGE_DIR: Path = BASE_DIR / "data"
    DOCUMENT_STORAGE: Path = BASE_DIR / "data" / "documents"
    VECTOR_STORAGE: Path = BASE_DIR / "data" / "indices"
    DB_PATH: Path = BASE_DIR / "data" / "cachemind.db"
    
    # Embedding Model Settings
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    
    # Caching Settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    EXACT_CACHE_TTL_SECONDS: int = 3600 * 24  # 24 hours
    SEMANTIC_CACHE_SIMILARITY_THRESHOLD: float = 0.88
    SEMANTIC_CACHE_MAX_ENTRIES: int = 10000
    RETRIEVAL_CACHE_TTL_SECONDS: int = 3600 * 12 # 12 hours
    PREFIX_CACHE_ENABLED: bool = True
    
    # Cache Admission Policy
    ADMISSION_MIN_FREQUENCY: int = 1
    ADMISSION_MIN_GENERATION_COST_MS: float = 100.0
    
    # Agent & Planning
    AGENT_MAX_STEPS: int = 6
    AGENT_TIMEOUT_SECONDS: float = 30.0
    AGENT_MAX_REWRITES: int = 2
    
    # LLM Router Defaults (Local)
    DEFAULT_SMALL_MODEL: str = "qwen2.5:0.5b"
    DEFAULT_MEDIUM_MODEL: str = "qwen2.5:3b"
    DEFAULT_LARGE_MODEL: str = "qwen2.5:7b"
    
    # Groq Cloud Inference (Optional for ultra-fast 500+ tokens/s)
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", "")
    GROQ_SMALL_MODEL: str = "llama-3.1-8b-instant"
    GROQ_MEDIUM_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_LARGE_MODEL: str = "llama-3.3-70b-versatile"
    
    # Local Inference & llama.cpp
    LLAMA_CPP_BASE_URL: str = os.getenv("LLAMA_CPP_BASE_URL", "http://localhost:8080")
    USE_MOCK_LLM_IF_UNAVAILABLE: bool = True
    
    model_config = ConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Ensure directories exist
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.DOCUMENT_STORAGE.mkdir(parents=True, exist_ok=True)
settings.VECTOR_STORAGE.mkdir(parents=True, exist_ok=True)
