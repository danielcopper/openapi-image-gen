import logging
from fastapi import APIRouter
import httpx

from app.core.config import settings
from app.schemas.responses import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    operation_id="health_check",
    summary="Health check",
    description="Check service health and provider availability"
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint to verify service and provider availability.
    """
    # Check LiteLLM connectivity
    litellm_available = False
    if settings.LITELLM_BASE_URL:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                url = f"{settings.LITELLM_BASE_URL.rstrip('/')}/health"
                response = await client.get(url)
                litellm_available = response.status_code == 200
        except Exception as e:
            logger.warning(f"LiteLLM health check failed: {e}")
            litellm_available = False

    return HealthResponse(
        status="healthy",
        litellm=litellm_available,
        openai=settings.openai_available,
        gemini=settings.gemini_available
    )
