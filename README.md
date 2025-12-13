# Image Generation OpenAPI Server

Production-ready OpenAPI server for AI image generation with LiteLLM proxy integration (cost tracking) and direct API fallback support for OpenAI DALL-E and Google Gemini models.

## Features

- **LiteLLM Integration**: Primary provider with automatic cost tracking and unified API
- **Multi-Provider Support**: OpenAI (DALL-E 3, GPT-Image-1) + Google Gemini (Imagen 3.0, Flash)
- **Dynamic Model Discovery**: Auto-loads available models from LiteLLM
- **SSE Streaming**: Real-time progress updates during generation
- **Flexible Responses**: JSON, SSE stream, or HTML preview
- **Local Storage**: Images saved locally and served via static files
- **Comprehensive API**: Full OpenAPI/Swagger documentation
- **Production Ready**: Docker support, health checks, authentication

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

### Generate Image (Standard)

```bash
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A serene mountain landscape at sunset",
    "provider": "litellm",
    "model": "dall-e-3",
    "aspect_ratio": "16:9",
    "quality": "hd"
  }'
```

### Generate with SSE Streaming

```bash
curl -N "http://localhost:8000/generate-stream" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A futuristic city skyline",
    "aspect_ratio": "9:16"
  }'
```

### Python Client

```python
import requests

response = requests.post(
    "http://localhost:8000/generate",
    json={
        "prompt": "A cute cat wearing sunglasses",
        "provider": "litellm",  # or "openai", "gemini"
        "aspect_ratio": "1:1",
        "n": 1
    }
)

result = response.json()
print(f"Image URL: {result['image_url']}")
```

### List Available Models

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

## Supported Models

### OpenAI
- **dall-e-3**: HD quality, multiple aspect ratios, n=1 only
- **gpt-image-1**: Newest model, multiple sizes
- **dall-e-2**: Square only, fast generation

### Google Gemini
- **gemini-2.0-flash-preview-image-generation**: Fast generation
- **imagen-3.0-generate-002**: High quality

See [CONFIGURATION.md](CONFIGURATION.md) for detailed model capabilities.

## Open WebUI Integration

1. In Open WebUI, go to **Settings > Tools**
2. Add new OpenAPI server:
   - **URL**: `http://your-server:8000/openapi.json`
   - **Name**: Image Generation
3. Tools will appear automatically in chat interface

For admin/global tools, configure in Admin Settings with server-accessible URL.

## API Endpoints

### Image Generation
- `POST /generate` - Generate image (JSON response)
- `POST /generate-stream` - Generate with SSE progress
- `POST /generate-preview` - Generate with HTML preview

### Model Management
- `GET /models` - List available models
- `POST /models/refresh` - Refresh model list from LiteLLM

### Health & Info
- `GET /health` - Health check + provider status
- `GET /` - API information
- `GET /docs` - Interactive API documentation

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

## Development

Project structure:
```
app/
├── main.py              # FastAPI application
├── core/                # Configuration & utilities
├── api/routes/          # API endpoints
├── schemas/             # Pydantic models
├── services/            # Business logic
└── utils/               # Helpers

tests/                   # Test suite
```

## License

MIT

## Contributing

Contributions welcome! Please ensure:
- Tests pass (`pytest`)
- Code follows project style
- Documentation updated

## Support

- Issues: GitHub Issues
- Docs: `/docs` endpoint
- Health: `/health` endpoint
