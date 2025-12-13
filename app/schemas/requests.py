from typing import Optional, Literal
from pydantic import BaseModel, Field


class ImageRequest(BaseModel):
    """
    Request schema for image generation.
    """

    prompt: str = Field(
        ...,
        description="Detailed description of the image to generate",
        min_length=1,
        max_length=4000,
        examples=["A serene mountain landscape at sunset with vibrant colors"]
    )

    provider: Literal["litellm", "openai", "gemini"] = Field(
        default="litellm",
        description=(
            "Image generation provider. "
            "'litellm' uses LiteLLM proxy (recommended for cost tracking), "
            "'openai' and 'gemini' are direct API fallbacks"
        )
    )

    model: Optional[str] = Field(
        default=None,
        description=(
            "Model to use. If not specified, uses provider's default. "
            "Examples: 'dall-e-3', 'gpt-image-1', 'gemini-2.0-flash-preview-image-generation', "
            "'imagen-3.0-generate-002'"
        ),
        examples=["dall-e-3"]
    )

    aspect_ratio: Literal["1:1", "16:9", "9:16", "4:3", "3:4"] = Field(
        default="1:1",
        description=(
            "Image aspect ratio. "
            "1:1 = square, 16:9 = landscape, 9:16 = portrait, "
            "4:3 = classic landscape, 3:4 = classic portrait"
        )
    )

    quality: Literal["standard", "hd"] = Field(
        default="standard",
        description="Image quality. 'hd' available for dall-e-3 only"
    )

    n: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of images to generate (1-4). Some models only support n=1"
    )

    stream: bool = Field(
        default=False,
        description="Enable SSE streaming for progress updates"
    )


class ModelRefreshRequest(BaseModel):
    """
    Request schema for refreshing model registry.
    """

    force: bool = Field(
        default=False,
        description="Force refresh even if cache is valid"
    )
