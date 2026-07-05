# Knowledge Engine — Project Overview

**Last Updated:** 2026-07-05
**Blueprint Version:** 1.0 (Frozen for MVP)
**Current Phase:** Pre-implementation — Phase 0 begins next

## What Is This Project?

The Knowledge Engine is a local-first AI platform for indexing, searching, and organizing personal knowledge stored as local files. It runs entirely on the user's machine using Ollama for AI capabilities and embedded databases (LanceDB, DuckDB) for storage.

## Current Status

The architecture is frozen for v0.1.0 implementation. All design decisions are documented as ADRs in `.ai/decisions/`. Engineering standards are in `.ai/standards/`.

## v0.1.0 MVP Scope

The MVP delivers a CLI tool that:
1. `lke init /path/to/vault` — initializes a vault for indexing
2. `lke index` — parses all Markdown/Obsidian files and generates embeddings
3. `lke search "query"` — performs semantic search
4. `lke watch` — watches for file changes and updates the index incrementally
5. `lke status` — shows health checks and indexing stats

## Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Language | Python 3.13+ | Modern syntax, type safety |
| AI Runtime | Ollama | Local-first, model-agnostic |
| Embedding Model | nomic-embed-text (768 dims) | Best quality/speed/resource balance |
| Vector Database | LanceDB | Embedded, disk-based, zero-config |
| Metadata Database | DuckDB | Embedded, SQL, zero-config |
| CLI | Typer + Rich | Modern Python CLI standard |
| Configuration | TOML + Pydantic | Stdlib support, validated, immutable |
| Logging | Loguru | Structured, flexible, simple API |
| Testing | pytest | Python standard |
| Linting | ruff + mypy --strict | Fast, comprehensive |
| Package Manager | uv | Fast, reproducible |

## Architecture

Clean Architecture with strict dependency rules:
- **Domain** (innermost): models, events, ports (protocols), domain services — zero external deps
- **Application**: orchestration services — depends on domain only
- **Infrastructure**: adapters for LanceDB, DuckDB, Ollama, filesystem — implements domain ports
- **CLI**: thin Typer layer — depends on application only
- **Composition Root**: DI container wires everything together

v0.1.0 uses synchronous direct method calls. No event bus, no async.

## Key Design Decisions

1. Two databases: LanceDB (vectors) + DuckDB (metadata) — each optimized for its query pattern
2. Synchronous execution — async deferred to HTTP API phase
3. No event bus in MVP — direct method calls, event bus in v0.3.0
4. No plugin system in MVP — protocols defined, registry deferred to v0.3.0
5. No knowledge graph in MVP — GraphRepository protocol defined, implementation in v0.2.0
6. Error handling: transient (retry), permanent (skip+log), partial (process what succeeds)
7. AI Provider has capability detection — no assumptions based on model names

## What NOT to Build Yet

- Knowledge graph (v0.2.0)
- LLM metadata generation (v0.3.0)
- Plugin system (v0.3.0)
- Event bus (v0.3.0)
- HTTP API (v1.0.0)
- Async execution (v1.0.0)

## Roadmap

| Phase | Weeks | Deliverable |
|-------|-------|-------------|
| Phase 0 — Foundation | 1-2 | Domain layer, config, logging, tests |
| Phase 1 — Parse+Embed+Search | 3-6 | Working init + index + search CLI |
| Phase 2 — Watch+Resilience | 7-8 | Watch mode, error recovery, benchmarks |
| Phase 3 — Release v0.1.0 | 9-10 | Docs, packaging, CI, v0.1.0 tag |

## For AI Assistants

If you are an AI assistant working on this project:
1. Read this file first for project context
2. Read the relevant ADRs in `.ai/decisions/` before making architectural decisions
3. Follow the standards in `.ai/standards/` for all code
4. Check `.ai/tasks/backlog.md` for current work items
5. Do not violate the dependency rules in `architecture_rules.md`
6. Do not build deferred features (knowledge graph, plugins, event bus, async)
