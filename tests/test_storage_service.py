from unittest.mock import patch

import pytest

from app.services.storage_service import StorageService


@pytest.mark.asyncio
async def test_save_image(temp_storage):
    """
    Test saving image to storage.
    """
    # Create service with temp storage
    with patch("app.services.storage_service.settings") as mock_settings:
        mock_settings.STORAGE_PATH = str(temp_storage)
        mock_settings.IMAGE_BASE_URL = "http://localhost:8000"

        service = StorageService()

        # Save test image
        image_data = b"test image data"
        url = await service.save_image(image_data, "png")

        # Verify URL format
        assert url.startswith("http://localhost:8000/images/")
        assert url.endswith(".png")

        # Verify file was created
        filename = url.split("/")[-1]
        filepath = temp_storage / filename
        assert filepath.exists()

        # Verify file content
        with open(filepath, "rb") as f:
            assert f.read() == image_data


@pytest.mark.asyncio
async def test_save_image_different_extensions(temp_storage):
    """
    Test saving images with different extensions.
    """
    with patch("app.services.storage_service.settings") as mock_settings:
        mock_settings.STORAGE_PATH = str(temp_storage)
        mock_settings.IMAGE_BASE_URL = "http://localhost:8000"

        service = StorageService()

        extensions = ["png", "jpg", "webp"]
        for ext in extensions:
            url = await service.save_image(b"test", ext)
            assert url.endswith(f".{ext}")

            filename = url.split("/")[-1]
            assert (temp_storage / filename).exists()


@pytest.mark.asyncio
async def test_save_image_with_custom_base_url(temp_storage):
    """
    Test that IMAGE_BASE_URL is used correctly.
    """
    with patch("app.services.storage_service.settings") as mock_settings:
        mock_settings.STORAGE_PATH = str(temp_storage)
        mock_settings.IMAGE_BASE_URL = "http://image-api:8000"

        service = StorageService()
        url = await service.save_image(b"test", "png")

        assert url.startswith("http://image-api:8000/images/")
