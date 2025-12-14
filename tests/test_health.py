from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_health_check_sends_auth_header():
    """
    Test that health check sends Authorization header to LiteLLM.
    """
    with patch("app.api.routes.health.settings") as mock_settings:
        mock_settings.LITELLM_BASE_URL = "http://litellm:4000"
        mock_settings.LITELLM_API_KEY = "sk-test-key"
        mock_settings.openai_available = False
        mock_settings.gemini_available = False

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.api.routes.health.httpx.AsyncClient", return_value=mock_client):
            from app.api.routes.health import health_check

            await health_check()

            # Verify auth header was sent
            mock_client_instance.get.assert_called_once()
            call_args = mock_client_instance.get.call_args
            assert "headers" in call_args.kwargs
            assert call_args.kwargs["headers"]["Authorization"] == "Bearer sk-test-key"


@pytest.mark.asyncio
async def test_health_check_no_auth_when_no_key():
    """
    Test that health check doesn't send auth header when LITELLM_API_KEY is not set.
    """
    with patch("app.api.routes.health.settings") as mock_settings:
        mock_settings.LITELLM_BASE_URL = "http://litellm:4000"
        mock_settings.LITELLM_API_KEY = None
        mock_settings.openai_available = False
        mock_settings.gemini_available = False

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client_instance = MagicMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.api.routes.health.httpx.AsyncClient", return_value=mock_client):
            from app.api.routes.health import health_check

            await health_check()

            # Verify empty headers were sent (no auth)
            mock_client_instance.get.assert_called_once()
            call_args = mock_client_instance.get.call_args
            assert call_args.kwargs["headers"] == {}
