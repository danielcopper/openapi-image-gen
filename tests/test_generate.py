from unittest.mock import MagicMock, patch


def test_get_default_model_uses_env_config():
    """
    Test that DEFAULT_MODEL env var is used.
    """
    with patch("app.api.routes.generate.settings") as mock_settings:
        mock_settings.DEFAULT_MODEL = "gemini/gemini-2.0-flash-exp-image-generation"

        from app.api.routes.generate import _get_default_model

        result = _get_default_model("litellm")
        assert result == "gemini/gemini-2.0-flash-exp-image-generation"


def test_get_default_model_fallback_to_registry():
    """
    Test fallback to registry when DEFAULT_MODEL is not set.
    """
    with patch("app.api.routes.generate.settings") as mock_settings:
        mock_settings.DEFAULT_MODEL = None

        with patch("app.api.routes.generate.model_registry") as mock_registry:
            mock_model = MagicMock()
            mock_model.id = "dall-e-3"
            mock_model.provider = "openai"
            mock_registry.get_models.return_value = [mock_model]

            from app.api.routes.generate import _get_default_model

            result = _get_default_model("litellm")
            assert result == "dall-e-3"


def test_get_default_model_hardcoded_fallback():
    """
    Test hardcoded fallback when no models in registry.
    """
    with patch("app.api.routes.generate.settings") as mock_settings:
        mock_settings.DEFAULT_MODEL = None

        with patch("app.api.routes.generate.model_registry") as mock_registry:
            mock_registry.get_models.return_value = []

            from app.api.routes.generate import _get_default_model

            # LiteLLM/OpenAI provider defaults to dall-e-3
            result = _get_default_model("litellm")
            assert result == "dall-e-3"

            result = _get_default_model("openai")
            assert result == "dall-e-3"

            # Gemini provider defaults to gemini model
            result = _get_default_model("gemini")
            assert result == "gemini-2.0-flash-preview-image-generation"
