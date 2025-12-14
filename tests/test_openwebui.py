from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_openwebui_available_property():
    """Test openwebui_available property."""
    from app.core.config import Settings

    # Not available when URL missing
    settings = Settings(OPENWEBUI_API_URL=None, OPENWEBUI_API_KEY="key")
    assert settings.openwebui_available is False

    # Not available when key missing
    settings = Settings(OPENWEBUI_API_URL="http://localhost", OPENWEBUI_API_KEY=None)
    assert settings.openwebui_available is False

    # Available when both set
    settings = Settings(
        OPENWEBUI_API_URL="http://localhost", OPENWEBUI_API_KEY="key"
    )
    assert settings.openwebui_available is True


@pytest.mark.asyncio
async def test_openwebui_service_upload():
    """Test Open WebUI upload service."""
    from app.services.openwebui_service import OpenWebUIService

    with patch("app.services.openwebui_service.settings") as mock_settings:
        mock_settings.OPENWEBUI_API_URL = "https://chat.example.com"
        mock_settings.OPENWEBUI_API_KEY = "test-key"

        service = OpenWebUIService()

        # Mock httpx client
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "file-123"}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.services.openwebui_service.httpx.AsyncClient",
            return_value=mock_client,
        ):
            url = await service.upload_image(b"test image data", "test.png")

            assert url == "https://chat.example.com/api/v1/files/file-123/content"
            mock_client.post.assert_called_once()

            # Verify the request
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://chat.example.com/api/v1/files/"
            assert "Authorization" in call_args[1]["headers"]
            assert call_args[1]["headers"]["Authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_openwebui_service_upload_no_file_id():
    """Test Open WebUI upload when response has no file ID."""
    from app.services.openwebui_service import OpenWebUIService

    with patch("app.services.openwebui_service.settings") as mock_settings:
        mock_settings.OPENWEBUI_API_URL = "https://chat.example.com"
        mock_settings.OPENWEBUI_API_KEY = "test-key"

        service = OpenWebUIService()

        mock_response = MagicMock()
        mock_response.json.return_value = {}  # No file ID
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch(
            "app.services.openwebui_service.httpx.AsyncClient",
            return_value=mock_client,
        ):
            with pytest.raises(ValueError, match="No file ID"):
                await service.upload_image(b"test", "test.png")


@pytest.mark.asyncio
async def test_storage_with_openwebui(temp_storage):
    """Test storage service uploads to Open WebUI when configured."""
    from app.services.storage_service import StorageService

    with patch("app.services.storage_service.settings") as mock_settings:
        mock_settings.STORAGE_PATH = str(temp_storage)
        mock_settings.IMAGE_BASE_URL = "http://localhost:8000"
        mock_settings.openwebui_available = True

        service = StorageService()

        # Mock the Open WebUI service
        mock_webui_service = MagicMock()
        mock_webui_service.upload_image = AsyncMock(
            return_value="https://chat.example.com/api/v1/files/123/content"
        )

        with patch(
            "app.services.openwebui_service.get_openwebui_service",
            return_value=mock_webui_service,
        ):
            url = await service.save_image(b"test image", "png")

            # Should return Open WebUI URL
            assert url == "https://chat.example.com/api/v1/files/123/content"
            mock_webui_service.upload_image.assert_called_once()


@pytest.mark.asyncio
async def test_storage_fallback_on_openwebui_error(temp_storage):
    """Test storage falls back to local URL when Open WebUI upload fails."""
    from app.services.storage_service import StorageService

    with patch("app.services.storage_service.settings") as mock_settings:
        mock_settings.STORAGE_PATH = str(temp_storage)
        mock_settings.IMAGE_BASE_URL = "http://localhost:8000"
        mock_settings.openwebui_available = True

        service = StorageService()

        # Mock the Open WebUI service to fail
        mock_webui_service = MagicMock()
        mock_webui_service.upload_image = AsyncMock(
            side_effect=Exception("Upload failed")
        )

        with patch(
            "app.services.openwebui_service.get_openwebui_service",
            return_value=mock_webui_service,
        ):
            url = await service.save_image(b"test image", "png")

            # Should fall back to local URL
            assert url.startswith("http://localhost:8000/images/")
            assert url.endswith(".png")


@pytest.mark.asyncio
async def test_storage_without_openwebui(temp_storage):
    """Test storage service uses local URL when Open WebUI not configured."""
    from app.services.storage_service import StorageService

    with patch("app.services.storage_service.settings") as mock_settings:
        mock_settings.STORAGE_PATH = str(temp_storage)
        mock_settings.IMAGE_BASE_URL = "http://localhost:8000"
        mock_settings.openwebui_available = False

        service = StorageService()
        url = await service.save_image(b"test image", "png")

        # Should return local URL
        assert url.startswith("http://localhost:8000/images/")
