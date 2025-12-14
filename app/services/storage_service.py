import logging
import uuid
from pathlib import Path

import aiofiles
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    Handles local file storage for generated images.
    Optionally uploads to Open WebUI for better accessibility.
    """

    def __init__(self):
        self.storage_path = Path(settings.STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def save_image(self, image_data: bytes, extension: str = "png") -> str:
        """
        Save image bytes to local storage and/or upload to Open WebUI.

        Args:
            image_data: Raw image bytes
            extension: File extension (png, jpg, webp)

        Returns:
            Public URL to access the image (Open WebUI URL if configured, else local)
        """
        filename = f"{uuid.uuid4()}.{extension}"
        local_url = f"{settings.IMAGE_BASE_URL.rstrip('/')}/images/{filename}"

        # Save locally if configured
        if settings.SAVE_IMAGES_LOCALLY:
            filepath = self.storage_path / filename
            async with aiofiles.open(filepath, "wb") as f:
                await f.write(image_data)

        # Upload to Open WebUI if configured
        if settings.openwebui_available:
            try:
                from app.services.openwebui_service import get_openwebui_service

                webui_service = get_openwebui_service()
                return await webui_service.upload_image(image_data, filename)
            except Exception as e:
                logger.warning(f"Open WebUI upload failed: {e}")
                if settings.SAVE_IMAGES_LOCALLY:
                    return local_url
                raise

        return local_url

    async def get_image(self, url: str) -> bytes:
        """
        Retrieve image bytes from URL or local storage.

        Args:
            url: URL to the image (local or external)

        Returns:
            Raw image bytes

        Raises:
            FileNotFoundError: If local file doesn't exist
            httpx.HTTPError: If external URL fetch fails
        """
        base_url = settings.IMAGE_BASE_URL.rstrip("/")

        # Check if this is a local image (served by this API)
        if url.startswith(base_url) or url.startswith("/images/"):
            # Extract filename from URL
            filename = url.split("/")[-1]
            filepath = self.storage_path / filename

            if not filepath.exists():
                raise FileNotFoundError(f"Image not found: {filename}")

            async with aiofiles.open(filepath, "rb") as f:
                return await f.read()

        # External URL - fetch via HTTP
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content


storage_service = StorageService()
