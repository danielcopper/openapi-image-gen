import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.api.routes import generate, models, health
from app.services.model_registry import model_registry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
    openapi_url="/openapi.json"
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
app.mount(
    "/images",
    StaticFiles(directory=settings.STORAGE_PATH),
    name="images"
)

# Register routers
app.include_router(generate.router)
app.include_router(models.router)
app.include_router(health.router)


@app.get(
    "/",
    tags=["Root"],
    summary="API Info",
    description="Get basic API information"
)
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
            "gemini": settings.gemini_available
        }
    }
