from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.litellm_service import LiteLLMService


class TestIsGeminiModel:
    """Tests for _is_gemini_model helper."""

    @pytest.fixture
    def service(self):
        with patch("app.services.litellm_service.settings") as mock_settings:
            mock_settings.LITELLM_BASE_URL = "http://localhost:4000"
            mock_settings.LITELLM_API_KEY = "test-key"
            return LiteLLMService()

    def test_gemini_model(self, service):
        assert service._is_gemini_model("gemini-2.0-flash-preview-image-generation") is True
        assert service._is_gemini_model("gemini/gemini-2.0-flash-exp") is True
        assert service._is_gemini_model("GEMINI-MODEL") is True

    def test_imagen_model(self, service):
        assert service._is_gemini_model("imagen-3.0-generate-002") is True
        assert service._is_gemini_model("vertex/imagen-3") is True

    def test_non_gemini_model(self, service):
        assert service._is_gemini_model("dall-e-3") is False
        assert service._is_gemini_model("gpt-image-1") is False
        assert service._is_gemini_model("stable-diffusion") is False


class TestNormalizeGeminiModel:
    """Tests for _normalize_gemini_model helper."""

    @pytest.fixture
    def service(self):
        with patch("app.services.litellm_service.settings") as mock_settings:
            mock_settings.LITELLM_BASE_URL = "http://localhost:4000"
            mock_settings.LITELLM_API_KEY = "test-key"
            return LiteLLMService()

    def test_removes_gemini_prefix(self, service):
        assert service._normalize_gemini_model("gemini/gemini-2.0-flash-exp") == "gemini-2.0-flash-exp"

    def test_keeps_model_without_prefix(self, service):
        assert service._normalize_gemini_model("gemini-2.0-flash-exp") == "gemini-2.0-flash-exp"

    def test_keeps_other_prefixes(self, service):
        assert service._normalize_gemini_model("vertex/imagen-3") == "vertex/imagen-3"


class TestShouldUseDirectProvider:
    """Tests for _should_use_direct_provider logic."""

    @pytest.fixture
    def service(self):
        with patch("app.services.litellm_service.settings") as mock_settings:
            mock_settings.LITELLM_BASE_URL = "http://localhost:4000"
            mock_settings.LITELLM_API_KEY = "test-key"
            return LiteLLMService()

    def test_disabled_when_fallback_false(self, service):
        with patch("app.services.litellm_service.settings") as mock_settings:
            mock_settings.DIRECT_PROVIDER_FALLBACK = False
            assert service._should_use_direct_provider("gemini/model", "16:9") is False

    def test_disabled_for_square_aspect_ratio(self, service):
        with patch("app.services.litellm_service.settings") as mock_settings:
            mock_settings.DIRECT_PROVIDER_FALLBACK = True
            mock_settings.gemini_available = True
            assert service._should_use_direct_provider("gemini/model", "1:1") is False

    def test_enabled_for_gemini_non_square(self, service):
        with patch("app.services.litellm_service.settings") as mock_settings:
            mock_settings.DIRECT_PROVIDER_FALLBACK = True
            mock_settings.gemini_available = True
            assert service._should_use_direct_provider("gemini/model", "16:9") is True
            assert service._should_use_direct_provider("gemini/model", "9:16") is True
            assert service._should_use_direct_provider("imagen-3", "4:3") is True

    def test_disabled_when_gemini_key_missing(self, service, caplog):
        with patch("app.services.litellm_service.settings") as mock_settings:
            mock_settings.DIRECT_PROVIDER_FALLBACK = True
            mock_settings.gemini_available = False
            assert service._should_use_direct_provider("gemini/model", "16:9") is False
            assert "GEMINI_API_KEY not set" in caplog.text

    def test_disabled_for_non_gemini_models(self, service):
        with patch("app.services.litellm_service.settings") as mock_settings:
            mock_settings.DIRECT_PROVIDER_FALLBACK = True
            mock_settings.gemini_available = True
            assert service._should_use_direct_provider("dall-e-3", "16:9") is False
            assert service._should_use_direct_provider("gpt-image-1", "9:16") is False


class TestGenerateImageWithFallback:
    """Tests for generate_image with direct provider fallback."""

    @pytest.fixture
    def service(self):
        with patch("app.services.litellm_service.settings") as mock_settings:
            mock_settings.LITELLM_BASE_URL = "http://localhost:4000"
            mock_settings.LITELLM_API_KEY = "test-key"
            return LiteLLMService()

    @pytest.mark.asyncio
    async def test_uses_direct_gemini_for_non_square(self, service):
        with patch("app.services.litellm_service.settings") as mock_settings:
            mock_settings.DIRECT_PROVIDER_FALLBACK = True
            mock_settings.gemini_available = True

            mock_gemini_service = MagicMock()
            mock_gemini_service.generate_image = AsyncMock(return_value=["http://example.com/image.png"])

            with patch("app.services.gemini_service.get_gemini_service", return_value=mock_gemini_service):
                result = await service.generate_image(
                    prompt="test prompt",
                    model="gemini/gemini-2.0-flash-exp",
                    aspect_ratio="16:9",
                    quality="standard",
                    n=1,
                )

                assert result == ["http://example.com/image.png"]
                mock_gemini_service.generate_image.assert_called_once_with(
                    prompt="test prompt",
                    model="gemini-2.0-flash-exp",  # Prefix removed
                    aspect_ratio="16:9",
                    quality="standard",
                    n=1,
                )

    @pytest.mark.asyncio
    async def test_uses_litellm_for_square_aspect_ratio(self, service, mock_openai_response):
        with patch("app.services.litellm_service.settings") as mock_settings:
            mock_settings.DIRECT_PROVIDER_FALLBACK = True
            mock_settings.gemini_available = True

            with patch.object(service.client.images, "generate", return_value=mock_openai_response):
                with patch("app.services.litellm_service.model_registry") as mock_registry:
                    mock_registry.get_model.return_value = None

                    with patch("app.services.litellm_service.storage_service") as mock_storage:
                        mock_storage.save_image = AsyncMock(return_value="http://example.com/image.png")

                        result = await service.generate_image(
                            prompt="test prompt",
                            model="gemini/gemini-2.0-flash-exp",
                            aspect_ratio="1:1",
                            quality="standard",
                            n=1,
                        )

                        assert result == ["http://example.com/image.png"]
                        service.client.images.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_litellm_when_fallback_disabled(self, service, mock_openai_response):
        with patch("app.services.litellm_service.settings") as mock_settings:
            mock_settings.DIRECT_PROVIDER_FALLBACK = False

            with patch.object(service.client.images, "generate", return_value=mock_openai_response):
                with patch("app.services.litellm_service.model_registry") as mock_registry:
                    mock_registry.get_model.return_value = None

                    with patch("app.services.litellm_service.storage_service") as mock_storage:
                        mock_storage.save_image = AsyncMock(return_value="http://example.com/image.png")

                        result = await service.generate_image(
                            prompt="test prompt",
                            model="gemini/gemini-2.0-flash-exp",
                            aspect_ratio="16:9",
                            quality="standard",
                            n=1,
                        )

                        assert result == ["http://example.com/image.png"]
                        service.client.images.generate.assert_called_once()
