# ADR-009: Plugin Architecture (Deferred)

**Status:** Accepted
**Date:** 2026-07-05
**Deciders:** Architecture Team

## Context

The Local Knowledge Engine is designed to be extensible across several dimensions:

- **Parsers** — new document formats (PDF, EPUB, HTML, Jupyter notebooks).
- **Output writers** — new export formats (JSON, CSV, Markdown reports).
- **AI providers** — new inference backends (llama.cpp, vLLM, OpenAI).
- **Data sources** — new ingestion sources (RSS feeds, web crawlers, API connectors).

A plugin system was designed in the initial architecture to support third-party extensions through a registry, discovery mechanism, and lifecycle manager. However, v0.1.0 has only two parsers (Markdown and Obsidian-flavored Markdown), both of which are internal code maintained by the core team.

The question is whether to build the full plugin infrastructure now or defer it.

## Decision

**Defer the plugin system to post-MVP (v0.3.0+).**

For v0.1.0:

- **Protocol interfaces ARE defined** — `Parser`, `OutputWriter`, and `AIProvider` Protocols exist in the domain layer. These define the extensibility contract that future plugins must satisfy.
- **Implementations are hardcoded** — parsers and output writers are registered directly in the dependency injection container. There is no plugin discovery, no registry, no entry point scanning.
- **No plugin infrastructure is built** — no plugin registry, no lifecycle manager, no error isolation boundary, no plugin configuration schema, no plugin versioning.

The Protocol interfaces serve as the **architectural seam** that makes future plugin support possible without requiring changes to the domain or application layers.

## Alternatives Considered

### 1. Build the Full Plugin System Now

Implement entry point discovery (PEP 621 `[project.entry-points]`), a plugin registry, lifecycle management (load, initialize, validate, teardown), error isolation, and plugin-specific configuration.

**Rejected because:**
- Building a full plugin registry for 2 internal parsers is over-engineering. The infrastructure cost is disproportionate to the extensibility need.
- Plugin systems require versioning (API compatibility between host and plugins), error isolation (a broken plugin must not crash the host), and dependency management (plugin dependencies must not conflict with host dependencies). Each of these is a significant engineering effort.
- The Protocol interfaces already provide the extensibility contract. The registry is ceremony on top of a solved problem.
- Delays MVP delivery by an estimated 2–3 weeks.

### 2. Never Build Plugins

Keep all parsers, output writers, and providers as internal code forever.

**Rejected because:**
- Limits the system's extensibility to what the core team supports.
- Forces users with niche formats (e.g., Logseq, Notion exports, Zotero libraries) to fork the project.
- Contradicts the architectural goal of being an extensible knowledge platform.

### 3. Simple `importlib`-Based Loading (v0.2.0)

A pragmatic middle ground: scan a `plugins/` directory, import modules that match a naming convention, and register classes that implement the Protocol. No lifecycle management, no error isolation.

**Considered for v0.2.0** as a stepping stone before the full plugin system. This provides basic extensibility without the full infrastructure cost.

## Trade-offs

| Aspect | Build Now | Defer |
|---|---|---|
| **Third-party extensibility** | Available immediately | Blocked until v0.3.0+ |
| **MVP delivery** | Delayed 2–3 weeks | On schedule |
| **Internal complexity** | Higher (registry, lifecycle, error isolation) | Lower (direct DI registration) |
| **Architectural risk** | Risk of premature abstraction (designing for unknown plugin needs) | Risk of architectural debt if Protocols are insufficient |
| **User value** | Minimal (no third-party plugins exist yet) | No loss (internal parsers work fine) |

The key insight is that **Protocol interfaces provide 80% of the extensibility value at 5% of the cost.** The plugin registry, discovery, and lifecycle management provide the remaining 20% of value at 95% of the cost. For v0.1.0, the 80% solution is correct.

## Consequences

1. **Third-party extensibility is blocked** until the plugin system is implemented in v0.3.0+. Users who need custom parsers must modify the source code directly.
2. **Protocol interfaces are stable contracts.** `Parser`, `OutputWriter`, and `AIProvider` Protocols are defined in the domain layer and are maintained as public API from v0.1.0 onward. Breaking changes to these Protocols require a deprecation cycle.
3. **Internal parsers implement the Protocol** but are registered directly in the DI container. When the plugin system is built, these internal implementations become "built-in plugins" with no code changes.
4. **Future plugin system** (v0.3.0+) will implement:
   - Entry point discovery via PEP 621 `[project.entry-points]`.
   - Plugin validation (verify Protocol compliance at load time).
   - Lifecycle management (load → validate → initialize → teardown).
   - Error isolation (a failing plugin is disabled, not crashed).
   - Plugin-specific configuration sections in TOML.
5. **The DI container is the migration path.** Moving from hardcoded registration to plugin-discovered registration is a change to the container configuration, not to the services or domain logic.
