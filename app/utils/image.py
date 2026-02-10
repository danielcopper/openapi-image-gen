import base64
import contextlib
import logging
from pathlib import Path

from fastapi.responses import HTMLResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

MIME_TYPES: dict[str, str] = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def get_mime_type(path: Path) -> str:
    """Get MIME type from file extension, defaulting to image/png."""
    return MIME_TYPES.get(path.suffix.lower(), "image/png")


def extract_safe_filename(url: str) -> str:
    """Extract filename from URL, using only the basename to prevent path traversal."""
    import os
    import re

    filename = os.path.basename(url.split("?")[0])
    # Validate it looks like a UUID-based filename (uuid4.ext)
    if not re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.\w+$", filename):
        raise ValueError(f"Invalid image filename: {filename}")
    return filename


async def read_image_as_base64(url: str, cleanup: bool = True) -> tuple[str, str]:
    """
    Read a locally stored image as base64.

    Args:
        url: URL containing the filename (last path segment)
        cleanup: If True and SAVE_IMAGES_LOCALLY is False, delete the file after reading

    Returns:
        Tuple of (base64_data, mime_type)

    Raises:
        FileNotFoundError: If the image file doesn't exist
    """
    image_filename = url.split("/")[-1]
    image_path = Path(settings.STORAGE_PATH) / image_filename

    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_filename}")

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    if cleanup and not settings.SAVE_IMAGES_LOCALLY:
        with contextlib.suppress(Exception):
            image_path.unlink()

    mime_type = get_mime_type(image_path)
    return image_data, mime_type


def build_openwebui_html_response(image_data: str, mime_type: str) -> HTMLResponse:
    """Build an HTML response with an embedded base64 image for OpenWebUI."""
    html = f'<img src="data:{mime_type};base64,{image_data}" style="max-width:100%; height:auto;">'
    return HTMLResponse(content=html, headers={"Content-Disposition": "inline"})
