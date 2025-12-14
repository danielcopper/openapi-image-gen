import tomllib
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def get_version() -> str:
    """Get version from pyproject.toml."""
    try:
        pyproject = Path(__file__).parent.parent.parent / "pyproject.toml"
        with open(pyproject, "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except Exception:
        return "0.1.0"


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    # API Configuration
    API_TITLE: str = "Image Generation API"
    API_VERSION: str = get_version()
    API_DESCRIPTION: str = (
        "Generate images using OpenAI DALL-E and Google Gemini via LiteLLM proxy "
        "with fallback to direct API calls. Supports SSE progress streaming."
    )

    # LiteLLM Configuration (Primary)
    LITELLM_BASE_URL: str | None = None
    LITELLM_API_KEY: str | None = None

    # Direct Provider API Keys (Fallback)
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    # Storage Configuration
    STORAGE_PATH: str = "./generated_images"
    BASE_URL: str = "http://localhost:8000"

    # Security (Optional)
    API_BEARER_TOKEN: str | None = None

    # Model Registry
    MODEL_CACHE_TTL: int = 3600  # Cache models for 1 hour

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @property
    def litellm_available(self) -> bool:
        """Check if LiteLLM is configured."""
        return bool(self.LITELLM_BASE_URL)

    @property
    def openai_available(self) -> bool:
        """Check if OpenAI direct access is available."""
        return bool(self.OPENAI_API_KEY)

    @property
    def gemini_available(self) -> bool:
        """Check if Gemini direct access is available."""
        return bool(self.GEMINI_API_KEY)


settings = Settings()
