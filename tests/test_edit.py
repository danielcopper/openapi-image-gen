from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def test_model_capabilities_editing_fields():
    """Test that ModelCapabilities has editing fields."""
    from app.schemas.responses import ModelCapabilities

    # Default values
    caps = ModelCapabilities()
    assert caps.supports_editing is False
    assert caps.editing_type is None

    # With editing enabled
    caps = ModelCapabilities(supports_editing=True, editing_type="mask")
    assert caps.supports_editing is True
    assert caps.editing_type == "mask"

    caps = ModelCapabilities(supports_editing=True, editing_type="prompt")
    assert caps.editing_type == "prompt"


def test_known_capabilities_editing():
    """Test that KNOWN_CAPABILITIES includes editing information."""
    from app.services.model_registry import ModelRegistry

    caps = ModelRegistry.KNOWN_CAPABILITIES

    # DALL-E 2 supports mask-based editing
    assert caps["dall-e-2"].supports_editing is True
    assert caps["dall-e-2"].editing_type == "mask"

    # DALL-E 3 does NOT support editing
    assert caps["dall-e-3"].supports_editing is False

    # GPT-Image-1 supports mask-based editing
    assert caps["gpt-image-1"].supports_editing is True
    assert caps["gpt-image-1"].editing_type == "mask"

    # Gemini supports prompt-based editing
    assert caps["gemini-2.0-flash-preview-image-generation"].supports_editing is True
    assert caps["gemini-2.0-flash-preview-image-generation"].editing_type == "prompt"


@pytest.mark.asyncio
async def test_storage_get_image_local(temp_storage):
    """Test getting image from local storage."""
    from app.services.storage_service import StorageService

    with patch("app.services.storage_service.settings") as mock_settings:
        mock_settings.STORAGE_PATH = str(temp_storage)
        mock_settings.IMAGE_BASE_URL = "http://localhost:8000"

        service = StorageService()

        # Save an image first
        test_data = b"test image content"
        url = await service.save_image(test_data, "png")

        # Retrieve the image
        retrieved = await service.get_image(url)
        assert retrieved == test_data


@pytest.mark.asyncio
async def test_storage_get_image_local_relative(temp_storage):
    """Test getting image using relative URL."""
    from app.services.storage_service import StorageService

    with patch("app.services.storage_service.settings") as mock_settings:
        mock_settings.STORAGE_PATH = str(temp_storage)
        mock_settings.IMAGE_BASE_URL = "http://localhost:8000"

        service = StorageService()

        # Save an image first
        test_data = b"test image content"
        url = await service.save_image(test_data, "png")

        # Get filename and use relative URL
        filename = url.split("/")[-1]
        relative_url = f"/images/{filename}"

        retrieved = await service.get_image(relative_url)
        assert retrieved == test_data


@pytest.mark.asyncio
async def test_storage_get_image_not_found(temp_storage):
    """Test error when local image not found."""
    from app.services.storage_service import StorageService

    with patch("app.services.storage_service.settings") as mock_settings:
        mock_settings.STORAGE_PATH = str(temp_storage)
        mock_settings.IMAGE_BASE_URL = "http://localhost:8000"

        service = StorageService()

        with pytest.raises(FileNotFoundError):
            await service.get_image("http://localhost:8000/images/nonexistent.png")


@pytest.mark.asyncio
async def test_storage_get_image_external():
    """Test getting image from external URL."""
    from app.services.storage_service import StorageService

    with patch("app.services.storage_service.settings") as mock_settings:
        mock_settings.STORAGE_PATH = "/tmp/test"
        mock_settings.IMAGE_BASE_URL = "http://localhost:8000"
        mock_settings.openwebui_available = False
        mock_settings.OPENWEBUI_BASE_URL = None

        service = StorageService()

        # Mock httpx client
        mock_response = MagicMock()
        mock_response.content = b"external image data"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.storage_service.httpx.AsyncClient", return_value=mock_client):
            result = await service.get_image("https://example.com/image.png")

            assert result == b"external image data"
            mock_client.get.assert_called_once_with("https://example.com/image.png", headers={})


def test_get_default_edit_model():
    """Test default edit model selection."""
    from app.api.routes.edit import _get_default_edit_model

    with patch("app.api.routes.edit.settings") as mock_settings:
        mock_settings.DEFAULT_MODEL = None

        with patch("app.api.routes.edit.model_registry") as mock_registry:
            # Create mock models with editing support
            mock_model = MagicMock()
            mock_model.id = "gpt-image-1"
            mock_model.provider = "openai"
            mock_model.capabilities.supports_editing = True

            mock_registry.get_models.return_value = [mock_model]
            mock_registry.get_model.return_value = None

            # Should return gpt-image-1 for litellm
            result = _get_default_edit_model("litellm")
            assert result == "gpt-image-1"


def test_get_default_edit_model_fallback():
    """Test fallback when no models in registry."""
    from app.api.routes.edit import _get_default_edit_model

    with patch("app.api.routes.edit.settings") as mock_settings:
        mock_settings.DEFAULT_MODEL = None

        with patch("app.api.routes.edit.model_registry") as mock_registry:
            mock_registry.get_models.return_value = []
            mock_registry.get_model.return_value = None

            # Should return hardcoded defaults
            assert _get_default_edit_model("openai") == "gpt-image-1"
            assert _get_default_edit_model("litellm") == "gpt-image-1"
            assert _get_default_edit_model("gemini") == "gemini-2.0-flash-preview-image-generation"
