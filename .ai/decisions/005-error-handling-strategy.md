# ADR-005: Error Handling Strategy

**Status:** Accepted
**Date:** 2026-07-05
**Deciders:** Architecture Team

## Context

LKE operates as a batch processing pipeline and a long-running watch-mode daemon. Both modes encounter multiple categories of failure:

- **Infrastructure failures:** Ollama service unavailable, Ollama model not pulled, database connection errors, disk full.
- **Input failures:** Malformed Markdown frontmatter, unsupported file formats, binary files in a text-expected path, files deleted between discovery and processing.
- **Partial processing failures:** One chunk out of many fails to embed, some frontmatter fields are unparseable while others succeed, a file is readable but too large for the embedding model's context window.
- **Self-inflicted failures:** LKE writes to a file that another process locks, a database migration fails mid-schema-change.

Watch mode runs unattended for extended periods. A single failure must not crash the system, halt processing of other documents, or corrupt data. Users need visibility into what failed and the ability to retry.

## Decision

### Three Error Categories

All errors are classified into one of three categories, each with a distinct recovery strategy:

#### 1. Transient Errors

**Definition:** Errors caused by temporary conditions that are likely to resolve on their own — Ollama timeout, temporary resource exhaustion, database lock contention.

**Recovery strategy:**
- Retry with exponential backoff: 3 attempts with delays of 1s, 2s, and 4s.
- After maximum retries are exhausted, the document is queued for later processing by setting its status to `PENDING` with an incremented retry count.
- Transient errors are logged at `WARNING` level.

**Examples:** Ollama HTTP timeout, DuckDB write lock timeout, temporary file permission error during write.

#### 2. Permanent Errors

**Definition:** Errors caused by conditions that will not resolve without user intervention — malformed files, unsupported formats, missing files, invalid configuration.

**Recovery strategy:**
- Log the error at `ERROR` level with full context (file path, error type, error message).
- Mark the document as `status=ERROR` with the error details stored in DuckDB (`error_message`, `error_category`, `error_timestamp`).
- Skip the document and continue processing the rest of the batch.
- Users can view errors via `lke status` and, after fixing the underlying issue, retry via `lke index --retry-errors`.

**Examples:** YAML parse error in frontmatter, binary file where Markdown was expected, file deleted between discovery and read.

#### 3. Partial Errors

**Definition:** Errors where some parts of a document process successfully but others fail — one chunk fails to embed while others succeed, some metadata fields are extracted but others are malformed.

**Recovery strategy:**
- Process and store everything that succeeds.
- Log each individual failure at `WARNING` level.
- Mark the document as `status=PARTIAL` with details of what failed.
- Partial documents are searchable (with reduced quality) and can be fully re-processed via `lke index --retry-errors`.

**Examples:** 9 of 10 chunks embed successfully but one exceeds the token limit, frontmatter `tags` field parsed but `date` field is malformed.

### Idempotent Pipeline Steps

All pipeline steps must be idempotent: re-running the same step with the same input produces the same result and the same stored state. This is the foundation of safe retries and recovery.

- **Embeddings:** Delete-before-insert pattern. Before storing new embeddings for a document, all existing embeddings for that document are deleted from LanceDB. This prevents duplicate or stale embeddings.
- **Metadata:** Upsert pattern. Document metadata in DuckDB is inserted or updated based on the document's unique identifier (file path + content hash). Re-processing a document overwrites its metadata with the latest values.

### Ollama Health Check

At startup (and before batch operations), LKE performs a health check:

1. **Connection check:** Verify that the Ollama HTTP API is reachable at the configured address.
2. **Model availability check:** Verify that the configured embedding model (and LLM model, if applicable) is available. If not, provide a clear error message: `Model 'nomic-embed-text' not found. Run: ollama pull nomic-embed-text`.

### Graceful Degradation

If Ollama is unavailable, LKE does not shut down entirely. Instead, it disables capabilities that require Ollama and continues operating in a reduced mode:

- **Available without Ollama:** Document parsing, file watching, metadata extraction from frontmatter, cached search results (previously indexed embeddings are still searchable), `lke status`, `lke list`.
- **Unavailable without Ollama:** New embedding generation, LLM-powered metadata generation (summaries, topic classification), re-indexing.

The CLI clearly communicates the degraded state: `⚠ Ollama is not available. Embedding and LLM features are disabled. Cached search results are still available.`

## Alternatives Considered

1. **Fail-fast on any error** — Halt the entire pipeline on the first error. This is appropriate for compilation (where a single error can invalidate the entire build) but too aggressive for batch document processing. A single malformed file in a vault of 10,000 documents should not prevent the other 9,999 from being indexed.

2. **Queue-based retry with dead-letter queue** — Use a persistent job queue (e.g., an internal SQLite-backed queue) with automatic retry scheduling and a dead-letter queue for permanently failed jobs. This is architecturally correct and would scale well, but it is over-engineered for v0.1.0. The document status tracking in DuckDB provides equivalent functionality with simpler implementation. The queue-based approach can be adopted later if retry patterns become more complex.

3. **Ignore all errors (log and continue silently)** — Process what succeeds, log failures, and never track error state. This is the simplest approach but provides no user visibility into failures and no mechanism for retry. Users would not know that documents are missing from search results until they notice gaps. This is unacceptable for a tool that manages personal knowledge.

## Trade-offs

- **Per-document error tracking adds schema complexity:** The `documents` table in DuckDB requires `status`, `error_message`, `error_category`, `error_timestamp`, and `retry_count` columns. This is more complex than a simple `processed: boolean` flag, but it enables the `lke status` command and the `--retry-errors` flag — both essential for user trust in an unattended system.

- **Three categories vs. two (or one):** Three error categories is more complex to implement than a binary success/fail model. However, the distinction between transient (retry automatically), permanent (skip and report), and partial (use what works) maps directly to user expectations and produces better behavior in each case.

- **Graceful degradation increases code complexity:** Every service that uses Ollama must handle the "Ollama unavailable" case, either by checking availability before calling or by catching connection errors and returning a degraded result. This adds conditional logic throughout the application layer but prevents the worst user experience — a tool that refuses to start because a background service is temporarily down.

## Consequences

- **`DocumentRepository` needs status and error fields:** The document metadata schema must include `status` (enum: `PENDING`, `PROCESSING`, `COMPLETE`, `PARTIAL`, `ERROR`), `error_message` (text, nullable), `error_category` (enum: `TRANSIENT`, `PERMANENT`, `PARTIAL`, nullable), `error_timestamp` (datetime, nullable), and `retry_count` (integer, default 0).

- **Every service method must catch and classify exceptions:** Application-layer services cannot let exceptions propagate uncaught. Each service method must wrap infrastructure calls in try/except blocks, classify the caught exception into one of the three categories, and take the appropriate recovery action. A shared `ErrorClassifier` utility can centralize the classification logic.

- **Loguru structured logging includes error context:** All error log entries must include: error category (`TRANSIENT`, `PERMANENT`, `PARTIAL`), document path, operation that failed, and a correlation ID that links all log entries for a single document's processing run. This enables efficient debugging from logs alone.

- **`lke status` command surfaces error state:** The CLI must provide a `lke status` command that reports: total documents indexed, documents with errors (grouped by error category), and the specific error message for each failed document. This is the primary user interface for error visibility.

- **`lke index --retry-errors` enables recovery:** The CLI must support a `--retry-errors` flag that re-processes all documents with `status=ERROR` or `status=PARTIAL`. Combined with idempotent pipeline steps, this provides a safe, one-command recovery path.

- **Startup health check prevents silent failures:** By verifying Ollama connectivity and model availability at startup, the system provides immediate feedback rather than failing silently during batch processing. This is especially important for first-time users who may not have pulled the required model.
