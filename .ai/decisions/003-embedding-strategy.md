# ADR-003: Embedding Strategy

**Status:** Accepted
**Date:** 2026-07-05
**Deciders:** Architecture Team

## Context

LKE performs semantic search across personal knowledge bases that contain mixed content — prose (notes, journal entries, research), code (scripts, configuration files, snippets), and structured data (tables, YAML frontmatter). Vector embeddings must capture the semantic meaning of this diverse content to enable similarity search, clustering, and retrieval-augmented generation (RAG).

All embedding computation must run fully locally — no API calls to external services. The system targets consumer hardware (laptops, desktops) where GPU availability is not guaranteed, so CPU inference performance is a hard constraint.

Three aspects of the embedding strategy must be decided: the embedding model, the chunking strategy, and how contextual information is encoded into chunks.

## Decision

### Embedding Model

Use **`nomic-embed-text`** via Ollama as the default embedding model.

- **Dimensions:** 768
- **Context window:** 8,192 tokens
- **Parameters:** 137M (small enough for CPU inference)
- **Matryoshka Representation Learning (MRL):** Supported — embeddings can be truncated to lower dimensions (512, 256, 128) with graceful quality degradation, enabling future storage optimization without re-indexing the model.
- **Served via Ollama:** Uses the same Ollama instance as the LLM, avoiding additional dependencies or runtime processes.

### Contextual Prefix

Each chunk is prepended with a contextual prefix before embedding to improve retrieval quality:

```
[File: {filename} | Section: {heading}]
{content}
```

This prefix encodes document-level and section-level context directly into the vector representation, allowing the embedding model to disambiguate semantically similar content from different sources. The prefix format is configurable.

### Chunking Strategy

Content-aware chunking tailored to document type:

- **Markdown:** Split on headings (H1–H6) to preserve semantic boundaries. Each heading-delimited section becomes a chunk. Sections exceeding the token limit are split at paragraph boundaries.
- **Code files:** Split on function/class boundaries where possible. Falls back to line-based splitting for languages without clear structural markers.
- **Target chunk size:** ~512 tokens with 10–20% overlap between consecutive chunks to preserve context at boundaries.
- **Chunking is pluggable:** Implemented as a domain service with a strategy pattern, allowing new document types to define their own chunking logic.

## Alternatives Considered

1. **`snowflake-arctic-embed-v2`** — Slightly better performance on code retrieval benchmarks, 1024 dimensions. However, the larger dimensionality increases storage requirements by 33% and memory usage during search. The code quality improvement is marginal for the mixed-content use case.

2. **`bge-m3`** — Supports hybrid search (dense + sparse vectors in a single model), which could eliminate the need for a separate keyword search layer. However, it has 569M parameters, requires ~2.3GB RAM for inference, and is significantly slower on CPU. Hybrid search is a future optimization, not a launch requirement.

3. **`qwen3-embedding`** — Highest quality on MTEB benchmarks among open-source models. However, inference speed on CPU is unacceptable for batch indexing of large knowledge bases. Better suited as a future option for users with GPU hardware.

4. **`all-minilm-l6-v2`** — Ultra-fast inference (384 dimensions, 22M parameters) but significantly lower quality on retrieval benchmarks. The quality gap is too large for a semantic search product where relevance is the primary user-facing metric.

5. **`sentence-transformers` library directly** — Bypasses Ollama and loads models directly via the sentence-transformers Python library. This avoids the Ollama dependency but introduces a direct PyTorch/ONNX dependency into the project, significantly increasing install size and complexity. Since LKE already depends on Ollama for LLM inference, reusing it for embeddings avoids adding a second ML runtime.

## Trade-offs

- **Quality vs. resource consumption:** `nomic-embed-text` is not the highest-quality embedding model available. Models like `qwen3-embedding` and `bge-m3` score higher on retrieval benchmarks. However, `nomic-embed-text` offers the best balance of quality, speed, and memory consumption for CPU-bound local inference. Users who need higher quality can swap models via configuration.

- **768 dimensions vs. smaller:** Higher dimensionality captures more semantic nuance but increases storage and search costs. 768 is a practical middle ground — large enough for high-quality retrieval, small enough for efficient IVF-PQ indexing in LanceDB. MRL support allows future reduction to 512 or 256 dimensions if storage becomes a constraint.

- **Contextual prefix adds tokens:** Prepending file and section information to each chunk consumes part of the model's context window and slightly increases embedding computation time. The retrieval quality improvement justifies this cost — without context, a chunk containing "merge these changes" is ambiguous (git? document editing? data processing?), but with context `[File: git-workflow.md | Section: Pull Requests]` the meaning is clear.

- **Ollama dependency for embeddings:** Routing embeddings through Ollama adds a network hop (localhost HTTP) compared to direct library calls. The latency per embedding call is ~1ms, which is negligible compared to the model inference time (~50ms per chunk on CPU). The architectural simplicity of a single ML runtime outweighs this overhead.

## Consequences

- **`AIProvider` interface abstracts the embedding model:** The domain layer defines an `AIProvider` port with an `embed()` method. The infrastructure layer implements this against Ollama. Swapping embedding models (or providers) requires changing only the infrastructure adapter and a configuration value.

- **Swapping models requires re-indexing:** Different embedding models produce vectors in incompatible vector spaces. Changing from `nomic-embed-text` to another model invalidates all existing embeddings and requires a full re-index. This is inherent to embedding-based systems and cannot be avoided without model-agnostic vector alignment (a research problem, not a practical option).

- **Chunk strategy is pluggable via domain service:** New document types can register custom chunking strategies without modifying existing code. The chunking service is a pure domain concern — it depends only on document content, not on infrastructure.

- **MRL enables future optimization:** If storage grows large, embedding dimensions can be reduced from 768 to 512 or 256 using the existing vectors (truncation, no re-embedding required). This provides a cost-free optimization path for users with very large knowledge bases.

- **Model availability must be verified at startup:** The system must check that the configured embedding model is available in Ollama before starting a batch indexing operation. If the model is missing, the system should provide a clear error message with the `ollama pull` command to resolve it.
