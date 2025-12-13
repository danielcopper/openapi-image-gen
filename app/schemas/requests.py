from typing import Literal, Optional

from pydantic import BaseModel, Field


class ImageRequest(BaseModel):
    """
    Request schema for image generation.
    """

    prompt: str = Field(
        ...,
        description="Detailed description of the image to generate. Be specific about style, colors, composition, and mood.",
        min_length=1,
        max_length=4000,
        examples=["A serene mountain landscape at sunset with vibrant colors"],
    )

    provider: Literal["litellm", "openai", "gemini"] = Field(
        default="litellm",
        description=(
            "Image generation provider. Use 'litellm' (default) which routes to all available models. "
            "Only use 'openai' or 'gemini' as direct fallback if LiteLLM is unavailable."
        ),
    )

    model: Optional[str] = Field(
        default=None,
        description=(
            "Model ID for image generation. Call GET /models to see all available models. "
            "Common models: 'openai/dall-e-3' (high quality), 'openai/gpt-image-1' (fast), "
            "'gemini/gemini-2.5-flash-image'. Models use 'provider/model-name' format."
        ),
        examples=["openai/dall-e-3", "openai/gpt-image-1", "gemini/gemini-2.5-flash-image"],
    )

    aspect_ratio: Literal["1:1", "16:9", "9:16", "4:3", "3:4"] = Field(
        default="1:1",
        description=(
            "Image aspect ratio. "
            "1:1 = square, 16:9 = landscape, 9:16 = portrait, "
            "4:3 = classic landscape, 3:4 = classic portrait"
        ),
    )

    quality: Literal["standard", "hd"] = Field(
        default="standard", description="Image quality. 'hd' available for dall-e-3 only"
    )

    n: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate (1-4). Some models only support n=1",
    )

    response_format: Literal["url", "base64"] = Field(
        default="url",
        description=(
            "Response format for generated images. "
            "Use 'base64' for chat integrations (returns image data directly, can be displayed inline). "
            "Use 'url' only for web applications that can fetch external URLs."
        ),
    )

    stream: bool = Field(default=False, description="Enable SSE streaming for progress updates")


class ModelRefreshRequest(BaseModel):
    """
    Request schema for refreshing model registry.
    """

    force: bool = Field(default=False, description="Force refresh even if cache is valid")
