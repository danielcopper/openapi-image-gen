import uuid
from pathlib import Path
import aiofiles

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

        if settings.BASE_URL:
            return f"{settings.BASE_URL.rstrip('/')}{relative_url}"
        return relative_url


storage_service = StorageService()
