import base64
from pathlib import Path
from unittest.mock import patch

import pytest

from app.utils.image import (
    build_openwebui_html_response,
    extract_safe_filename,
    get_mime_type,
    read_image_as_base64,
)


class TestGetMimeType:
    def test_png(self):
        assert get_mime_type(Path("image.png")) == "image/png"

    def test_jpg(self):
        assert get_mime_type(Path("image.jpg")) == "image/jpeg"

    def test_jpeg(self):
        assert get_mime_type(Path("image.jpeg")) == "image/jpeg"

    def test_webp(self):
        assert get_mime_type(Path("image.webp")) == "image/webp"

    def test_unknown_defaults_to_png(self):
        assert get_mime_type(Path("image.bmp")) == "image/png"

    def test_case_insensitive(self):
        assert get_mime_type(Path("image.PNG")) == "image/png"


class TestExtractSafeFilename:
    def test_valid_uuid_filename(self):
        url = "http://localhost:8000/images/550e8400-e29b-41d4-a716-446655440000.png"
        assert extract_safe_filename(url) == "550e8400-e29b-41d4-a716-446655440000.png"

    def test_valid_uuid_with_query_params(self):
        url = "http://localhost:8000/images/550e8400-e29b-41d4-a716-446655440000.webp?token=abc"
        assert extract_safe_filename(url) == "550e8400-e29b-41d4-a716-446655440000.webp"

    def test_rejects_non_uuid_filename(self):
        with pytest.raises(ValueError, match="Invalid image filename"):
            extract_safe_filename("http://example.com/images/../../etc/passwd")

    def test_rejects_plain_name(self):
        with pytest.raises(ValueError, match="Invalid image filename"):
            extract_safe_filename("http://example.com/images/malicious.png")

    def test_rejects_empty_path(self):
        with pytest.raises(ValueError, match="Invalid image filename"):
            extract_safe_filename("http://example.com/")


class TestReadImageAsBase64:
    @pytest.mark.asyncio
    async def test_reads_and_encodes(self, temp_storage):
        test_data = b"fake image content"
        image_file = temp_storage / "test.png"
        image_file.write_bytes(test_data)

        with patch("app.utils.image.settings") as mock_settings:
            mock_settings.STORAGE_PATH = str(temp_storage)
            mock_settings.SAVE_IMAGES_LOCALLY = True

            data, mime = await read_image_as_base64("http://host/images/test.png", cleanup=True)

        assert data == base64.b64encode(test_data).decode("utf-8")
        assert mime == "image/png"
        assert image_file.exists()  # not cleaned up because SAVE_IMAGES_LOCALLY=True

    @pytest.mark.asyncio
    async def test_cleanup_when_not_saving(self, temp_storage):
        image_file = temp_storage / "test.png"
        image_file.write_bytes(b"data")

        with patch("app.utils.image.settings") as mock_settings:
            mock_settings.STORAGE_PATH = str(temp_storage)
            mock_settings.SAVE_IMAGES_LOCALLY = False

            await read_image_as_base64("http://host/images/test.png", cleanup=True)

        assert not image_file.exists()

    @pytest.mark.asyncio
    async def test_no_cleanup_when_flag_false(self, temp_storage):
        image_file = temp_storage / "test.png"
        image_file.write_bytes(b"data")

        with patch("app.utils.image.settings") as mock_settings:
            mock_settings.STORAGE_PATH = str(temp_storage)
            mock_settings.SAVE_IMAGES_LOCALLY = False

            await read_image_as_base64("http://host/images/test.png", cleanup=False)

        assert image_file.exists()  # preserved because cleanup=False

    @pytest.mark.asyncio
    async def test_file_not_found(self, temp_storage):
        with patch("app.utils.image.settings") as mock_settings:
            mock_settings.STORAGE_PATH = str(temp_storage)

            with pytest.raises(FileNotFoundError):
                await read_image_as_base64("http://host/images/missing.png")


class TestBuildOpenwebuiHtmlResponse:
    def test_returns_html_with_image(self):
        response = build_openwebui_html_response("abc123", "image/png")
        body = response.body.decode("utf-8")
        assert "data:image/png;base64,abc123" in body
        assert "<img" in body
        assert response.headers["content-disposition"] == "inline"

    def test_uses_provided_mime_type(self):
        response = build_openwebui_html_response("data", "image/webp")
        body = response.body.decode("utf-8")
        assert "data:image/webp;base64,data" in body
