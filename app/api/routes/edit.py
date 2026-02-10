import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.dependencies import get_service
from app.core.config import settings
from app.core.security import verify_token
from app.schemas.requests import ImageEditRequest
from app.schemas.responses import ImageResponse
from app.services.model_registry import model_registry
from app.services.storage_service import storage_service
from app.utils.image import build_openwebui_html_response, read_image_as_base64

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
        service = get_service(provider)
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
        try:
            image_data, mime_type = await read_image_as_base64(urls[0], cleanup=False)
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Edited image file not found") from None

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


@router.post(
    "/json",
    response_model=None,
    operation_id="edit_image_json",
    summary="Edit image (JSON)",
    description=(
        "Edit an existing image using a JSON request body. "
        "This endpoint is designed for LLM tool use - provide the image_url "
        "from a previous generate_image response. Uses prompt-based editing. "
        "Response format depends on OPENWEBUI_MODE setting."
    ),
)
async def edit_image_json(
    request: ImageEditRequest,
    _: None = Depends(verify_token),
):
    """
    Edit an image using JSON request body (LLM-friendly endpoint).
    """
    logger.info(f"Edit JSON request: provider={request.provider}, model={request.model}")

    # Load image from URL
    try:
        image_bytes = await storage_service.get_image(request.image_url)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except Exception as e:
        logger.error(f"Failed to load image: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to load image: {str(e)}") from None

    # Determine model if not specified
    model = request.model
    if not model:
        model = _get_default_edit_model(request.provider)

    # Get service based on provider
    try:
        service = get_service(request.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

    # Edit image (prompt-based, no mask for JSON endpoint)
    try:
        urls = await service.edit_image(
            image=image_bytes,
            prompt=request.prompt,
            model=model,
            n=request.n,
        )
    except Exception as e:
        logger.error(f"Edit failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Edit failed: {str(e)}") from None

    if not urls:
        raise HTTPException(status_code=500, detail="No images generated")

    # OpenWebUI mode
    if settings.OPENWEBUI_MODE:
        if settings.openwebui_upload_available:
            # OWUI upload succeeded — URL is already an OWUI file URL.
            return ImageResponse(
                image_url=urls[0],
                markdown=f"![Edited image]({urls[0]})",
                prompt=request.prompt,
                model=model,
                provider=request.provider,
                metadata={
                    "n": len(urls),
                    "edit": True,
                    "source_image": request.image_url,
                    "all_urls": urls if len(urls) > 1 else None,
                },
            )
        # Fallback: HTMLResponse with base64 (iframe display)
        try:
            image_data, mime_type = await read_image_as_base64(urls[0])
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Edited image file not found") from None
        return build_openwebui_html_response(image_data, mime_type)

    # Return based on MARKDOWN_EMBED_IMAGES setting
    if settings.MARKDOWN_EMBED_IMAGES:
        try:
            image_data, mime_type = await read_image_as_base64(urls[0])
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Edited image file not found") from None

        markdown = f"![Edited image](data:{mime_type};base64,{image_data})"
        return ImageResponse(
            markdown=markdown,
            prompt=request.prompt,
            model=model,
            provider=request.provider,
            metadata={
                "n": len(urls),
                "edit": True,
                "source_image": request.image_url,
            },
        )
    else:
        # Return markdown with image URL
        markdown = f"![Edited image]({urls[0]})"
        return ImageResponse(
            markdown=markdown,
            image_url=urls[0],
            prompt=request.prompt,
            model=model,
            provider=request.provider,
            metadata={
                "all_urls": urls if len(urls) > 1 else None,
                "n": len(urls),
                "edit": True,
                "source_image": request.image_url,
            },
        )


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
        return "gemini-2.5-flash-image"
    else:
        return "gpt-image-1"
