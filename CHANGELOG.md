# CHANGELOG

<!-- version list -->

## v0.8.0 (2025-12-15)

### Features

- Simplify image response with MARKDOWN_EMBED_IMAGES config
  ([`2028018`](https://github.com/danielcopper/openapi-image-gen/commit/20280186508c4b3e0f7af75892f46355e46494d5))


## v0.7.0 (2025-12-14)

### Features

- Add JSON-based edit endpoint for LLM tool use
  ([`02781c0`](https://github.com/danielcopper/openapi-image-gen/commit/02781c0cda12846e9c231e72425a2bf0951b13cd))


## v0.6.0 (2025-12-14)

### Features

- Show DEFAULT_MODEL in OpenAPI schema
  ([`c16e04c`](https://github.com/danielcopper/openapi-image-gen/commit/c16e04ce4b163a17ee188f43befc7c989d823cc4))

### Refactoring

- Rename OPENWEBUI_API_URL to OPENWEBUI_BASE_URL
  ([`2620222`](https://github.com/danielcopper/openapi-image-gen/commit/2620222be1a3254cf77d6532bcb111411698e29b))


## v0.5.0 (2025-12-14)

### Features

- **config**: Add SAVE_IMAGES_LOCALLY option
  ([`3d48993`](https://github.com/danielcopper/openapi-image-gen/commit/3d489932f260866da3a3acd4b8043ba2edbf9a73))


## v0.4.0 (2025-12-14)

### Bug Fixes

- Resolve all ruff lint errors
  ([`606384d`](https://github.com/danielcopper/openapi-image-gen/commit/606384d9f4476e3d6f77bfac93912a15e1592df3))

### Documentation

- Add Open WebUI integration documentation
  ([`d99a5d4`](https://github.com/danielcopper/openapi-image-gen/commit/d99a5d40cd5c96177a2cef987a3ded9faf5c5bb3))

- Update documentation for image editing feature
  ([`8dde037`](https://github.com/danielcopper/openapi-image-gen/commit/8dde037e77c5d7b2c56dba18236ed7a059021c3a))

### Features

- Add Open WebUI Files API integration
  ([`d72a2ad`](https://github.com/danielcopper/openapi-image-gen/commit/d72a2ade8b36f61f37f41cfd1e066e85695e22ee))

### Testing

- Add Open WebUI service tests
  ([`61a328c`](https://github.com/danielcopper/openapi-image-gen/commit/61a328ca5ccc003dd1dddef47987a6dce46f0d4b))


## v0.3.0 (2025-12-14)

### Chores

- Remove mypy
  ([`b0961d6`](https://github.com/danielcopper/openapi-image-gen/commit/b0961d6fd67147e8e1c631355331a024039d5466))

### Code Style

- Combine nested if statements in openapi schema
  ([`145097c`](https://github.com/danielcopper/openapi-image-gen/commit/145097ced083f1d32c81e201e6f37f4fa635c8ac))

### Features

- **api**: Add /edit endpoint for image editing
  ([`7a7b096`](https://github.com/danielcopper/openapi-image-gen/commit/7a7b09676d87c0c8af9e1d113a3166183f1cba75))

- **schemas**: Add editing capabilities to ModelCapabilities
  ([`a1f8c23`](https://github.com/danielcopper/openapi-image-gen/commit/a1f8c231d5d92feffcb5336dc30205bd7f415118))

- **services**: Add edit_image to Gemini service
  ([`e44a249`](https://github.com/danielcopper/openapi-image-gen/commit/e44a249155ebfd3d86b96f2c345e247dcf41b5ca))

- **services**: Add edit_image to LiteLLM service
  ([`01d95ba`](https://github.com/danielcopper/openapi-image-gen/commit/01d95ba8e3a8de259eb6c713fcc23927d8054be6))

- **services**: Add edit_image to OpenAI service
  ([`2b34ce1`](https://github.com/danielcopper/openapi-image-gen/commit/2b34ce144f7ebb6ab8b629f0f6ea235d6192424e))

- **storage**: Add get_image method for retrieving images
  ([`a520e75`](https://github.com/danielcopper/openapi-image-gen/commit/a520e75a7ebc23ada8d42673963baa2911239d8e))

### Testing

- Add unit tests for image editing
  ([`976fb66`](https://github.com/danielcopper/openapi-image-gen/commit/976fb66f9f301b8f41f3a766fdd4ed41ca0b1170))


## v0.2.0 (2025-12-14)

### Bug Fixes

- Add auth header to LiteLLM health check
  ([`0c6edf7`](https://github.com/danielcopper/openapi-image-gen/commit/0c6edf7970933350ae10739c8ce8f690c628a302))

### Features

- Add DEFAULT_MODEL environment variable
  ([`bcd6f17`](https://github.com/danielcopper/openapi-image-gen/commit/bcd6f1799e1fa298f082808ee47ee4a22630fd92))

- Filter models to only image generation models
  ([`30f80ee`](https://github.com/danielcopper/openapi-image-gen/commit/30f80ee969d83d5c5f674f4d4ca8ff7221ad6a51))

- Rename BASE_URL to IMAGE_BASE_URL
  ([`f433e17`](https://github.com/danielcopper/openapi-image-gen/commit/f433e1748bd0f6731a944e38998cfcf77fccf4d5))


## v0.1.3 (2025-12-14)

### Bug Fixes

- **ci**: Correct semantic-release config format
  ([`9c95107`](https://github.com/danielcopper/openapi-image-gen/commit/9c95107181bcc426919da3f529c08ac8f56fc393))

- **ci**: Simplify semantic-release config
  ([`313b6e9`](https://github.com/danielcopper/openapi-image-gen/commit/313b6e96f41ea2bb95d075e2b98404a22da1915c))

- **ci**: Use python-semantic-release v10 with publish-action
  ([`c4df49b`](https://github.com/danielcopper/openapi-image-gen/commit/c4df49b12e81f4102f638fb6ac8f50398d6d9795))

### Chores

- **ci**: Setup automatic semantic-release with Docker build
  ([`57bcd63`](https://github.com/danielcopper/openapi-image-gen/commit/57bcd6393373ace69b3e4c820dd600a507cf0875))


## v0.1.2 (2025-12-14)

### Features

- Add markdown response format for chat/LLM integrations
  ([`e4a5da6`](https://github.com/danielcopper/openapi-image-gen/commit/e4a5da66b116a655289732e3d0f8df108714c6dc))


## v0.1.1 (2025-12-13)

### Bug Fixes

- Use correct google-genai package in requirements.txt
  ([`576342a`](https://github.com/danielcopper/openapi-image-gen/commit/576342a1ac427ed597c6c19898608a39001ad140))


## v0.1.0 (2025-12-13)

- Initial Release
