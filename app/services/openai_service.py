import base64
import logging
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.services.model_registry import model_registry
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


class OpenAIService:
    """
    Direct OpenAI API integration (fallback).
    """

    ASPECT_RATIO_SIZES = {
        "dall-e-2": {
            "1:1": "1024x1024",
            "16:9": "1024x1024",  # Fallback to square
            "9:16": "1024x1024",
            "4:3": "1024x1024",
            "3:4": "1024x1024",
        },
        "dall-e-3": {
            "1:1": "1024x1024",
            "16:9": "1792x1024",
            "9:16": "1024x1792",
            "4:3": "1792x1024",
            "3:4": "1024x1792",
        },
        "gpt-image-1": {
            "1:1": "1024x1024",
            "16:9": "1536x1024",
            "9:16": "1024x1536",
            "4:3": "1536x1024",
            "3:4": "1024x1536",
        },
    }

    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not configured")

        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate_image(
        self,
        prompt: str,
        model: str,
        aspect_ratio: str = "1:1",
        quality: str = "standard",
        n: int = 1,
    ) -> list[str]:
        """
        Generate images using OpenAI API directly.
        """
        logger.info(f"Generating {n} image(s) with {model} via OpenAI direct")

        # Get size for this model
        size = self._get_size(model, aspect_ratio)

        # Get model capabilities
        model_info = model_registry.get_model(model)

        # Build request parameters
        params: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "response_format": "b64_json",
        }

        # Add quality parameter only if model supports it
        if model_info and model_info.capabilities.supports_quality:
            params["quality"] = quality

        # Adjust n if model doesn't support multiple images
        if model_info and n > model_info.capabilities.max_images:
            logger.warning(
                f"Model {model} supports max {model_info.capabilities.max_images} images"
            )
            params["n"] = model_info.capabilities.max_images

        # Call OpenAI API
        response = self.client.images.generate(**params)

        # Save images and return URLs
        urls = []
        for image_data in response.data:
            image_bytes = base64.b64decode(image_data.b64_json)
            url = await storage_service.save_image(image_bytes, "png")
            urls.append(url)

        logger.info(f"Generated {len(urls)} image(s) successfully")
        return urls

    def _get_size(self, model: str, aspect_ratio: str) -> str:
        """
        Get size for model and aspect ratio.
        """
        model_sizes = self.ASPECT_RATIO_SIZES.get(model)
        if not model_sizes:
            # Default to gpt-image-1 sizes for unknown models
            model_sizes = self.ASPECT_RATIO_SIZES["gpt-image-1"]

        return model_sizes.get(aspect_ratio, "1024x1024")


def get_openai_service() -> OpenAIService:
    """
    Factory function to get OpenAI service instance.
    """
    return OpenAIService()
