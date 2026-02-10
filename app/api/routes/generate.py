import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse

from app.api.dependencies import get_service
from app.core.config import settings
from app.core.security import verify_token
from app.schemas.requests import ImageRequest
from app.schemas.responses import ImageResponse
from app.services.model_registry import model_registry
from app.utils.image import build_openwebui_html_response, read_image_as_base64
from app.utils.sse import generate_with_progress

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generate", tags=["Image Generation"])


@router.post(
    "",
    response_model=None,
    operation_id="generate_image",
    summary="Generate image",
    description=(
        "Generate an image from a text prompt. "
        "Uses LiteLLM proxy by default for cost tracking, with fallback to direct API calls. "
        "Supports OpenAI DALL-E and Google Gemini models. "
        "Response format depends on OPENWEBUI_MODE and response_format parameter."
    ),
)
async def generate_image(request: ImageRequest, _: None = Depends(verify_token)):
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
        service = get_service(request.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

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
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}") from None

    # Return first URL (or could return all URLs)
    if not urls:
        raise HTTPException(status_code=500, detail="No images generated")

    # OpenWebUI mode: return HTML with embedded image for iframe display
    if settings.OPENWEBUI_MODE:
        try:
            image_data, mime_type = await read_image_as_base64(urls[0])
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Generated image file not found") from None
        return build_openwebui_html_response(image_data, mime_type)

    # Handle response format
    if request.response_format == "base64":
        try:
            image_data, mime_type = await read_image_as_base64(urls[0])
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail="Generated image file not found") from None

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
        if settings.MARKDOWN_EMBED_IMAGES:
            try:
                image_data, mime_type = await read_image_as_base64(urls[0])
            except FileNotFoundError:
                raise HTTPException(
                    status_code=500, detail="Generated image file not found"
                ) from None

            markdown = f"![Generated image](data:{mime_type};base64,{image_data})"
            return ImageResponse(
                markdown=markdown,
                prompt=request.prompt,
                model=model,
                provider=request.provider,
                metadata={
                    "aspect_ratio": request.aspect_ratio,
                    "quality": request.quality,
                    "n": len(urls),
                },
            )
        else:
            # Return markdown with image URL
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
        service = get_service(request.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

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
        service = get_service(request.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from None

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
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}") from None

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
            return "gpt-image-1"
        elif provider == "gemini":
            return "gemini-2.5-flash-image"
        else:
            return "gpt-image-1"

    # Return first available model
    return provider_models[0].id
