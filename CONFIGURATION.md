# Configuration Guide

Complete configuration reference for the Image Generation API.

## Environment Variables

### LiteLLM Configuration (Primary)

**`LITELLM_BASE_URL`**
- LiteLLM proxy base URL
- Example: `http://litellm:4000` or `http://localhost:4000`
- Required for LiteLLM provider
- Leave empty to disable LiteLLM

**`LITELLM_API_KEY`**
- API key for LiteLLM authentication
- Optional, depends on your LiteLLM configuration
- Leave empty if your LiteLLM instance doesn't require auth

### Direct Provider Keys (Fallback)

**`OPENAI_API_KEY`**
- OpenAI API key for direct access
- Required for `provider="openai"`
- Format: `sk-...`
- Get from: https://platform.openai.com/api-keys

**`GEMINI_API_KEY`**
- Google Gemini API key for direct access
- Required for `provider="gemini"`
- Get from: https://aistudio.google.com/apikey

### Storage Configuration

**`STORAGE_PATH`**
- Local directory for generated images
- Default: `./generated_images`
- Docker: Use volume mount (e.g., `/app/generated_images`)

**`IMAGE_BASE_URL`**
- Public base URL for serving images
- Default: `http://localhost:8000`
- Example: `https://api.example.com`
- Used to construct full image URLs

### Model Defaults

**`DEFAULT_MODEL`**
- Default model for generation/editing when not specified in request
- Example: `gpt-image-1`, `dall-e-3`
- Optional - if not set, first available model is used

### Security

**`API_BEARER_TOKEN`**
- Bearer token for API authentication
- Optional - leave empty to disable auth
- When set, all requests must include `Authorization: Bearer <token>` header
- Generate secure token: `openssl rand -base64 32`

### Model Registry

**`MODEL_CACHE_TTL`**
- Model list cache duration in seconds
- Default: `3600` (1 hour)
- Increase for production to reduce LiteLLM API calls
- Decrease for development for faster model updates

### Server Configuration

**`HOST`**
- Host to bind server to
- Default: `0.0.0.0` (all interfaces)
- Use `127.0.0.1` for localhost only

**`PORT`**
- Port to listen on
- Default: `8000`
- Change if port conflicts exist

## Model Capabilities

### OpenAI Models

**dall-e-2**
- Aspect Ratios: `1:1` only
- Quality: Not supported
- Max Images (n): 4
- Editing: Yes (mask-based)

**dall-e-3**
- Aspect Ratios: `1:1`, `16:9`, `9:16`
- Quality: `standard`, `hd`
- Max Images (n): 1
- Editing: No

**gpt-image-1**
- Aspect Ratios: `1:1`, `16:9`, `9:16`
- Quality: Not supported
- Max Images (n): 4
- Editing: Yes (mask-based)

### Google Gemini Models

**gemini-2.0-flash-preview-image-generation**
- Aspect Ratios: `1:1`, `16:9`, `9:16`, `4:3`, `3:4`
- Quality: Not supported
- Max Images (n): 4
- Editing: Yes (prompt-based)

## Provider Setup

### LiteLLM Setup (Recommended)

1. Deploy LiteLLM proxy (Docker recommended):
```yaml
services:
  litellm:
    image: ghcr.io/berriai/litellm:latest
    ports:
      - "4000:4000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
```

2. Configure this API:
```env
LITELLM_BASE_URL=http://litellm:4000
```

3. Models are auto-discovered from LiteLLM

### Direct API Setup

For fallback or without LiteLLM:

```env
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
```

Set `provider="openai"` or `provider="gemini"` in requests.

## Request Parameters

### Provider Selection

```json
{
  "provider": "litellm"  // or "openai", "gemini"
}
```

- `litellm`: Routes through LiteLLM proxy (recommended)
- `openai`: Direct OpenAI API call
- `gemini`: Direct Gemini API call

### Model Selection

```json
{
  "model": "dall-e-3"  // or null for auto-select
}
```

Leave `null` to use first available model for provider.

### Aspect Ratios

```json
{
  "aspect_ratio": "16:9"
}
```

Options: `1:1`, `16:9` (landscape), `9:16` (portrait), `4:3`, `3:4`

Model compatibility:
- dall-e-2: `1:1` only
- dall-e-3: `1:1`, `16:9`, `9:16`
- gpt-image-1: `1:1`, `16:9`, `9:16`
- Gemini models: All ratios

### Quality

```json
{
  "quality": "hd"  // or "standard"
}
```

- `standard`: Faster generation
- `hd`: Higher detail (dall-e-3 only)

### Number of Images

```json
{
  "n": 4
}
```

Constraints:
- dall-e-3: max 1
- Others: max 4

## Image Editing

The `/edit` endpoint supports two editing modes:

### Mask-based Editing (OpenAI)

Used with `dall-e-2` and `gpt-image-1`. Requires:
- `image`: Source image (upload or URL)
- `mask`: PNG with transparent areas marking regions to edit
- `prompt`: Description of what to generate in masked area

The mask should have transparent (alpha=0) pixels where editing should occur.

### Prompt-based Editing (Gemini)

Used with `gemini-2.0-flash-preview-image-generation`. Requires:
- `image`: Source image (upload or URL)
- `prompt`: Natural language description of the edit

No mask needed - Gemini understands what to change from the prompt alone.

### Input Methods

Images can be provided two ways:
- **File upload**: `image=@photo.png` (multipart form)
- **URL reference**: `image_url=http://localhost:8000/images/abc.png`

URL reference works with previously generated images or external URLs.

## Authentication

### No Authentication

Leave `API_BEARER_TOKEN` empty. All requests allowed.

### Bearer Token Authentication

1. Generate secure token:
```bash
openssl rand -base64 32
```

2. Set in `.env`:
```env
API_BEARER_TOKEN=your-generated-token
```

3. Include in requests:
```bash
curl -H "Authorization: Bearer your-generated-token" \
  http://localhost:8000/generate
```

## Storage Options

### Local Storage (Default)

Images saved to `STORAGE_PATH` and served via `/images/` endpoint.

Docker volume mount:
```yaml
volumes:
  - ./generated_images:/app/generated_images
```

### Custom Base URL

For reverse proxy or custom domain:

```env
IMAGE_BASE_URL=https://api.yourdomain.com
```

Images will be served at: `https://api.yourdomain.com/images/filename.png`

## Health Check

Endpoint: `GET /health`

Response:
```json
{
  "status": "healthy",
  "litellm": true,
  "openai": true,
  "gemini": false
}
```

- `litellm`: LiteLLM connectivity
- `openai`: OpenAI API key configured
- `gemini`: Gemini API key configured

## Model Refresh

Force reload models from LiteLLM:

```bash
curl -X POST http://localhost:8000/models/refresh \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

Use after LiteLLM configuration changes.

## Troubleshooting

**Models not loading**
- Check `LITELLM_BASE_URL` is accessible
- Verify LiteLLM is running: `curl http://litellm:4000/health`
- Check logs for connection errors

**Generation fails**
- Verify API keys are correct
- Check model availability: `GET /models`
- Review provider status: `GET /health`

**Images not accessible**
- Verify `STORAGE_PATH` has write permissions
- Check `BASE_URL` matches your deployment
- For Docker, ensure volume is mounted correctly
