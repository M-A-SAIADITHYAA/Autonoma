import os
from pathlib import Path
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

class Settings(BaseModel):
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    drive_dir: Path = PROJECT_ROOT / "data" / "sample_drive"
    db_path: Path = PROJECT_ROOT / "data" / "company_erp.db"
    
    # Server ports
    company_host: str = "127.0.0.1"
    company_port: int = 8000
    company_base_url: str = "http://127.0.0.1:8000"
    
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 8080
    
    # Agent constraints & parameters
    max_steps: int = 25
    approval_amount_threshold: float = 10000.0
    auto_retry_max_attempts: int = 3
    retry_backoff_seconds: float = 0.5
    
    # LLM configurations
    llm_provider: str = Field(
        default_factory=lambda: os.getenv("AUTONOMA_LLM_PROVIDER", "gemini")
    )
    openai_api_key: str | None = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    gemini_api_key: str | None = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
    )
    gemini_model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
    )
    anthropic_api_key: str | None = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    ollama_base_url: str | None = Field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

settings = Settings()

# Ensure directories exist
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.drive_dir.mkdir(parents=True, exist_ok=True)
