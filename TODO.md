# TODO - openapi-image-gen

## 1. Investigation & General Improvements
Status: DONE

Fix security and code quality issues found during review:
- Use `secrets.compare_digest()` for bearer token comparison
- Add basic SSRF guard to `storage_service.get_image()` (block metadata IPs, private ranges)
- Fix CORS: don't combine `allow_origins=["*"]` with `allow_credentials=True`
- Sanitize filenames extracted from URLs (even though UUIDs, harden the path)
- Extract duplicated MIME type dict and OPENWEBUI_MODE response logic into helpers
- Replace sync `open()` with `aiofiles` in async route handlers
- Fix Dockerfile: add `COPY pyproject.toml .` so version reading works in container
- Add async lock to model registry cache
- Bump stale dependency versions where appropriate

## 2. Add New Models
Status: DONE

Add models released since the last update:
- OpenAI: gpt-image-1 variants, any new DALL-E models
- Google: gemini-2.0-flash-preview-image-generation updates, newer Gemini image models, Imagen 3 updates
- Update KNOWN_CAPABILITIES in model_registry.py
- Update documentation tables
- Test with LiteLLM model discovery

## 3. Improve OWUI Image Display
Status: DONE

Added Open WebUI file upload integration:
- Images uploaded directly to OWUI via `POST /api/v1/files/` when `OPENWEBUI_BASE_URL` + `OPENWEBUI_API_KEY` configured
- Returns JSON with OWUI file URL — images display natively in chat (with download/save)
- Graceful fallback to base64 HTMLResponse when OWUI upload not configured or fails
- Eliminated dependency on `ENABLE_CHAT_RESPONSE_BASE64_IMAGE_URL_CONVERSION` setting
