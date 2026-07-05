# Architecture Rules

> Local Knowledge Engine (LKE) — structural rules that must never be violated.

---

## Dependency Direction

The system follows the **Dependency Inversion Principle**. Dependencies flow inward — outer layers depend on inner layers, never the reverse.

```
┌─────────────────────────────────────────────┐
│                 CLI Layer                    │
│          (depends on Application)            │
├─────────────────────────────────────────────┤
│            Infrastructure Layer              │
│   (depends on Domain — implements ports)     │
├─────────────────────────────────────────────┤
│            Application Layer                 │
│         (depends on Domain only)             │
├─────────────────────────────────────────────┤
│              Domain Layer                    │
│         (depends on NOTHING)                 │
└─────────────────────────────────────────────┘
```

### Rules

| Layer          | May Depend On       | Must NOT Depend On                  |
|----------------|---------------------|-------------------------------------|
| Domain         | Nothing             | Application, Infrastructure, CLI    |
| Application    | Domain              | Infrastructure, CLI                 |
| Infrastructure | Domain              | Application, CLI                    |
| CLI            | Application         | Domain internals, Infrastructure    |

- **Domain depends on NOTHING external.** No imports from `application`, `infrastructure`, `cli`, or any third-party library (except stdlib and typing).
- **Application depends on Domain ONLY.** Application services orchestrate domain logic through injected ports. No direct imports from `infrastructure`.
- **Infrastructure depends on Domain.** Adapters implement domain ports (Protocols). They may import third-party libraries (lancedb, duckdb, ollama, etc.).
- **CLI depends on Application.** The CLI layer calls application services and formats output. It never reaches into domain internals or infrastructure directly.

---

## No Circular Imports

- **Circular imports between layers are forbidden.** If module A imports from module B and module B imports from module A, this is a structural defect.
- Enforce with **import-linter** configuration or architectural tests that validate import graphs.
- Within a single layer, circular imports should also be avoided. If unavoidable, restructure by extracting shared types into a separate module.

---

## Layer Contents

### Domain Layer (`lke/domain/`)

The domain layer is the core of the system. It contains pure business logic with zero external dependencies.

- **Models**: Entities and aggregates (e.g., `Document`, `Vault`, `SearchResult`)
- **Value Objects**: Immutable data holders (e.g., `DocumentId`, `VaultPath`, `EmbeddingVector`)
- **Events**: Domain events representing state changes (e.g., `DocumentIndexed`, `DocumentDeleted`)
- **Ports**: `typing.Protocol` interfaces that define how the domain interacts with the outside world (e.g., `EmbeddingPort`, `StoragePort`, `SearchPort`)
- **Domain Services**: Pure functions or stateless classes that implement business rules. No I/O, no side effects.

**The domain layer must be testable with zero infrastructure — no database, no filesystem, no network.**

### Application Layer (`lke/application/`)

The application layer orchestrates domain logic with infrastructure through injected ports.

- **Application Services**: Coordinate multi-step operations (e.g., `IndexService.index_document()` calls parse → embed → store).
- **Use Cases**: Each public method represents a single use case.
- **No direct DB calls.** No SQL, no LanceDB queries.
- **No HTTP calls.** No Ollama client usage.
- **No file I/O.** No `open()`, no `pathlib.Path.read_text()`.
- All external operations happen through injected Protocol implementations.

### Infrastructure Layer (`lke/infrastructure/`)

The infrastructure layer contains concrete implementations of domain ports.

- **Adapters**: Each adapter implements one or more domain Protocols. Each adapter lives in its own module:
  - `ollama_adapter.py` — implements `EmbeddingPort`
  - `lancedb_adapter.py` — implements `VectorStoragePort`
  - `duckdb_adapter.py` — implements `MetadataStoragePort`
  - `filesystem_adapter.py` — implements `FileSystemPort`
- Adapters **may use third-party libraries** (this is where `lancedb`, `duckdb`, `ollama`, etc. are imported).
- Adapters are responsible for translating between domain types and infrastructure-specific types.

### CLI Layer (`lke/cli/`)

The CLI layer is a thin adapter between the user and the application.

- Maps user input (commands, arguments, options) → application service method calls.
- Formats application service return values → user-readable output (tables, JSON, progress bars).
- **No business logic.** If you're writing an `if` statement that makes a domain decision in the CLI layer, it belongs in the application or domain layer.
- Uses Typer for command definition and Rich for output formatting.

---

## Interface Communication

- **All inter-layer communication goes through interfaces** (`typing.Protocol`).
- Never depend on concrete adapter implementations in application or domain code.
- The composition root (wiring) lives in the CLI/entrypoint layer, where concrete adapters are instantiated and injected into application services.

### Example

```
# Domain defines the port
class EmbeddingPort(Protocol):
    def embed(self, text: str) -> list[float]: ...

# Application depends on the port
class IndexService:
    def __init__(self, embedding: EmbeddingPort) -> None: ...

# Infrastructure implements the port
class OllamaEmbeddingAdapter:
    def embed(self, text: str) -> list[float]: ...  # concrete implementation

# CLI wires it together
adapter = OllamaEmbeddingAdapter(config)
service = IndexService(embedding=adapter)
```

---

## Configuration

- Configuration is **loaded once at startup** and is **immutable at runtime**.
- Use Pydantic `BaseModel` with `frozen=True` for config objects.
- Config is read from TOML files, validated, and injected into services via constructors.
- No runtime config mutations. No global config singletons. If a service needs config, it receives it through its constructor.

---

## Simplicity Constraints (v0.1.0)

- **Direct method calls** between services. No event bus, no message queue, no async/await.
- Synchronous execution throughout. Async will be introduced in a future version if profiling shows it's needed.
- No microservices, no RPC. Single-process architecture.
- Keep it simple. Add complexity only when there is a measured need.

---

## Documentation

- **Every public interface must have a docstring** (Google style).
- Protocol methods must document their contract: what they accept, what they return, what errors they raise, and any preconditions.
- Module-level docstrings should describe the module's responsibility and its place in the architecture.

---

## Size Constraints

### No God Objects

- Any class with **more than 7 constructor parameters** should be reviewed for splitting.
- Any class with **more than 10 public methods** should be reviewed for splitting.
- These are signals, not hard rules — but they require explicit justification if exceeded.

### Single Responsibility

- Each module has **one reason to change**.
- If a module is modified for two unrelated features, it should be split.
- Each class has a single, clearly stated purpose documented in its docstring.

---

## New Dependencies

- **Every new dependency requires an Architecture Decision Record (ADR)** justifying the addition.
- ADRs live in `.ai/decisions/` and follow the standard ADR format.
- Evaluate before adding:
  - Can this be done with stdlib?
  - Can an existing dependency cover this?
  - What is the maintenance health of the package?
  - What is its license? (Must be MIT/Apache-2.0/BSD compatible)
  - Does it support Python 3.13+?
  - What is its transitive dependency footprint?
