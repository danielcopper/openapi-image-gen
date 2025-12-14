import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def temp_storage():
    """
    Create temporary storage directory for tests.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_openai_response():
    """
    Mock OpenAI API response.
    """
    mock_image = Mock()
    mock_image.b64_json = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    mock_response = Mock()
    mock_response.data = [mock_image]

    return mock_response


@pytest.fixture
def mock_gemini_response():
    """
    Mock Gemini API response.
    """
    mock_inline_data = Mock()
    mock_inline_data.data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    mock_inline_data.mime_type = "image/png"

    mock_part = Mock()
    mock_part.inline_data = mock_inline_data

    mock_content = Mock()
    mock_content.parts = [mock_part]

    mock_candidate = Mock()
    mock_candidate.content = mock_content

    mock_response = Mock()
    mock_response.candidates = [mock_candidate]

    return mock_response


@pytest.fixture
def mock_litellm_models_response():
    """
    Mock LiteLLM /v1/models response.
    """
    return {
        "data": [
            {"id": "dall-e-3"},
            {"id": "gpt-image-1"},
            {"id": "gemini-2.0-flash-preview-image-generation"},
        ]
    }
