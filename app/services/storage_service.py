import uuid
from pathlib import Path

import aiofiles
import httpx

from app.core.config import settings


class StorageService:
    """
    Handles local file storage for generated images.
    """

    def __init__(self):
        self.storage_path = Path(settings.STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def save_image(self, image_data: bytes, extension: str = "png") -> str:
        """
        Save image bytes to local storage and return public URL.

        Args:
            image_data: Raw image bytes
            extension: File extension (png, jpg, webp)

        Returns:
            Public URL to access the image
        """
        filename = f"{uuid.uuid4()}.{extension}"
        filepath = self.storage_path / filename

        async with aiofiles.open(filepath, "wb") as f:
            await f.write(image_data)

        relative_url = f"/images/{filename}"

        return f"{settings.IMAGE_BASE_URL.rstrip('/')}{relative_url}"

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
