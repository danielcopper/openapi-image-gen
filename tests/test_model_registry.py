import pytest
from unittest.mock import patch, AsyncMock
import httpx

from app.services.model_registry import ModelRegistry
from app.schemas.responses import ModelInfo, ModelCapabilities


@pytest.mark.asyncio
async def test_load_from_litellm(mock_litellm_models_response):
    """
    Test loading models from LiteLLM API.
    """
    registry = ModelRegistry()

    with patch("app.services.model_registry.settings") as mock_settings:
        mock_settings.LITELLM_BASE_URL = "http://litellm:4000"
        mock_settings.LITELLM_API_KEY = None
        mock_settings.litellm_available = True

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_litellm_models_response
            mock_response.raise_for_status = AsyncMock()

            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )

            models = await registry.load_models()

            assert len(models) == 3
            assert any(m.id == "dall-e-3" for m in models)
            assert any(m.id == "gpt-image-1" for m in models)
            assert any(m.id.startswith("gemini") for m in models)


@pytest.mark.asyncio
async def test_load_static_models():
    """
    Test fallback to static model list.
    """
    registry = ModelRegistry()

    with patch("app.services.model_registry.settings") as mock_settings:
        mock_settings.litellm_available = False
        mock_settings.openai_available = True
        mock_settings.gemini_available = True

        models = await registry.load_models()

        # Should have OpenAI and Gemini models
        assert len(models) > 0
        openai_models = [m for m in models if m.provider == "openai"]
        gemini_models = [m for m in models if m.provider == "gemini"]

        assert len(openai_models) > 0
        assert len(gemini_models) > 0


@pytest.mark.asyncio
async def test_cache_validity():
    """
    Test model cache validity.
    """
    registry = ModelRegistry()

    with patch("app.services.model_registry.settings") as mock_settings:
        mock_settings.litellm_available = False
        mock_settings.openai_available = True
        mock_settings.MODEL_CACHE_TTL = 3600

        # Load models
        await registry.load_models()

        # Cache should be valid
        assert registry.cache_valid

        # Cache age should be small
        assert registry.cache_age is not None
        assert registry.cache_age < 5

        # Expires in should be close to TTL
        assert registry.cache_expires_in is not None
        assert registry.cache_expires_in > 3590


def test_get_model_capabilities():
    """
    Test getting model capabilities.
    """
    registry = ModelRegistry()

    # Test known model
    caps = registry._get_capabilities("dall-e-3")
    assert caps.supports_quality is True
    assert caps.max_images == 1
    assert "16:9" in caps.supports_aspect_ratios

    # Test unknown model (should get defaults)
    caps = registry._get_capabilities("unknown-model")
    assert caps.supports_quality is False
    assert caps.max_images == 4


def test_infer_provider():
    """
    Test provider inference from model ID.
    """
    registry = ModelRegistry()

    assert registry._infer_provider("dall-e-3") == "openai"
    assert registry._infer_provider("gpt-image-1") == "openai"
    assert registry._infer_provider("gemini-2.0-flash") == "gemini"
    assert registry._infer_provider("imagen-3.0") == "gemini"
    assert registry._infer_provider("unknown") == "unknown"
