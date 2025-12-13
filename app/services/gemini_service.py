import logging
from typing import List
from google import genai
from google.genai import types

from app.core.config import settings
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


class GeminiService:
    """
    Direct Google Gemini API integration (fallback).
    """

    ASPECT_RATIO_MAP = {
        "1:1": "1:1",
        "16:9": "16:9",
        "9:16": "9:16",
        "4:3": "4:3",
        "3:4": "3:4",
    }

    def __init__(self):
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")

        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def generate_image(
        self,
        prompt: str,
        model: str,
        aspect_ratio: str = "1:1",
        quality: str = "standard",  # Not used for Gemini
        n: int = 1
    ) -> List[str]:
        """
        Generate images using Google Gemini API directly.
        """
        logger.info(f"Generating {n} image(s) with {model} via Gemini direct")

        gemini_aspect_ratio = self.ASPECT_RATIO_MAP.get(aspect_ratio, "1:1")

        urls = []

        # Gemini generates one image per request
        for i in range(n):
            logger.debug(f"Generating image {i+1}/{n}")

            response = self.client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=gemini_aspect_ratio
                    ),
                ),
            )

            # Extract image from response
            for part in response.candidates[0].content.parts:
                if hasattr(part, "inline_data") and part.inline_data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type
                    extension = mime_type.split("/")[-1] if "/" in mime_type else "png"

                    url = await storage_service.save_image(image_bytes, extension)
                    urls.append(url)

        logger.info(f"Generated {len(urls)} image(s) successfully")
        return urls


def get_gemini_service() -> GeminiService:
    """
    Factory function to get Gemini service instance.
    """
    return GeminiService()
