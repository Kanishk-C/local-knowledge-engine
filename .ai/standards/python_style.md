# Python Coding Standards

> Local Knowledge Engine (LKE) — Python style guide and coding conventions.

---

## Python Version

- **Minimum version: Python 3.13+**
- Use modern syntax features available in 3.13:
  - `X | Y` union syntax instead of `Union[X, Y]`
  - Built-in generics: `list[str]`, `dict[str, int]`, `tuple[int, ...]` — never `List`, `Dict`, `Tuple` from `typing`
  - `match`/`case` statements where they improve clarity over `if`/`elif` chains (e.g., dispatching on enum values, parsing structured data)
  - `type` statement for type aliases where appropriate

---

## Type Hints

### Requirements

- **All public functions** must have type annotations on every parameter and the return type.
- **All class attributes** (including dataclass fields and Pydantic model fields) must be annotated.
- Private/internal helper functions should be annotated where non-obvious.

### Guidelines

- Use `typing.Protocol` to define interfaces (ports). Never use `ABC` for interface-only types.
- Use `typing.TypeAlias` (or the `type` statement) for complex type expressions to improve readability:

  ```
  type DocumentId = str
  type EmbeddingVector = list[float]
  type SearchResults = list[tuple[DocumentId, float]]
  ```

- **No `Any`** except in genuinely dynamic contexts such as raw config dictionaries or plugin boundaries. Every use of `Any` must include a comment explaining why.
- Use `Self` (from `typing`) for methods that return their own class.
- Use `Never` for functions that always raise.
- Prefer `X | None` over `Optional[X]`.

---

## Type Checker

- **mypy in strict mode** (`--strict`) is the project type checker.
- **Zero type errors** are required in CI. No `# type: ignore` without a trailing error code and justifying comment:

  ```python
  value = external_lib.get()  # type: ignore[no-untyped-call]  # third-party lib lacks stubs
  ```

- mypy configuration lives in `pyproject.toml` under `[tool.mypy]`.

---

## Linter and Formatter

- **ruff** is the single tool for linting, formatting, and import sorting (replaces flake8, black, and isort).
- Configuration lives in `pyproject.toml` under `[tool.ruff]`.
- All ruff warnings must be resolved before merge. No `# noqa` without a justifying comment.

---

## Naming Conventions

| Element              | Convention         | Example                        |
|----------------------|--------------------|--------------------------------|
| Functions/methods    | `snake_case`       | `parse_document`, `get_config` |
| Variables            | `snake_case`       | `file_path`, `doc_count`       |
| Classes              | `PascalCase`       | `DocumentParser`, `VaultIndex` |
| Constants            | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `DEFAULT_MODEL` |
| Private members      | `_prefixed`        | `_connection`, `_parse_header` |
| Type aliases         | `PascalCase`       | `DocumentId`, `SearchResults`  |
| Protocol interfaces  | `PascalCase`       | `EmbeddingPort`, `SearchPort`  |

- Boolean variables and parameters should read as predicates: `is_indexed`, `has_frontmatter`, `should_reindex`.
- Avoid abbreviations except universally understood ones (`id`, `db`, `config`, `doc`).

---

## Import Order

Imports must follow this order, with each group separated by a single blank line:

1. **Standard library** (`os`, `pathlib`, `dataclasses`, ...)
2. **Third-party packages** (`pydantic`, `loguru`, `lancedb`, ...)
3. **Local project imports** (`lke.domain.models`, `lke.application.services`, ...)

This order is enforced by ruff's isort rules (`I` rule set). Relative imports are allowed within the same package but discouraged across packages.

---

## Docstrings

- **Style: Google style.**
- **Required on:** all public classes, methods, functions, and modules.
- Private methods: optional, but recommended for complex logic.

### Template

```python
def search_documents(
    query: str,
    *,
    limit: int = 10,
    min_score: float = 0.5,
) -> list[SearchResult]:
    """Search indexed documents by semantic similarity.

    Embeds the query string and performs a vector similarity search
    against the document index.

    Args:
        query: Natural language search query.
        limit: Maximum number of results to return.
        min_score: Minimum similarity score threshold (0.0–1.0).

    Returns:
        List of search results ordered by descending similarity score.

    Raises:
        IndexNotReadyError: If the index has not been built yet.
        EmbeddingError: If the embedding model fails to process the query.
    """
```

- Include `Args`, `Returns`, and `Raises` sections where applicable.
- Omit empty sections (e.g., don't include `Raises:` if nothing is raised).
- Class docstrings should describe the purpose and responsibilities, not implementation details.

---

## String Formatting

- **f-strings are the preferred** string formatting method:

  ```python
  logger.info(f"Indexed {count} documents in {duration_ms}ms")
  ```

- Do not use `.format()` or `%` formatting. The only exception is Loguru's lazy formatting syntax, which is acceptable:

  ```python
  logger.debug("Processing document: {}", document_path)
  ```

---

## Data Classes and Models

- **Value objects** (immutable domain data): use `@dataclass(frozen=True, slots=True)`:

  ```python
  @dataclass(frozen=True, slots=True)
  class DocumentId:
      value: str
  ```

- **Validated configuration objects**: use Pydantic `BaseModel` with `model_config = ConfigDict(frozen=True)`:

  ```python
  class EmbeddingConfig(BaseModel):
      model_config = ConfigDict(frozen=True)
      model_name: str
      dimensions: int = 768
  ```

- Do not use plain dictionaries for structured data. Always define a class.

---

## Error Handling

- **Never catch bare `except:`** — always specify the exception type.
- **Never silently swallow errors** — always log the exception at minimum.
- Catch exceptions at the narrowest scope possible.
- Use custom exception classes for domain errors, inheriting from a project base exception.
- Re-raise unknown exceptions after logging context.

### Example

```python
# GOOD
try:
    result = embedding_client.embed(text)
except ConnectionError as exc:
    logger.error(f"Embedding service unreachable: {exc}")
    raise EmbeddingError("Failed to generate embedding") from exc

# BAD — never do this
try:
    result = embedding_client.embed(text)
except:
    pass
```

---

## Line and Length Limits

| Metric              | Limit   | Enforcement   |
|----------------------|---------|---------------|
| Max line length      | 99 chars | ruff (hard)   |
| Max function length  | ~30 lines | guideline     |
| Max file length      | ~300 lines | guideline    |

- If a function exceeds ~30 lines, consider extracting helper functions.
- If a file exceeds ~300 lines, consider splitting into sub-modules.
- These are guidelines to trigger review, not hard enforcement.

---

## State and Dependency Management

### No Global Mutable State

- All state must live in explicitly constructed objects.
- No module-level mutable variables (e.g., no `_cache = {}` at module scope).
- Module-level constants (`UPPER_SNAKE_CASE`, immutable) are fine.

### Dependency Injection

- Dependencies are provided via **constructor parameters**, not imported globals.
- Services receive their ports/adapters through `__init__`:

  ```python
  class IndexService:
      def __init__(
          self,
          embedding_port: EmbeddingPort,
          storage_port: StoragePort,
          config: IndexConfig,
      ) -> None:
          self._embedding_port = embedding_port
          self._storage_port = storage_port
          self._config = config
  ```

- Composition root (where objects are wired together) lives in the CLI/entrypoint layer.
