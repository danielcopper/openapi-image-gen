# Image Generation OpenAPI Server

OpenAPI server for AI image generation and editing. Supports LiteLLM proxy (for cost tracking) and direct API access to OpenAI and Google Gemini.

## Features

- **Image Generation**: Create images from text prompts
- **Image Editing**: Edit existing images with mask-based inpainting (OpenAI) or prompt-based editing (Gemini)
- **Multi-Provider**: OpenAI (DALL-E 3, GPT-Image-1) and Google Gemini
- **LiteLLM Integration**: Unified API with cost tracking
- **Open WebUI Integration**: Auto-upload images to Open WebUI's file storage
- **Dynamic Models**: Auto-discovers available models from LiteLLM

## Quick Start

### Docker (Recommended)

1. Clone and configure:

```bash
git clone <your-repo>
cd openapi-image-gen
cp .env.example .env
# Edit .env with your API keys
```

2. Start the server:

```bash
docker-compose up -d
```

3. Access the API:

- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Manual Setup

1. Install dependencies:

    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

2. Configure environment:

    ```bash
    cp .env.example .env
    # Edit .env with your configuration
    ```

3. Run the server:

    ```bash
    uvicorn app.main:app --reload
    ```

## API Examples

### Generate Image

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A mountain landscape at sunset",
    "model": "dall-e-3",
    "aspect_ratio": "16:9"
  }'
```

### Edit Image (Mask-based, OpenAI)

```bash
curl -X POST "http://localhost:8000/edit" \
  -F "image=@photo.png" \
  -F "mask=@mask.png" \
  -F "prompt=Replace the sky with a sunset" \
  -F "provider=openai" \
  -F "model=gpt-image-1"
```

### Edit Image (Prompt-based, Gemini)

```bash
curl -X POST "http://localhost:8000/edit" \
  -F "image=@photo.png" \
  -F "prompt=Make the background more colorful" \
  -F "provider=gemini"
```

### Edit via URL Reference

```bash
curl -X POST "http://localhost:8000/edit" \
  -F "image_url=http://localhost:8000/images/abc123.png" \
  -F "prompt=Add a hat to the person" \
  -F "provider=gemini"
```

### List Models

```bash
curl "http://localhost:8000/models"
```

## Provider Configuration

### LiteLLM (Primary - Recommended)

LiteLLM provides unified access, cost tracking, and rate limiting:

```env
LITELLM_BASE_URL=http://litellm:4000
LITELLM_API_KEY=your-key  # Optional
```

### Direct APIs (Fallback)

Configure direct access for fallback when LiteLLM is unavailable:

```env
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

### Direct Provider Fallback

LiteLLM doesn't support all provider features. Enable `DIRECT_PROVIDER_FALLBACK` to automatically use the native provider API when needed:

```env
DIRECT_PROVIDER_FALLBACK=true
GEMINI_API_KEY=...  # Required for Gemini fallback
```

Currently applies to:
- **Gemini aspect ratios**: 16:9, 9:16, 4:3, 3:4 (LiteLLM only supports 1:1)

## Supported Models

### OpenAI

| Model | Generation | Editing | Notes |
|-------|------------|---------|-------|
| dall-e-3 | Yes | No | HD quality, multiple aspect ratios |
| gpt-image-1 | Yes | Yes (mask) | Fast, supports inpainting |
| dall-e-2 | Yes | Yes (mask) | Square only |

### Google Gemini

| Model | Generation | Editing | Notes |
|-------|------------|---------|-------|
| gemini-2.0-flash-preview-image-generation | Yes | Yes (prompt) | Fast, prompt-based editing |

See [CONFIGURATION.md](CONFIGURATION.md) for details.

## Open WebUI Integration

1. In Open WebUI, go to **Settings > Tools**
2. Add new OpenAPI server:
   - **URL**: `http://your-server:8000/openapi.json`
   - **Name**: Image Generation
3. Tools will appear automatically in chat interface

For admin/global tools, configure in Admin Settings with server-accessible URL.

## API Endpoints

### Image Generation

- `POST /generate` - Generate image from prompt

### Image Editing

- `POST /edit` - Edit existing image (supports file upload or URL reference)

### Models

- `GET /models` - List available models
- `POST /models/refresh` - Refresh model list from LiteLLM

### Info

- `GET /health` - Health check + provider status
- `GET /docs` - API documentation

## Configuration

See [CONFIGURATION.md](CONFIGURATION.md) for complete configuration guide including:

- Environment variables
- Model capabilities
- Provider setup
- Authentication
- Storage options

## Testing

Run tests:

```bash
pytest
```

With coverage:

```bash
pytest --cov=app --cov-report=html
```

## Project Structure

```
app/
├── main.py              # FastAPI app
├── core/                # Config, security
├── api/routes/          # Endpoints (generate, edit, models, health)
├── schemas/             # Request/response models
└── services/            # Provider integrations

tests/                   # Tests
```

## License

MIT
