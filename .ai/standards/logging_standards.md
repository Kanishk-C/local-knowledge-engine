# Logging and Observability Standards

> Local Knowledge Engine (LKE) — standards for logging, timing, and operational visibility.

---

## Library

- **Loguru** is the logging library (replaces stdlib `logging`).
- Use a **single logger instance** (`from loguru import logger`). Do not create custom loggers.
- Loguru is configured once at application startup in the CLI/entrypoint layer.

---

## Log Levels

Use levels consistently across the codebase. Each level has a specific purpose:

| Level    | Purpose                                                    | Example                                      |
|----------|------------------------------------------------------------|----------------------------------------------|
| TRACE    | Verbose debug output for tracing execution flow            | Entering/exiting functions, intermediate values |
| DEBUG    | Developer-relevant diagnostic information                  | Config values loaded, adapter initialized     |
| INFO     | Operational events — the system is doing what it should    | Document indexed, search completed, vault scanned |
| WARNING  | Recoverable issues — the system continues but something is off | Missing optional field, slow response, retry  |
| ERROR    | Operation failures — a specific action failed              | Embedding request failed, parse error         |
| CRITICAL | System-breaking failures — the application cannot continue | Database connection lost, config file missing |

### Level Selection Guidelines

- If the message is useful only during active debugging, use **DEBUG** or **TRACE**.
- If the message confirms a successful operation, use **INFO**.
- If the system can continue but something unexpected happened, use **WARNING**.
- If a user-requested operation failed, use **ERROR**.
- If the entire application must stop, use **CRITICAL**.

---

## Structured Fields

Every log message **must** include these fields as structured key-value pairs:

### Required Fields

| Field       | Type   | Description                              |
|-------------|--------|------------------------------------------|
| `module`    | `str`  | Source module name (e.g., `index_service`, `ollama_adapter`) |
| `operation` | `str`  | What was being attempted (e.g., `embed_document`, `search_index`, `parse_frontmatter`) |

### Optional Fields

| Field            | Type    | Description                                             |
|------------------|---------|---------------------------------------------------------|
| `document_path`  | `str`   | Path to the document being processed                    |
| `document_id`    | `str`   | Unique identifier of the document                       |
| `error_category` | `str`   | One of: `transient`, `permanent`, `partial`             |
| `duration_ms`    | `float` | Elapsed time in milliseconds                            |
| `count`          | `int`   | Number of items processed/returned                      |
| `correlation_id` | `str`   | Shared ID for related operations (see Correlation below) |

### Example

```
logger.info(
    "Document indexed successfully",
    module="index_service",
    operation="index_document",
    document_path="/vault/notes/example.md",
    document_id="abc123",
    duration_ms=142.5,
)
```

---

## Log Format

### Development

Human-readable, colored output for terminal use:

```
2025-01-15 10:23:45.123 | INFO | index_service | index_document | Document indexed successfully | duration_ms=142.5
```

### Production / CI

JSON format for machine parsing and log aggregation:

```json
{
  "timestamp": "2025-01-15T10:23:45.123Z",
  "level": "INFO",
  "module": "index_service",
  "operation": "index_document",
  "message": "Document indexed successfully",
  "duration_ms": 142.5,
  "document_id": "abc123"
}
```

- Format selection is controlled by application configuration (`log_format = "json" | "human"`).

---

## Performance Timing

Key operations must be timed and the duration logged. Use a `@timed` decorator or context manager pattern.

### Operations That Must Be Timed

| Operation              | Level |
|------------------------|-------|
| Document parsing       | DEBUG |
| Embedding generation   | DEBUG |
| Vector search          | INFO  |
| Index build/rebuild    | INFO  |
| Full vault scan        | INFO  |
| Database queries       | DEBUG |

### Pattern

```
# Decorator approach
@timed(operation="embed_document", module="ollama_adapter")
def embed(self, text: str) -> list[float]: ...

# Context manager approach
with timed_operation("search_index", module="search_service"):
    results = self._storage.search(query_vector, limit=10)
```

The timing utility logs `duration_ms` automatically on completion.

---

## Sensitive Data

### NEVER Log

- File contents or document text
- Embedding vectors
- Full LLM prompts or responses
- API keys or tokens
- User-specific filesystem paths beyond the vault root

### Safe to Log

- File paths (relative to vault root)
- Document IDs
- Operation names and results (success/failure)
- Counts and durations
- Model names and configuration values
- Error messages and exception types

---

## Log Rotation

- Configurable via application settings.
- Defaults:

| Setting        | Default Value |
|----------------|---------------|
| Max file size   | 10 MB         |
| Max rotations   | 5             |
| Compression     | gzip          |

- Log files are stored in the LKE data directory (configurable, default: `~/.lke/logs/`).

---

## Correlation

Operations triggered by the same event (e.g., a file change triggering parse → embed → index) must share a **correlation_id**.

### Rules

- Generate a `correlation_id` (UUID4) at the entry point of each pipeline invocation.
- Pass it through all service calls in the pipeline.
- Include it in every log message for that pipeline run.

### Example Flow

```
# File change detected → generates correlation_id
correlation_id = "f47ac10b-58cc"

# All subsequent log messages include it:
INFO  | watcher       | file_changed     | correlation_id=f47ac10b-58cc | path=notes/new.md
DEBUG | parser        | parse_document   | correlation_id=f47ac10b-58cc | duration_ms=12
DEBUG | ollama_adapter| embed_document   | correlation_id=f47ac10b-58cc | duration_ms=230
INFO  | index_service | index_document   | correlation_id=f47ac10b-58cc | duration_ms=310
```

This enables tracing a single file change through the entire processing pipeline.

---

## Error Logging

When logging errors:

1. **Always include the exception type and message.**
2. **Always include relevant context** (document path, operation name, what was attempted).
3. **Classify the error** using `error_category`:
   - `transient` — likely to succeed on retry (network timeout, temporary unavailability)
   - `permanent` — will not succeed on retry (invalid file format, missing required field)
   - `partial` — operation partially succeeded (3 of 5 documents indexed)
4. **Stack traces** are logged at **DEBUG level** (not ERROR) to avoid noisy output. The ERROR message itself should contain enough context to understand the failure.

### Example

```
logger.error(
    "Failed to generate embedding",
    module="ollama_adapter",
    operation="embed_document",
    document_path="notes/example.md",
    error_category="transient",
    exception_type="ConnectionError",
    exception_message="Connection refused",
)
logger.debug("Full stack trace for embedding failure", exc_info=True)
```

---

## Audit Log

Key operations are logged at **INFO level** as audit events for operational traceability:

| Audit Event         | Trigger                              |
|---------------------|--------------------------------------|
| `document_indexed`  | A document was successfully indexed  |
| `document_deleted`  | A document was removed from the index |
| `index_rebuilt`     | The full index was rebuilt           |
| `config_changed`    | Application configuration was modified |
| `vault_registered`  | A new vault was added to the system  |
| `vault_removed`     | A vault was removed from the system  |

Audit log entries should include enough context to answer "who did what, when, and to what" — typically the operation name, target (document/vault), timestamp, and result.
