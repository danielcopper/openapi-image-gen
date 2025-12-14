import base64
import logging
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.config import settings
from app.core.security import verify_token
from app.schemas.responses import ImageResponse
from app.services.gemini_service import get_gemini_service
from app.services.litellm_service import get_litellm_service
from app.services.model_registry import model_registry
from app.services.openai_service import get_openai_service
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edit", tags=["Image Editing"])

# Type aliases for form fields
ImageFile = Annotated[UploadFile | None, File(description="Image file to edit")]
MaskFile = Annotated[UploadFile | None, File(description="Mask image (transparent areas will be edited)")]


@router.post(
    "",
    response_model=ImageResponse,
    operation_id="edit_image",
    summary="Edit image",
    description=(
        "Edit an existing image using mask-based inpainting (OpenAI) or "
        "prompt-based editing (Gemini). Provide either an image file upload "
        "or a URL to an existing image."
    ),
)
async def edit_image(
    prompt: str = Form(..., description="Description of the edit to make"),
    provider: Literal["litellm", "openai", "gemini"] = Form(
        "litellm", description="Provider to use for editing"
    ),
    model: str | None = Form(None, description="Model ID (optional, uses default if not set)"),
    image: ImageFile = None,
    image_url: str | None = Form(None, description="URL to existing image (alternative to upload)"),
    mask: MaskFile = None,
    n: int = Form(1, ge=1, le=4, description="Number of variations to generate"),
    response_format: Literal["url", "base64", "markdown"] = Form(
        "url", description="Response format"
    ),
    _: None = Depends(verify_token),
) -> ImageResponse:
    """
    Edit an image using mask-based (OpenAI) or prompt-based (Gemini) editing.
    """
    logger.info(f"Edit request: provider={provider}, model={model}")

    # Validate: need either image upload or image_url
    if not image and not image_url:
        raise HTTPException(
            status_code=400, detail="Either 'image' file or 'image_url' must be provided"
        )

    # Load image bytes
    try:
        if image:
            image_bytes = await image.read()
        else:
            image_bytes = await storage_service.get_image(image_url)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except Exception as e:
        logger.error(f"Failed to load image: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to load image: {str(e)}") from None

    # Load mask bytes if provided
    mask_bytes = None
    if mask:
        mask_bytes = await mask.read()

    # Determine model if not specified
    if not model:
        model = _get_default_edit_model(provider)

    # Get service based on provider
    try:
        service = _get_service(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Edit image
    try:
        if provider == "gemini":
            # Gemini uses prompt-based editing (no mask)
            urls = await service.edit_image(
                image=image_bytes,
                prompt=prompt,
                model=model,
                n=n,
            )
        else:
            # OpenAI/LiteLLM uses mask-based editing
            urls = await service.edit_image(
                image=image_bytes,
                prompt=prompt,
                model=model,
                mask=mask_bytes,
                n=n,
            )
    except Exception as e:
        logger.error(f"Edit failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Edit failed: {str(e)}") from None

    if not urls:
        raise HTTPException(status_code=500, detail="No images generated")

    # Handle response format
    if response_format == "base64":
        image_filename = urls[0].split("/")[-1]
        image_path = Path(settings.STORAGE_PATH) / image_filename

        if not image_path.exists():
            raise HTTPException(status_code=500, detail="Edited image file not found")

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        ext = image_path.suffix.lower()
        mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
        mime_type = mime_types.get(ext, "image/png")

        return ImageResponse(
            image_base64=image_data,
            mime_type=mime_type,
            prompt=prompt,
            model=model,
            provider=provider,
            metadata={"n": len(urls), "edit": True},
        )

    if response_format == "markdown":
        markdown = f"![Edited image]({urls[0]})"
        return ImageResponse(
            markdown=markdown,
            image_url=urls[0],
            prompt=prompt,
            model=model,
            provider=provider,
            metadata={"n": len(urls), "edit": True},
        )

    return ImageResponse(
        image_url=urls[0],
        prompt=prompt,
        model=model,
        provider=provider,
        metadata={
            "all_urls": urls if len(urls) > 1 else None,
            "n": len(urls),
            "edit": True,
        },
    )


def _get_service(provider: str):
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


def _get_default_edit_model(provider: str) -> str:
    """Get default model for editing based on provider."""
    # Check if DEFAULT_MODEL supports editing
    if settings.DEFAULT_MODEL:
        model_info = model_registry.get_model(settings.DEFAULT_MODEL)
        if model_info and model_info.capabilities.supports_editing:
            return settings.DEFAULT_MODEL

    # Find first model that supports editing for this provider
    models = model_registry.get_models()
    for m in models:
        if m.capabilities.supports_editing and (provider == "litellm" or m.provider == provider):
            return m.id

    # Fallback defaults
    if provider == "gemini":
        return "gemini-2.0-flash-preview-image-generation"
    else:
        return "gpt-image-1"
