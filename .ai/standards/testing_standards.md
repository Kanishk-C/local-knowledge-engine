# Testing Standards

> Local Knowledge Engine (LKE) — testing conventions, structure, and quality requirements.

---

## Framework

- **pytest** is the only test framework. No `unittest.TestCase` subclasses.
- Use pytest idioms: plain functions, fixtures, parametrize, markers.

---

## Test Types

| Type        | Purpose                                      | I/O Allowed | Speed Target     |
|-------------|----------------------------------------------|-------------|------------------|
| Unit        | Test individual functions/classes in isolation | No          | < 1s per test    |
| Integration | Test real adapters with real DBs/filesystem   | Yes         | < 10s per test   |
| E2E         | Test full pipelines end-to-end                | Yes         | Reasonable       |

### Unit Tests

- Fast, isolated, no I/O (no filesystem, no network, no database).
- All dependencies injected as fakes/stubs.
- Cover domain logic, application services, and pure utility functions.

### Integration Tests

- Exercise real infrastructure adapters (LanceDB, DuckDB, filesystem).
- Use temporary directories and in-memory databases where possible.
- Must clean up all resources on completion (temp dirs, DB files).

### E2E Tests

- Test the full pipeline from CLI input to observable output.
- May invoke Ollama (use lightweight models or mocks in CI).
- Run in a dedicated CI job, not on every commit.

---

## Test Directory Structure

```
tests/
├── conftest.py              # Root-level shared fixtures
├── unit/
│   ├── conftest.py          # Unit test fixtures
│   ├── domain/
│   │   ├── test_models.py
│   │   └── test_services.py
│   └── application/
│       └── test_index_service.py
├── integration/
│   ├── conftest.py          # Integration fixtures (DB setup, tmp dirs)
│   ├── test_lancedb_adapter.py
│   └── test_duckdb_adapter.py
├── e2e/
│   ├── conftest.py
│   └── test_index_pipeline.py
└── fixtures/
    ├── sample_vault/        # Sample Obsidian vault for testing
    ├── documents/           # Sample markdown files
    └── configs/             # Sample TOML configs
```

- Mirror the source tree structure within each test type directory.
- Shared test data goes in `tests/fixtures/` and is committed to the repo.

---

## Naming Conventions

### Test Files

- Name: `test_{module_name}.py` (e.g., `test_document_parser.py`)

### Test Functions

- Pattern: `test_{method}_{scenario}_{expected_result}`
- Be descriptive — the test name should explain the behavior being verified.

Examples:

```
test_parse_document_with_valid_frontmatter_returns_metadata
test_parse_document_with_missing_title_uses_filename
test_search_with_empty_query_raises_validation_error
test_index_document_when_already_indexed_skips_reindex
```

---

## Fixtures

- Use **pytest fixtures** for all setup and teardown. No `setUp`/`tearDown` methods.
- Place shared fixtures in `conftest.py` at the appropriate directory level:
  - `tests/conftest.py` — fixtures used across all test types
  - `tests/unit/conftest.py` — fixtures for unit tests only
  - `tests/integration/conftest.py` — fixtures for integration tests (DB connections, temp dirs)
- Use the narrowest fixture scope that works:
  - `function` (default) — per test
  - `module` — expensive setup shared across a test file
  - `session` — very expensive setup shared across the entire test run (e.g., database schemas)
- Fixture names should describe what they provide, not how they're built:

  ```
  # GOOD
  @pytest.fixture
  def sample_document() -> Document: ...

  # BAD
  @pytest.fixture
  def setup_document() -> Document: ...
  ```

---

## Mocking Strategy

### Prefer Dependency Injection Over Mocking

- The architecture uses Protocol-based ports. For testing, create **test doubles** (fakes, stubs) that implement the same Protocol.
- This avoids brittle mock assertions and tests the actual interface contract.

### When to Use `unittest.mock.patch`

- **Only at external boundaries** that cannot be injected:
  - Ollama HTTP calls (when not using a fake client)
  - Filesystem operations in legacy code
  - System clock (`time.time`, `datetime.now`)
- Every use of `patch` should include a comment explaining why DI was not feasible.

### Example: Fake vs. Mock

```
# PREFERRED: Fake that implements the Protocol
class FakeEmbeddingPort:
    def embed(self, text: str) -> list[float]:
        return [0.1] * 768

# AVOID unless necessary
with patch("lke.infrastructure.ollama_client.embed") as mock_embed:
    mock_embed.return_value = [0.1] * 768
```

---

## Coverage

| Layer                    | Coverage Target | Enforcement    |
|--------------------------|-----------------|----------------|
| Domain                   | ≥ 80%           | CI gate        |
| Application              | ≥ 80%           | CI gate        |
| Infrastructure / CLI     | Not gated       | Integration tests cover these |

- Measured by **coverage.py** with the pytest-cov plugin.
- Coverage on **changed files** in a PR must be ≥ 80%.
- Aim for meaningful coverage — test behavior, not implementation. Don't write tests just to hit a number.

---

## Test Speed

| Suite         | Target Wall Time |
|---------------|------------------|
| Unit tests    | < 30 seconds     |
| Single unit   | < 1 second       |
| Single integration | < 10 seconds |

- Slow tests indicate a design problem (hidden I/O, expensive setup).
- If a unit test is slow, it's probably an integration test — move it.

---

## CI Configuration

- **Separate CI jobs** for unit and integration tests.
- Default `pytest` invocation (no markers) runs **unit tests only**.
- Integration tests require the `@pytest.mark.integration` marker and are run with `pytest -m integration`.
- E2E tests require `@pytest.mark.e2e` and run in a dedicated pipeline stage.
- All tests must pass before merge to `main`.

---

## Markers

Register all custom markers in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "integration: tests that require real databases or filesystem",
    "e2e: end-to-end tests that exercise the full pipeline",
    "slow: tests that take >5s (excluded from default runs)",
]
```

Default run excludes integration and e2e:

```toml
addopts = "-m 'not integration and not e2e'"
```

---

## Test Data

- Store reusable test data in `tests/fixtures/`.
- Sample vaults, markdown files, TOML configs — all committed to the repository.
- Do not generate test data at test time unless testing randomized/property-based behavior.
- Use meaningful, realistic data — not `"test"`, `"foo"`, `"bar"`.

---

## Property-Based Testing

- Consider **Hypothesis** for domain model validation:
  - Document ID format validation
  - Frontmatter parsing edge cases
  - Search score normalization
- Property tests complement (not replace) example-based tests.
- Use `@settings(max_examples=100)` to keep test times reasonable.

---

## Flaky Tests

- **No flaky tests.** Any test that fails intermittently is a bug and must be fixed immediately.
- Common causes and fixes:
  - **Time-dependent**: Inject a clock, don't use `datetime.now()` directly.
  - **Order-dependent**: Ensure test isolation — no shared mutable state between tests.
  - **Resource leaks**: Always clean up temp files, DB connections, and background threads.
  - **Race conditions**: Unit tests must not use threads or async unless testing concurrency.
- If a test cannot be made reliable, delete it and file an issue to rewrite it.

---

## Resource Cleanup

- Integration tests **must** clean up all created resources:
  - Use `tmp_path` fixture for temporary directories (pytest cleans these up automatically).
  - Close all database connections in fixture teardown.
  - Remove any files created outside of `tmp_path`.
- Use `try`/`finally` or `yield` fixtures for guaranteed cleanup:

  ```
  @pytest.fixture
  def db_connection(tmp_path):
      db = DuckDB(tmp_path / "test.db")
      yield db
      db.close()
  ```
