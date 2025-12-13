import json
import logging
from typing import AsyncGenerator, Callable, Any, Awaitable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SSEEvent:
    """
    Server-Sent Event message.
    """
    event: str
    data: dict

    def format(self) -> str:
        """Format as SSE message."""
        return f"event: {self.event}\ndata: {json.dumps(self.data)}\n\n"


async def generate_with_progress(
    prompt: str,
    model: str,
    provider: str,
    service_func: Callable[..., Awaitable[Any]],
    **kwargs
) -> AsyncGenerator[str, None]:
    """
    Generic SSE generator for image generation with progress updates.

    Args:
        prompt: Image prompt
        model: Model ID
        provider: Provider name
        service_func: Async function that performs the actual generation
        **kwargs: Additional arguments to pass to service_func

    Yields:
        SSE formatted messages
    """
    try:
        # Status: Queued
        yield SSEEvent("status", {
            "status": "queued",
            "progress": 0,
            "message": f"Request queued for {model}"
        }).format()

        # Status: Starting generation
        yield SSEEvent("status", {
            "status": "generating",
            "progress": 20,
            "message": f"Starting generation with {provider}/{model}"
        }).format()

        # Call actual generation service
        logger.info(f"Calling generation service for {model}")
        urls = await service_func(
            prompt=prompt,
            model=model,
            **kwargs
        )

        # Status: Processing
        yield SSEEvent("status", {
            "status": "processing",
            "progress": 80,
            "message": "Processing and saving images"
        }).format()

        # Status: Complete
        yield SSEEvent("complete", {
            "status": "complete",
            "progress": 100,
            "message": f"Successfully generated {len(urls)} image(s)",
            "image_urls": urls,
            "model": model,
            "provider": provider
        }).format()

    except Exception as e:
        logger.error(f"Generation error: {e}", exc_info=True)
        yield SSEEvent("error", {
            "status": "error",
            "message": str(e)
        }).format()
