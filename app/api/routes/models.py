import logging
from fastapi import APIRouter, Depends

from app.core.security import verify_token
from app.schemas.requests import ModelRefreshRequest
from app.schemas.responses import ModelListResponse
from app.services.model_registry import model_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["Models"])


@router.get(
    "",
    response_model=ModelListResponse,
    operation_id="list_models",
    summary="List available models",
    description=(
        "Get list of available image generation models. "
        "Results are cached and refreshed periodically or on demand."
    )
)
async def list_models(
    _: None = Depends(verify_token)
) -> ModelListResponse:
    """
    List all available models for image generation.
    """
    models = model_registry.get_models()

    return ModelListResponse(
        models=models,
        cached=model_registry.cache_valid,
        cache_expires_in=model_registry.cache_expires_in
    )


@router.post(
    "/refresh",
    response_model=ModelListResponse,
    operation_id="refresh_models",
    summary="Refresh model list",
    description=(
        "Force refresh of available models from LiteLLM. "
        "Use this to reload models after configuration changes."
    )
)
async def refresh_models(
    request: ModelRefreshRequest = ModelRefreshRequest(),
    _: None = Depends(verify_token)
) -> ModelListResponse:
    """
    Refresh model list from LiteLLM.
    """
    logger.info(f"Refreshing models (force={request.force})")

    models = await model_registry.load_models(force=request.force)

    return ModelListResponse(
        models=models,
        cached=False,  # Just refreshed
        cache_expires_in=model_registry.cache_expires_in
    )
