import ipaddress
import logging
import socket
import uuid
from pathlib import Path
from urllib.parse import urlparse

import aiofiles
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """
    Handles image storage — local filesystem and Open WebUI file upload.
    """

    def __init__(self):
        self.storage_path = Path(settings.STORAGE_PATH)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    async def save_image(self, image_data: bytes, extension: str = "png") -> str:
        """
        Save image bytes to the best available storage.

        When OPENWEBUI_MODE is enabled and OWUI upload is configured, uploads
        to Open WebUI's file storage and returns an OWUI file URL. Falls back
        to local storage on failure or when OWUI upload is not configured.

        Args:
            image_data: Raw image bytes
            extension: File extension (png, jpg, webp)

        Returns:
            Public URL to access the image (OWUI URL or local URL)
        """
        # Try OWUI upload when in OWUI mode with upload configured
        if settings.OPENWEBUI_MODE and settings.openwebui_upload_available:
            try:
                owui_url = await self._upload_to_openwebui(image_data, extension)
                # Also save locally if configured
                if settings.SAVE_IMAGES_LOCALLY:
                    await self._save_locally(image_data, extension)
                return owui_url
            except Exception as e:
                logger.warning(f"OWUI upload failed, falling back to local storage: {e}")

        # Local storage
        return await self._save_locally(image_data, extension)

    async def _save_locally(self, image_data: bytes, extension: str = "png") -> str:
        """Save image bytes to local filesystem."""
        filename = f"{uuid.uuid4()}.{extension}"
        filepath = self.storage_path / filename

        async with aiofiles.open(filepath, "wb") as f:
            await f.write(image_data)

        return f"{settings.IMAGE_BASE_URL.rstrip('/')}/images/{filename}"

    async def _upload_to_openwebui(self, image_data: bytes, extension: str = "png") -> str:
        """
        Upload image to Open WebUI's file storage.

        Returns:
            OWUI file URL (e.g. http://open-webui:3000/api/v1/files/{id}/content)
        """
        filename = f"{uuid.uuid4()}.{extension}"
        mime_type = f"image/{extension}"
        base_url = settings.OPENWEBUI_BASE_URL.rstrip("/")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/api/v1/files/",
                files={"file": (filename, image_data, mime_type)},
                headers={"Authorization": f"Bearer {settings.OPENWEBUI_API_KEY}"},
            )
            response.raise_for_status()
            file_id = response.json()["id"]
            logger.info(f"Uploaded image to OWUI: {file_id}")
            return f"{base_url}/api/v1/files/{file_id}/content"

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

        # External URL - validate and fetch via HTTP
        self._validate_external_url(url)
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    @staticmethod
    def _validate_external_url(url: str) -> None:
        """Validate that an external URL doesn't point to internal/private networks."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"URL scheme must be http or https, got: {parsed.scheme}")

        hostname = parsed.hostname
        if not hostname:
            raise ValueError("URL must include a hostname")

        # Resolve hostname and check all returned IPs
        try:
            addrinfo = socket.getaddrinfo(hostname, None)
        except socket.gaierror as e:
            raise ValueError(f"Cannot resolve hostname: {hostname}") from e

        for _family, _, _, _, sockaddr in addrinfo:
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ValueError(f"URL resolves to blocked address: {ip}")


storage_service = StorageService()
