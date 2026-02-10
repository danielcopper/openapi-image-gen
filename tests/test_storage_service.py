from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.storage_service import StorageService


@pytest.mark.asyncio
async def test_save_image(temp_storage):
    """Test saving image to storage."""
    with patch("app.services.storage_service.settings") as mock_settings:
        mock_settings.STORAGE_PATH = str(temp_storage)
        mock_settings.IMAGE_BASE_URL = "http://localhost:8000"
        mock_settings.OPENWEBUI_MODE = False

        service = StorageService()
        image_data = b"test image data"
        url = await service.save_image(image_data, "png")

        assert url.startswith("http://localhost:8000/images/")
        assert url.endswith(".png")

        filename = url.split("/")[-1]
        filepath = temp_storage / filename
        assert filepath.exists()

        with open(filepath, "rb") as f:
            assert f.read() == image_data


@pytest.mark.asyncio
async def test_save_image_different_extensions(temp_storage):
    """Test saving images with different extensions."""
    with patch("app.services.storage_service.settings") as mock_settings:
        mock_settings.STORAGE_PATH = str(temp_storage)
        mock_settings.IMAGE_BASE_URL = "http://localhost:8000"
        mock_settings.OPENWEBUI_MODE = False

        service = StorageService()

        extensions = ["png", "jpg", "webp"]
        for ext in extensions:
            url = await service.save_image(b"test", ext)
            assert url.endswith(f".{ext}")

            filename = url.split("/")[-1]
            assert (temp_storage / filename).exists()


@pytest.mark.asyncio
async def test_save_image_with_custom_base_url(temp_storage):
    """Test that IMAGE_BASE_URL is used correctly."""
    with patch("app.services.storage_service.settings") as mock_settings:
        mock_settings.STORAGE_PATH = str(temp_storage)
        mock_settings.IMAGE_BASE_URL = "http://image-api:8000"
        mock_settings.OPENWEBUI_MODE = False

        service = StorageService()
        url = await service.save_image(b"test", "png")

        assert url.startswith("http://image-api:8000/images/")


class TestUploadToOpenWebUI:
    """Tests for _upload_to_openwebui."""

    @pytest.fixture
    def service(self, temp_storage):
        with patch("app.services.storage_service.settings") as mock_settings:
            mock_settings.STORAGE_PATH = str(temp_storage)
            mock_settings.IMAGE_BASE_URL = "http://localhost:8000"
            yield StorageService()

    @pytest.mark.asyncio
    async def test_upload_success(self, service):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "abc-123"}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.storage_service.settings") as mock_settings:
            mock_settings.OPENWEBUI_BASE_URL = "http://open-webui:3000"
            mock_settings.OPENWEBUI_API_KEY = "test-key"

            with patch("app.services.storage_service.httpx.AsyncClient", return_value=mock_client):
                url = await service._upload_to_openwebui(b"image-data", "png")

        assert url == "http://open-webui:3000/api/v1/files/abc-123/content"
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert "/api/v1/files/" in call_kwargs.args[0]
        assert call_kwargs.kwargs["headers"]["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_upload_strips_trailing_slash(self, service):
        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "def-456"}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.storage_service.settings") as mock_settings:
            mock_settings.OPENWEBUI_BASE_URL = "http://open-webui:3000/"
            mock_settings.OPENWEBUI_API_KEY = "key"

            with patch("app.services.storage_service.httpx.AsyncClient", return_value=mock_client):
                url = await service._upload_to_openwebui(b"data", "png")

        assert url == "http://open-webui:3000/api/v1/files/def-456/content"


class TestSaveImageRouting:
    """Tests for save_image routing between OWUI upload and local storage."""

    @pytest.fixture
    def service(self, temp_storage):
        with patch("app.services.storage_service.settings") as mock_settings:
            mock_settings.STORAGE_PATH = str(temp_storage)
            mock_settings.IMAGE_BASE_URL = "http://localhost:8000"
            yield StorageService()

    @pytest.mark.asyncio
    async def test_owui_upload_when_configured(self, service):
        with patch("app.services.storage_service.settings") as mock_settings:
            mock_settings.OPENWEBUI_MODE = True
            mock_settings.openwebui_upload_available = True
            mock_settings.SAVE_IMAGES_LOCALLY = False

            with patch.object(
                service, "_upload_to_openwebui", new_callable=AsyncMock
            ) as mock_upload:
                mock_upload.return_value = "http://owui/api/v1/files/123/content"

                url = await service.save_image(b"image-data", "png")

        assert url == "http://owui/api/v1/files/123/content"
        mock_upload.assert_called_once_with(b"image-data", "png")

    @pytest.mark.asyncio
    async def test_owui_upload_also_saves_locally(self, service, temp_storage):
        with patch("app.services.storage_service.settings") as mock_settings:
            mock_settings.OPENWEBUI_MODE = True
            mock_settings.openwebui_upload_available = True
            mock_settings.SAVE_IMAGES_LOCALLY = True
            mock_settings.IMAGE_BASE_URL = "http://localhost:8000"

            with patch.object(
                service, "_upload_to_openwebui", new_callable=AsyncMock
            ) as mock_upload:
                mock_upload.return_value = "http://owui/api/v1/files/123/content"

                url = await service.save_image(b"image-data", "png")

        # Returns OWUI URL
        assert url == "http://owui/api/v1/files/123/content"
        # But also saved locally
        local_files = list(temp_storage.glob("*.png"))
        assert len(local_files) == 1

    @pytest.mark.asyncio
    async def test_fallback_to_local_on_owui_failure(self, service, temp_storage):
        with patch("app.services.storage_service.settings") as mock_settings:
            mock_settings.OPENWEBUI_MODE = True
            mock_settings.openwebui_upload_available = True
            mock_settings.SAVE_IMAGES_LOCALLY = True
            mock_settings.IMAGE_BASE_URL = "http://localhost:8000"

            with patch.object(
                service, "_upload_to_openwebui", new_callable=AsyncMock
            ) as mock_upload:
                mock_upload.side_effect = Exception("OWUI unreachable")

                url = await service.save_image(b"image-data", "png")

        # Falls back to local URL
        assert url.startswith("http://localhost:8000/images/")
        assert url.endswith(".png")

    @pytest.mark.asyncio
    async def test_local_only_when_owui_not_configured(self, service, temp_storage):
        with patch("app.services.storage_service.settings") as mock_settings:
            mock_settings.OPENWEBUI_MODE = True
            mock_settings.openwebui_upload_available = False
            mock_settings.SAVE_IMAGES_LOCALLY = True
            mock_settings.IMAGE_BASE_URL = "http://localhost:8000"

            url = await service.save_image(b"image-data", "png")

        assert url.startswith("http://localhost:8000/images/")

    @pytest.mark.asyncio
    async def test_local_only_when_owui_mode_off(self, service, temp_storage):
        with patch("app.services.storage_service.settings") as mock_settings:
            mock_settings.OPENWEBUI_MODE = False
            mock_settings.openwebui_upload_available = True
            mock_settings.SAVE_IMAGES_LOCALLY = True
            mock_settings.IMAGE_BASE_URL = "http://localhost:8000"

            url = await service.save_image(b"image-data", "png")

        assert url.startswith("http://localhost:8000/images/")
