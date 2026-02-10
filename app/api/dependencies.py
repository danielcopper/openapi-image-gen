from app.core.config import settings
from app.services.gemini_service import get_gemini_service
from app.services.litellm_service import get_litellm_service
from app.services.openai_service import get_openai_service


def get_service(provider: str):
    """Get service instance based on provider."""
    if provider == "litellm":
        if not settings.litellm_available:
            raise ValueError("LiteLLM not configured. Set LITELLM_BASE_URL")
        return get_litellm_service()
    elif provider == "openai":
        if not settings.openai_available:
            raise ValueError("OpenAI not configured. Set OPENAI_API_KEY")
        return get_openai_service()
    elif provider == "gemini":
        if not settings.gemini_available:
            raise ValueError("Gemini not configured. Set GEMINI_API_KEY")
        return get_gemini_service()
    else:
        raise ValueError(f"Unknown provider: {provider}")
