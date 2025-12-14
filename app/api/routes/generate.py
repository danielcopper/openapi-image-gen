import base64
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from app.core.config import settings
from app.core.security import verify_token
from app.schemas.requests import ImageRequest
from app.schemas.responses import ImageResponse
from app.services.gemini_service import get_gemini_service
from app.services.litellm_service import get_litellm_service
from app.services.model_registry import model_registry
from app.services.openai_service import get_openai_service
from app.utils.sse import generate_with_progress

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["Image Generation"])


@router.post(
    "",
    response_model=ImageResponse,
    operation_id="generate_image",
    summary="Generate image",
    description=(
        "Generate an image from a text prompt. "
        "Uses LiteLLM proxy by default for cost tracking, with fallback to direct API calls. "
        "Supports OpenAI DALL-E and Google Gemini models."
    ),
)
async def generate_image(request: ImageRequest, _: None = Depends(verify_token)) -> ImageResponse:
    """
    Generate image with standard JSON response.
    """
    logger.info(
        f"Generate request: provider={request.provider}, model={request.model}, "
        f"aspect_ratio={request.aspect_ratio}"
    )

    # Determine model if not specified
    model = request.model
    if not model:
        model = _get_default_model(request.provider)

    # Get service based on provider
    try:
        service = _get_service(request.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Generate images
    try:
        urls = await service.generate_image(
            prompt=request.prompt,
            model=model,
            aspect_ratio=request.aspect_ratio,
            quality=request.quality,
            n=request.n,
        )
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    # Return first URL (or could return all URLs)
    if not urls:
        raise HTTPException(status_code=500, detail="No images generated")

    # Handle response format
    if request.response_format == "base64":
        # Extract filename from URL and read file
        image_filename = urls[0].split("/")[-1]
        image_path = Path(settings.STORAGE_PATH) / image_filename

        if not image_path.exists():
            raise HTTPException(status_code=500, detail="Generated image file not found")

        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # Determine mime type from extension
        ext = image_path.suffix.lower()
        mime_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
        mime_type = mime_types.get(ext, "image/png")

        return ImageResponse(
            image_base64=image_data,
            mime_type=mime_type,
            prompt=request.prompt,
            model=model,
            provider=request.provider,
            metadata={
                "aspect_ratio": request.aspect_ratio,
                "quality": request.quality,
                "n": len(urls),
            },
        )

    if request.response_format == "markdown":
        # Return ready-to-use markdown with image URL
        markdown = f"![Generated image]({urls[0]})"
        return ImageResponse(
            markdown=markdown,
            image_url=urls[0],
            prompt=request.prompt,
            model=model,
            provider=request.provider,
            metadata={
                "aspect_ratio": request.aspect_ratio,
                "quality": request.quality,
                "n": len(urls),
            },
        )

    return ImageResponse(
        image_url=urls[0],
        prompt=request.prompt,
        model=model,
        provider=request.provider,
        metadata={
            "all_urls": urls if len(urls) > 1 else None,
            "aspect_ratio": request.aspect_ratio,
            "quality": request.quality,
            "n": len(urls),
        },
    )


@router.post(
    "-stream",
    operation_id="generate_image_stream",
    summary="Generate image with SSE streaming",
    description=(
        "Generate an image with real-time progress updates via Server-Sent Events. "
        "Returns a stream of status updates followed by the final result."
    ),
)
async def generate_image_stream(request: ImageRequest, _: None = Depends(verify_token)):
    """
    Generate image with SSE progress streaming.
    """
    logger.info(f"Stream generate request: provider={request.provider}")

    # Determine model if not specified
    model = request.model
    if not model:
        model = _get_default_model(request.provider)

    # Get service based on provider
    try:
        service = _get_service(request.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Return SSE stream
    return StreamingResponse(
        generate_with_progress(
            prompt=request.prompt,
            model=model,
            provider=request.provider,
            service_func=service.generate_image,
            aspect_ratio=request.aspect_ratio,
            quality=request.quality,
            n=request.n,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.post(
    "-preview",
    operation_id="generate_image_preview",
    summary="Generate image with HTML preview",
    description=(
        "Generate an image and return an HTML page with inline preview. "
        "Useful for displaying images directly in web interfaces."
    ),
)
async def generate_image_preview(request: ImageRequest, _: None = Depends(verify_token)):
    """
    Generate image with HTML preview response.
    """
    logger.info(f"Preview generate request: provider={request.provider}")

    # Determine model if not specified
    model = request.model
    if not model:
        model = _get_default_model(request.provider)

    # Get service based on provider
    try:
        service = _get_service(request.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Generate images
    try:
        urls = await service.generate_image(
            prompt=request.prompt,
            model=model,
            aspect_ratio=request.aspect_ratio,
            quality=request.quality,
            n=request.n,
        )
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    if not urls:
        raise HTTPException(status_code=500, detail="No images generated")

    # Build HTML response
    images_html = "\n".join(
        [
            f'<img src="{url}" alt="{request.prompt}" '
            f'style="max-width: 100%; height: auto; border-radius: 8px; margin: 8px 0;" />'
            for url in urls
        ]
    )

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            margin: 0;
            padding: 16px;
            display: flex;
            flex-direction: column;
            align-items: center;
            background: #f5f5f5;
            font-family: system-ui, -apple-system, sans-serif;
        }}
        .container {{
            max-width: 1200px;
            width: 100%;
        }}
        .info {{
            background: white;
            padding: 12px 16px;
            border-radius: 8px;
            margin-bottom: 16px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .info strong {{
            color: #333;
        }}
        .images {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 16px;
        }}
        img {{
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="info">
            <strong>Model:</strong> {model} ({request.provider}) |
            <strong>Aspect Ratio:</strong> {request.aspect_ratio} |
            <strong>Quality:</strong> {request.quality}
        </div>
        <div class="images">
            {images_html}
        </div>
    </div>
</body>
</html>"""

    return HTMLResponse(content=html_content, headers={"Content-Disposition": "inline"})


def _get_service(provider: str):
    """
    Get service instance based on provider.
    """
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


def _get_default_model(provider: str) -> str:
    """
    Get default model for provider based on available models.
    """
    # Check if DEFAULT_MODEL is configured
    if settings.DEFAULT_MODEL:
        return settings.DEFAULT_MODEL

    models = model_registry.get_models()

    # Filter models for this provider
    provider_models = [m for m in models if m.provider == provider or provider == "litellm"]

    if not provider_models:
        # Fallback defaults
        if provider == "openai" or provider == "litellm":
            return "dall-e-3"
        elif provider == "gemini":
            return "gemini-2.0-flash-preview-image-generation"
        else:
            return "dall-e-3"

    # Return first available model
    return provider_models[0].id
