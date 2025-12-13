import pytest
import json
from unittest.mock import AsyncMock

from app.utils.sse import generate_with_progress, SSEEvent


@pytest.mark.asyncio
async def test_sse_event_format():
    """
    Test SSE event formatting.
    """
    event = SSEEvent("test", {"message": "hello"})
    formatted = event.format()

    assert "event: test" in formatted
    assert "data: " in formatted
    assert "hello" in formatted
    assert formatted.endswith("\n\n")


@pytest.mark.asyncio
async def test_generate_with_progress_success():
    """
    Test SSE generator with successful generation.
    """
    # Mock service function
    async def mock_service_func(prompt, model, **kwargs):
        return ["http://example.com/image.png"]

    # Collect events
    events = []
    async for event_str in generate_with_progress(
        prompt="test prompt",
        model="dall-e-3",
        provider="openai",
        service_func=mock_service_func
    ):
        events.append(event_str)

    # Verify event sequence
    assert len(events) >= 4  # queued, generating, processing, complete

    # Parse events
    event_types = []
    for event_str in events:
        lines = event_str.strip().split("\n")
        for line in lines:
            if line.startswith("event: "):
                event_types.append(line.split("event: ")[1])

    # Verify event progression
    assert "status" in event_types
    assert "complete" in event_types

    # Verify final event has image URLs
    last_event = events[-1]
    assert "image_urls" in last_event or "complete" in last_event


@pytest.mark.asyncio
async def test_generate_with_progress_error():
    """
    Test SSE generator with error.
    """
    # Mock service function that raises error
    async def mock_service_func(prompt, model, **kwargs):
        raise ValueError("Test error")

    # Collect events
    events = []
    async for event_str in generate_with_progress(
        prompt="test prompt",
        model="dall-e-3",
        provider="openai",
        service_func=mock_service_func
    ):
        events.append(event_str)

    # Verify error event was sent
    event_types = []
    for event_str in events:
        lines = event_str.strip().split("\n")
        for line in lines:
            if line.startswith("event: "):
                event_types.append(line.split("event: ")[1])

    assert "error" in event_types

    # Verify error message
    last_event = events[-1]
    assert "error" in last_event
    assert "Test error" in last_event


@pytest.mark.asyncio
async def test_sse_progress_values():
    """
    Test that progress values increase correctly.
    """
    async def mock_service_func(prompt, model, **kwargs):
        return ["http://example.com/image.png"]

    # Collect progress values
    progress_values = []
    async for event_str in generate_with_progress(
        prompt="test",
        model="test-model",
        provider="test",
        service_func=mock_service_func
    ):
        # Parse progress from data
        lines = event_str.strip().split("\n")
        for line in lines:
            if line.startswith("data: "):
                data_str = line.split("data: ")[1]
                data = json.loads(data_str)
                if "progress" in data:
                    progress_values.append(data["progress"])

    # Verify progress increases
    assert len(progress_values) > 0
    assert progress_values[0] == 0  # Should start at 0
    assert progress_values[-1] == 100  # Should end at 100
    assert all(progress_values[i] <= progress_values[i+1]
               for i in range(len(progress_values)-1))  # Should be non-decreasing
