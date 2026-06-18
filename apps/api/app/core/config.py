from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    app_name: str = "AI Workspace Chat"
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(default_factory=lambda: [
        "http://localhost:3000", 
        "https://work-space-web.vercel.app"
    ])

    database_url: str = ""
    supabase_url: str = ""
    supabase_jwks_url: str = ""
    supabase_service_role_key: str = ""

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    llm_api_key: str = ""
    llm_base_url: str = "https://openrouter.ai/api/v1"
    default_model: str = "openai/gpt-4o-mini"
    cheap_model: str = "openai/gpt-4o-mini"
    max_output_tokens: int = 2400

    tavily_api_key: str = ""
    tavily_search_depth: str = "basic"
    max_web_search_results: int = 5
    embedding_provider: str = "openai"
    embedding_api_key: str = ""
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 768
    embedding_batch_size: int = 24
    upload_dir: str = "uploads"
    max_upload_mb: int = 12
    langchain_verbose: bool = False

    model_config = SettingsConfigDict(env_file=None, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.supabase_url.startswith("your_"):
        settings.supabase_url = ""
    if settings.supabase_jwks_url.startswith("your_"):
        settings.supabase_jwks_url = ""
    if settings.supabase_service_role_key.startswith("your_"):
        settings.supabase_service_role_key = ""
    if settings.embedding_api_key.startswith("your_"):
        settings.embedding_api_key = ""
    return settings
