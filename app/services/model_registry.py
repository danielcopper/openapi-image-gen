import logging
import time

import httpx

from app.core.config import settings
from app.schemas.responses import ModelCapabilities, ModelInfo

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Manages available models with dynamic discovery from LiteLLM.
    Caches results to avoid frequent API calls.
    """

    # Model capabilities database (fallback for known models)
    KNOWN_CAPABILITIES: dict[str, ModelCapabilities] = {
        "dall-e-2": ModelCapabilities(
            supports_quality=False, supports_aspect_ratios=["1:1"], max_images=4
        ),
        "dall-e-3": ModelCapabilities(
            supports_quality=True, supports_aspect_ratios=["1:1", "16:9", "9:16"], max_images=1
        ),
        "gpt-image-1": ModelCapabilities(
            supports_quality=False, supports_aspect_ratios=["1:1", "16:9", "9:16"], max_images=4
        ),
        "gemini-2.0-flash-preview-image-generation": ModelCapabilities(
            supports_quality=False,
            supports_aspect_ratios=["1:1", "16:9", "9:16", "4:3", "3:4"],
            max_images=4,
        ),
        "imagen-3.0-generate-002": ModelCapabilities(
            supports_quality=False,
            supports_aspect_ratios=["1:1", "16:9", "9:16", "4:3", "3:4"],
            max_images=4,
        ),
    }

    def __init__(self):
        self._models: list[ModelInfo] = []
        self._cache_timestamp: float | None = None

    @property
    def cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self._cache_timestamp:
            return False
        age = time.time() - self._cache_timestamp
        return age < settings.MODEL_CACHE_TTL

    @property
    def cache_age(self) -> int | None:
        """Get cache age in seconds."""
        if not self._cache_timestamp:
            return None
        return int(time.time() - self._cache_timestamp)

    @property
    def cache_expires_in(self) -> int | None:
        """Get seconds until cache expiration."""
        if not self._cache_timestamp:
            return None
        age = self.cache_age
        if age is None:
            return None
        remaining = settings.MODEL_CACHE_TTL - age
        return max(0, remaining)

    async def load_models(self, force: bool = False) -> list[ModelInfo]:
        """
        Load available models from LiteLLM or fallback to static list.

        Args:
            force: Force refresh even if cache is valid

        Returns:
            List of available models
        """
        if not force and self.cache_valid:
            logger.debug("Returning cached models")
            return self._models

        logger.info("Loading models from LiteLLM")
        models = []

        # Try loading from LiteLLM if configured
        if settings.litellm_available:
            try:
                models = await self._load_from_litellm()
                logger.info(f"Loaded {len(models)} models from LiteLLM")
            except Exception as e:
                logger.warning(f"Failed to load models from LiteLLM: {e}")

        # Fallback to static known models if LiteLLM failed or not configured
        if not models:
            logger.info("Using static model list")
            models = self._get_static_models()

        self._models = models
        self._cache_timestamp = time.time()

        return self._models

    async def _load_from_litellm(self) -> list[ModelInfo]:
        """
        Load models from LiteLLM /v1/models endpoint.
        """
        url = f"{settings.LITELLM_BASE_URL.rstrip('/')}/v1/models"
        headers = {}

        if settings.LITELLM_API_KEY:
            headers["Authorization"] = f"Bearer {settings.LITELLM_API_KEY}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        models = []
        for model_data in data.get("data", []):
            model_id = model_data.get("id")
            if not model_id:
                continue

            # Determine provider from model ID
            provider = self._infer_provider(model_id)

            # Get capabilities
            capabilities = self._get_capabilities(model_id)

            models.append(ModelInfo(id=model_id, provider=provider, capabilities=capabilities))

        return models

    def _get_static_models(self) -> list[ModelInfo]:
        """
        Return static list of known models based on available API keys.
        """
        models = []

        # OpenAI models
        if settings.openai_available or settings.litellm_available:
            for model_id in ["dall-e-3", "gpt-image-1", "dall-e-2"]:
                models.append(
                    ModelInfo(
                        id=model_id,
                        provider="openai",
                        capabilities=self.KNOWN_CAPABILITIES.get(model_id, ModelCapabilities()),
                    )
                )

        # Gemini models
        if settings.gemini_available or settings.litellm_available:
            for model_id in [
                "gemini-2.0-flash-preview-image-generation",
                "imagen-3.0-generate-002",
            ]:
                models.append(
                    ModelInfo(
                        id=model_id,
                        provider="gemini",
                        capabilities=self.KNOWN_CAPABILITIES.get(model_id, ModelCapabilities()),
                    )
                )

        return models

    def _infer_provider(self, model_id: str) -> str:
        """
        Infer provider from model ID.
        """
        model_lower = model_id.lower()

        if "dall-e" in model_lower or "gpt-image" in model_lower:
            return "openai"
        elif "gemini" in model_lower or "imagen" in model_lower:
            return "gemini"
        else:
            return "unknown"

    def _get_capabilities(self, model_id: str) -> ModelCapabilities:
        """
        Get capabilities for a model, using known database or defaults.
        """
        # Check exact match
        if model_id in self.KNOWN_CAPABILITIES:
            return self.KNOWN_CAPABILITIES[model_id]

        # Check partial match
        for known_model, caps in self.KNOWN_CAPABILITIES.items():
            if known_model in model_id.lower():
                return caps

        # Default capabilities (assume full support)
        return ModelCapabilities(
            supports_quality=False,
            supports_aspect_ratios=["1:1", "16:9", "9:16", "4:3", "3:4"],
            max_images=4,
        )

    def get_models(self) -> list[ModelInfo]:
        """
        Get cached models (non-async).
        """
        return self._models

    def get_model(self, model_id: str) -> ModelInfo | None:
        """
        Get specific model info.
        """
        for model in self._models:
            if model.id == model_id:
                return model
        return None


model_registry = ModelRegistry()
