from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ImageResponse(BaseModel):
    """
    Response schema for image generation.
    """

    image_url: Optional[str] = Field(
        default=None, description="URL to access the generated image (when response_format='url')"
    )

    image_base64: Optional[str] = Field(
        default=None, description="Base64 encoded image data (when response_format='base64')"
    )

    mime_type: Optional[str] = Field(
        default=None, description="MIME type of the image (e.g., 'image/png')"
    )

    prompt: str = Field(..., description="The prompt used for generation")

    model: str = Field(..., description="The model that generated the image")

    provider: str = Field(..., description="The provider used (litellm, openai, gemini)")

    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about the generation"
    )


class ModelCapabilities(BaseModel):
    """
    Model capabilities and parameters.
    """

    supports_quality: bool = Field(
        default=False, description="Whether model supports quality parameter"
    )

    supports_aspect_ratios: List[str] = Field(
        default_factory=lambda: ["1:1"], description="Supported aspect ratios"
    )

    max_images: int = Field(default=1, description="Maximum number of images (n parameter)")


class ModelInfo(BaseModel):
    """
    Information about an available model.
    """

    id: str = Field(..., description="Model identifier")

    provider: str = Field(..., description="Provider offering this model")

    capabilities: ModelCapabilities = Field(
        default_factory=ModelCapabilities, description="Model capabilities"
    )


class ModelListResponse(BaseModel):
    """
    Response schema for listing available models.
    """

    models: List[ModelInfo] = Field(..., description="List of available models")

    cached: bool = Field(..., description="Whether results are from cache")

    cache_expires_in: Optional[int] = Field(
        default=None, description="Seconds until cache expiration"
    )


class HealthResponse(BaseModel):
    """
    Response schema for health check.
    """

    status: str = Field(..., description="Overall service status")

    litellm: bool = Field(..., description="LiteLLM availability")

    openai: bool = Field(..., description="OpenAI direct access availability")

    gemini: bool = Field(..., description="Gemini direct access availability")
