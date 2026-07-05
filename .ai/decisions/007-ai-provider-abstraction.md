# ADR-007: AI Provider Abstraction

**Status:** Accepted
**Date:** 2026-07-05
**Deciders:** Architecture Team

## Context

The Local Knowledge Engine uses Ollama for two core AI capabilities: generating embeddings for semantic search and generating text for entity extraction and summarization. However, the system must remain **vendor-neutral**. Locking the application to a single AI platform (Ollama, OpenAI, vLLM, llama.cpp) creates fragility and limits deployment options.

The initial architecture placed entity extraction directly on the AI provider interface. This violates the **Interface Segregation Principle (ISP)** — a provider that only supports embeddings (e.g., a dedicated embedding server) would be forced to implement entity extraction methods it cannot fulfill. Entity extraction is an application-layer concern that combines prompt engineering, response parsing, and domain knowledge. It does not belong on a transport-level provider interface.

Additionally, different providers have different capabilities. Ollama may have certain models pulled locally; an OpenAI provider has different context limits. The system must detect what a provider actually supports rather than assuming based on configuration.

## Decision

The `AIProvider` Protocol defines exactly **three responsibilities**:

### 1. `embed(texts: list[str]) -> list[EmbeddingVector]`

Generate embedding vectors for a batch of input texts. The provider handles batching internally if the underlying API has batch size limits.

### 2. `generate(prompt: str, system_prompt: str | None = None) -> str`

Generate text from a prompt with an optional system prompt. This is a synchronous, single-turn generation. The provider does not maintain conversation state.

### 3. `capabilities() -> ProviderCapabilities`

Report what the provider actually supports. This is called **once at startup** to detect the provider's capabilities rather than discovering failures at runtime.

The `ProviderCapabilities` value object includes:

| Field | Type | Description |
|---|---|---|
| `supports_embedding` | `bool` | Whether the provider can generate embeddings |
| `supports_generation` | `bool` | Whether the provider can generate text |
| `embedding_models` | `list[str]` | Available embedding models |
| `generation_models` | `list[str]` | Available generation models |
| `max_context_tokens` | `int` | Maximum context window size in tokens |
| `max_batch_size` | `int` | Maximum number of texts per embedding batch |

### Capability Detection at Startup

At application startup, the system calls `capabilities()` to verify the provider is correctly configured:

- If the configured embedding model is not in `embedding_models`, emit a warning with actionable guidance (e.g., "Model 'nomic-embed-text' not found. Run `ollama pull nomic-embed-text` to install it.").
- If `supports_embedding` is `False` but embedding features are requested, fail fast with a clear error.
- If `supports_generation` is `False` but entity extraction is configured, warn that entity extraction will be disabled.

### Entity Extraction Is an Application-Layer Concern

Entity extraction is handled by an `EntityExtractionService` in the application layer. This service:

- Constructs prompt templates with domain-specific instructions.
- Calls `AIProvider.generate()` with the constructed prompt.
- Parses and validates the response into domain entity objects.

The AI provider has **no knowledge** of domain concepts like entities, relationships, or knowledge graphs.

## Alternatives Considered

### 1. Include `extract_entities()` on AIProvider

Add entity extraction as a fourth method on the provider interface.

**Rejected because:**
- Violates ISP — providers that only do embeddings must implement entity extraction.
- Couples the provider interface to domain concepts (entities, relationships).
- Prompt engineering and response parsing are application concerns, not transport concerns.
- Makes testing harder — mock providers must implement domain logic.

### 2. Separate `EmbeddingProvider` and `GenerationProvider` Interfaces

Split the provider into two single-responsibility protocols.

**Deferred because:**
- Correct from an ISP perspective, but over-segmented for v0.1.0 when Ollama provides both capabilities through a single connection.
- Would require two separate provider instances, two configuration blocks, two health checks.
- Can be introduced later if providers that only support one capability become common.

### 3. No Capabilities Detection

Assume the provider supports everything based on configuration file values.

**Rejected because:**
- Fails silently when models are not pulled in Ollama.
- Produces cryptic runtime errors (HTTP 404 from Ollama) instead of actionable startup warnings.
- Users waste time debugging provider connectivity issues.

## Trade-offs

| Aspect | With Capability Detection | Without |
|---|---|---|
| **Startup cost** | One additional API call to Ollama | Zero startup cost |
| **Error quality** | Clear, actionable messages at startup | Cryptic failures at runtime |
| **Provider contract** | Three methods to implement | Two methods (simpler) |
| **Domain coupling** | Provider knows nothing about entities | Provider may leak domain concepts |

Capability detection adds a minor startup cost (one API call to Ollama, typically <100ms on localhost) but prevents cryptic runtime failures that waste significantly more time to debug.

## Consequences

1. **New providers** (llama.cpp, vLLM, OpenAI) implement exactly three methods: `embed()`, `generate()`, and `capabilities()`. The barrier to adding a new provider is minimal.
2. **`EntityExtractionService`** lives in the application layer and calls `generate()` with prompt templates. It is fully testable with a mock provider that returns predetermined strings.
3. **Capability detection at startup** catches misconfiguration early. The system either starts correctly or fails with actionable guidance.
4. **The provider interface is stable.** Adding new AI capabilities (e.g., image understanding) would extend `ProviderCapabilities` and add optional methods, not change existing ones.
5. **Testing is straightforward.** A mock provider returns fixed embeddings and fixed text, with no prompt engineering or parsing logic to stub out.
