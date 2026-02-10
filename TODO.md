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
Status: PENDING

Current approach returns HTMLResponse with base64-encoded `<img>` tag — a workaround
that went through several iterations. OWUI has had updates since; investigate:
- Check current OWUI tool response handling (artifact display, image rendering)
- See if OWUI now natively supports image URLs or base64 in tool responses without HTML hack
- Consider using OWUI's file upload API to store images there directly
- Reduce unnecessary disk I/O (currently writes to disk then reads back for base64)
- Test with latest OWUI version and document the recommended setup
