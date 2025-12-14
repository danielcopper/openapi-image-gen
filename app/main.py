import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import edit, generate, health, models
from app.core.config import settings
from app.services.model_registry import model_registry

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    """
    # Startup
    logger.info("Starting Image Generation API")

    # Ensure storage directory exists
    storage_path = Path(settings.STORAGE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Storage path: {storage_path.absolute()}")

    # Load available models
    try:
        models_list = await model_registry.load_models()
        logger.info(f"Loaded {len(models_list)} models")
    except Exception as e:
        logger.warning(f"Failed to load models on startup: {e}")
        logger.info("Will use fallback static model list")

    # Log provider availability
    logger.info(f"LiteLLM available: {settings.litellm_available}")
    logger.info(f"OpenAI available: {settings.openai_available}")
    logger.info(f"Gemini available: {settings.gemini_available}")

    yield

    # Shutdown
    logger.info("Shutting down Image Generation API")


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description=settings.API_DESCRIPTION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for generated images
app.mount("/images", StaticFiles(directory=settings.STORAGE_PATH), name="images")

# Register routers
app.include_router(generate.router)
app.include_router(edit.router)
app.include_router(models.router)
app.include_router(health.router)


@app.get("/", tags=["Root"], summary="API Info", description="Get basic API information")
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "docs": "/docs",
        "openapi": "/openapi.json",
        "providers": {
            "litellm": settings.litellm_available,
            "openai": settings.openai_available,
            "gemini": settings.gemini_available,
        },
    }


def custom_openapi():
    """
    Custom OpenAPI schema that includes available models in the description.
    """
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Get available models and add to schema description
    available_models = model_registry.get_models()
    if available_models:
        image_models = [m.id for m in available_models if "image" in m.id.lower() or "dall" in m.id.lower()]
        if not image_models:
            image_models = [m.id for m in available_models[:10]]  # First 10 as fallback

        models_list = ", ".join(f"'{m}'" for m in image_models)

        # Update the model field description in ImageRequest schema
        if (
            "components" in openapi_schema
            and "schemas" in openapi_schema["components"]
            and "ImageRequest" in openapi_schema["components"]["schemas"]
        ):
            props = openapi_schema["components"]["schemas"]["ImageRequest"].get("properties", {})
            if "model" in props:
                props["model"]["description"] = (
                    f"Model ID for image generation. Available models: {models_list}. "
                    "Use 'openai/dall-e-3' for high quality, 'openai/gpt-image-1' for fast generation."
                )

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
