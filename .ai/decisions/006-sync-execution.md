# ADR-006: Synchronous Execution Model

**Status:** Accepted
**Date:** 2026-07-05
**Deciders:** Architecture Team

## Context

Python supports `async`/`await` for I/O-bound operations. The Local Knowledge Engine makes HTTP calls to Ollama for embeddings and text generation, reads files from disk, and writes to embedded databases (LanceDB, DuckDB). On paper, these are I/O-bound operations that could benefit from asynchronous execution.

However, the actual performance profile of these operations does not match the typical async use case:

- **Ollama inference** is the primary bottleneck. It is compute-bound on the Ollama server, not I/O-bound on the LKE client. The client spends most of its time waiting for the server to finish inference. Making the HTTP call async does not make inference faster — it just changes how the client waits.
- **LanceDB and DuckDB** are embedded databases with microsecond-level access times. There is no network round-trip to optimize away.
- **File reads** are local disk I/O, typically completing in single-digit milliseconds.

Additionally, v0.1.0 is a CLI tool, not a web server. There is no concurrent request handling requirement.

## Decision

v0.1.0 uses a **fully synchronous execution model**. No `async def`, no `await`, no event loop anywhere in the codebase — not in domain logic, not in application services, not in infrastructure adapters.

If batch embedding parallelism is needed (e.g., embedding 500 documents), use `concurrent.futures.ThreadPoolExecutor` to parallelize Ollama HTTP calls. This provides real parallelism for the one operation that benefits from it, without infecting the rest of the codebase.

All Protocol method signatures use regular `def`, not `async def`.

## Alternatives Considered

### 1. Async Throughout

Use `asyncio` across the entire stack — async repository methods, async services, async CLI commands.

**Rejected because:**
- Async "infects" the entire call stack. Every caller of an async function must also be async, doubling the surface area for bugs (forgotten `await`, event loop conflicts).
- The primary bottleneck (Ollama inference) is server-side compute, not client-side I/O. Async does not reduce inference time.
- Testing async code requires event loop management (`pytest-asyncio`, `@pytest.mark.asyncio`), adding friction to every test.
- Marginal benefit for a CLI tool with no concurrent request handling.

### 2. Hybrid (Async for Ollama, Sync for DB)

Use async only for Ollama HTTP calls while keeping database access synchronous.

**Rejected because:**
- Creates a leaky abstraction at the boundary between async and sync code.
- Requires `asyncio.run()` bridges or sync wrappers around async code, which are confusing and error-prone.
- Developers must reason about two execution models in the same codebase.

### 3. Threading with `concurrent.futures`

Use `ThreadPoolExecutor` for batch operations that benefit from parallelism.

**Accepted as a tactical tool** for batch embedding parallelism, if profiling demonstrates a measurable benefit. This is used at the call site, not as an architectural pattern.

## Trade-offs

| Aspect | Synchronous Model | Async Model |
|---|---|---|
| **Simplicity** | Straightforward control flow, easy to debug | Requires event loop reasoning, complex stack traces |
| **Testing** | Standard `pytest`, no event loop management | Requires `pytest-asyncio`, async fixtures |
| **Throughput** | Single-threaded for sequential operations | Potential concurrency for I/O-bound operations |
| **Future migration** | Must introduce async when HTTP API is added | Already async-ready |
| **Batch parallelism** | Achievable via `ThreadPoolExecutor` | Native with `asyncio.gather()` |

The synchronous model is simpler but single-threaded. When the HTTP API is added (post-MVP), async will be introduced at the infrastructure layer. The port/adapter architecture (ADR-004) ensures that the sync-to-async migration is **localized to infrastructure adapters** — domain logic and application services remain synchronous, and async adapters wrap them.

## Consequences

1. **All Protocol methods** in the domain layer use regular `def`, not `async def`. This is a hard rule for v0.1.0.
2. **Services are straightforward to test** with no event loop setup, no `@pytest.mark.asyncio`, no async fixtures.
3. **`ThreadPoolExecutor`** is used for batch embedding only if profiling shows a measurable benefit. It is not used speculatively.
4. **When the HTTP API is introduced** (post-MVP), async will be added at the infrastructure layer (e.g., an async FastAPI handler that calls synchronous services via `run_in_executor`). The domain and application layers do not change.
5. **No `asyncio` dependency** in v0.1.0. The event loop is never started.
