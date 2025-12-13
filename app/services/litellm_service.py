import base64
import logging
from typing import List, Dict, Any
from openai import OpenAI

from app.core.config import settings
from app.services.storage_service import storage_service
from app.services.model_registry import model_registry

logger = logging.getLogger(__name__)


class LiteLLMService:
    """
    Primary image generation service using LiteLLM proxy.
    Uses OpenAI-compatible API for unified access to all providers.
    """

    # Aspect ratio to size mapping for OpenAI-compatible models
    ASPECT_RATIO_SIZES = {
        "1:1": "1024x1024",
        "16:9": "1792x1024",
        "9:16": "1024x1792",
        "4:3": "1792x1024",
        "3:4": "1024x1792",
    }

    def __init__(self):
        if not settings.LITELLM_BASE_URL:
            raise ValueError("LITELLM_BASE_URL not configured")

        self.client = OpenAI(
            base_url=settings.LITELLM_BASE_URL,
            api_key=settings.LITELLM_API_KEY or "dummy"
        )

    async def generate_image(
        self,
        prompt: str,
        model: str,
        aspect_ratio: str = "1:1",
        quality: str = "standard",
        n: int = 1
    ) -> List[str]:
        """
        Generate images using LiteLLM proxy.

        Args:
            prompt: Image description
            model: Model ID
            aspect_ratio: Image aspect ratio
            quality: Image quality (standard/hd)
            n: Number of images

        Returns:
            List of image URLs
        """
        logger.info(f"Generating {n} image(s) with {model} via LiteLLM")

        # Get model capabilities to adjust parameters
        model_info = model_registry.get_model(model)
        size = self._get_size(aspect_ratio)

        # Build request parameters
        params: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "response_format": "b64_json"
        }

        # Add quality parameter only if model supports it
        if model_info and model_info.capabilities.supports_quality:
            params["quality"] = quality

        # Adjust n if model doesn't support multiple images
        if model_info and n > model_info.capabilities.max_images:
            logger.warning(
                f"Model {model} supports max {model_info.capabilities.max_images} images, "
                f"adjusting from {n}"
            )
            params["n"] = model_info.capabilities.max_images

        # Call LiteLLM proxy
        response = self.client.images.generate(**params)

        # Save images and return URLs
        urls = []
        for image_data in response.data:
            image_bytes = base64.b64decode(image_data.b64_json)
            url = await storage_service.save_image(image_bytes, "png")
            urls.append(url)

        logger.info(f"Generated {len(urls)} image(s) successfully")
        return urls

    def _get_size(self, aspect_ratio: str) -> str:
        """
        Convert aspect ratio to OpenAI size format.
        """
        return self.ASPECT_RATIO_SIZES.get(aspect_ratio, "1024x1024")


def get_litellm_service() -> LiteLLMService:
    """
    Factory function to get LiteLLM service instance.
    """
    return LiteLLMService()
