from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.model_registry import ModelRegistry


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

        # Create mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_litellm_models_response
        mock_response.raise_for_status.return_value = None

        # Create async client mock
        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.model_registry.httpx.AsyncClient", return_value=mock_client):
            models = await registry.load_models()

            assert len(models) == 6
            assert any(m.id == "gpt-image-1.5" for m in models)
            assert any(m.id == "gpt-image-1" for m in models)
            assert any(m.id == "gpt-image-1-mini" for m in models)
            assert any(m.id == "dall-e-3" for m in models)
            assert any(m.id == "gemini-2.5-flash-image" for m in models)
            assert any(m.id.startswith("gemini-2.0") for m in models)


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


def test_new_model_capabilities():
    """
    Test capabilities for newly added models.
    """
    registry = ModelRegistry()

    # gpt-image-1.5
    caps = registry._get_capabilities("gpt-image-1.5")
    assert caps.supports_quality is True
    assert caps.quality_values == ["auto", "high", "medium", "low"]
    assert "2:3" in caps.supports_aspect_ratios
    assert "3:2" in caps.supports_aspect_ratios
    assert caps.max_images == 4
    assert caps.supports_editing is True

    # gemini-2.5-flash-image
    caps = registry._get_capabilities("gemini-2.5-flash-image")
    assert caps.supports_editing is True
    assert caps.editing_type == "prompt"
    assert "2:3" in caps.supports_aspect_ratios


def test_deprecated_models():
    """
    Test deprecation flags on models.
    """
    registry = ModelRegistry()

    # Deprecated models
    assert registry._get_capabilities("dall-e-3").deprecated is not None
    assert "May" in registry._get_capabilities("dall-e-3").deprecated
    assert registry._get_capabilities("dall-e-2").deprecated is not None
    assert registry._get_capabilities("gemini-2.0-flash-preview-image-generation").deprecated is not None

    # Active models
    assert registry._get_capabilities("gpt-image-1").deprecated is None
    assert registry._get_capabilities("gpt-image-1.5").deprecated is None
    assert registry._get_capabilities("gemini-2.5-flash-image").deprecated is None


def test_infer_provider():
    """
    Test provider inference from model ID.
    """
    registry = ModelRegistry()

    assert registry._infer_provider("dall-e-3") == "openai"
    assert registry._infer_provider("gpt-image-1") == "openai"
    assert registry._infer_provider("gpt-image-1.5") == "openai"
    assert registry._infer_provider("gpt-image-1-mini") == "openai"
    assert registry._infer_provider("gemini-2.0-flash") == "gemini"
    assert registry._infer_provider("gemini-2.5-flash-image") == "gemini"
    assert registry._infer_provider("imagen-3.0") == "gemini"
    assert registry._infer_provider("imagen-4.0-generate-001") == "gemini"
    assert registry._infer_provider("unknown") == "unknown"


def test_is_image_model():
    """
    Test image model detection.
    """
    registry = ModelRegistry()

    # Should match image models
    assert registry._is_image_model("dall-e-3") is True
    assert registry._is_image_model("gpt-image-1") is True
    assert registry._is_image_model("gpt-image-1.5") is True
    assert registry._is_image_model("gpt-image-1-mini") is True
    assert registry._is_image_model("gemini-2.0-flash-preview-image-generation") is True
    assert registry._is_image_model("gemini-2.5-flash-image") is True
    assert registry._is_image_model("gemini-3-pro-image-preview") is True
    assert registry._is_image_model("imagen-3.0") is True
    assert registry._is_image_model("imagen-4.0-generate-001") is True

    # Should NOT match non-image models
    assert registry._is_image_model("gpt-4o") is False
    assert registry._is_image_model("claude-3-opus") is False
    assert registry._is_image_model("gemini-pro") is False


@pytest.mark.asyncio
async def test_filter_image_models():
    """
    Test that only image models are returned when filter is enabled.
    """
    registry = ModelRegistry()

    mock_response = {
        "data": [
            {"id": "dall-e-3"},
            {"id": "gpt-4o"},
            {"id": "claude-3-opus"},
            {"id": "gemini-2.0-flash-preview-image-generation"},
        ]
    }

    with patch("app.services.model_registry.settings") as mock_settings:
        mock_settings.LITELLM_BASE_URL = "http://litellm:4000"
        mock_settings.LITELLM_API_KEY = None
        mock_settings.litellm_available = True
        mock_settings.FILTER_IMAGE_MODELS = True
        mock_settings.MODEL_CACHE_TTL = 3600

        # Mock HTTP response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status.return_value = None

        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_resp)
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.model_registry.httpx.AsyncClient", return_value=mock_client):
            models = await registry.load_models()

            # Should only have image models
            assert len(models) == 2
            model_ids = [m.id for m in models]
            assert "dall-e-3" in model_ids
            assert "gemini-2.0-flash-preview-image-generation" in model_ids
            assert "gpt-4o" not in model_ids
            assert "claude-3-opus" not in model_ids
