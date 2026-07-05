# ADR-001: Repository Structure

**Status:** Accepted
**Date:** 2026-07-05
**Deciders:** Architecture Team

## Context

The Local Knowledge Engine (LKE) is a Python platform for indexing, searching, and organizing personal knowledge. It follows Clean Architecture principles with clearly separated domain, application, infrastructure, and CLI layers. The repository structure must support this architectural approach while remaining practical for a single-package Python project. Additionally, the project uses AI-assisted development and needs a persistent location for engineering memory — context documents, architectural decisions, coding standards, and task tracking — that survives across sessions and tools.

## Decision

Adopt a `src/lke/` layout with layer-oriented subdirectories reflecting Clean Architecture boundaries:

```
local_knowledge_engine/
├── src/lke/
│   ├── domain/          # Entities, value objects, repository interfaces
│   ├── application/     # Use cases, services, orchestration
│   ├── infrastructure/  # Database adapters, Ollama client, file I/O
│   └── cli/             # Typer CLI commands, output formatting
├── tests/
│   ├── unit/            # Mirrors src/ structure
│   ├── integration/     # Cross-layer tests
│   └── e2e/             # End-to-end pipeline tests
├── config/              # Default configuration files (TOML)
├── docs/                # MkDocs documentation
├── .ai/                 # Persistent engineering memory
│   ├── context/         # Project context documents
│   ├── decisions/       # Architecture Decision Records
│   ├── standards/       # Coding standards and conventions
│   ├── tasks/           # Task tracking and plans
│   └── sessions/        # Session logs
├── pyproject.toml
├── README.md
└── ...                  # Minimal top-level files
```

Top-level directories are kept minimal. Directories such as `benchmarks/`, `plugins/`, and `examples/` are not created until they have content — no empty placeholders.

## Alternatives Considered

1. **Flat `src` layout without `src/` directory** — Placing the `lke` package directly at the repository root is simpler but doesn't support namespace packages or editable installs (`pip install -e .`) as cleanly. The flat layout risks conflating the package root with the project root, making it easy to accidentally import test or config modules.

2. **Monorepo with multiple packages** — Structuring the project as multiple independently versioned packages (e.g., `lke-core`, `lke-cli`, `lke-obsidian`) provides strong isolation but is overkill for a single-package project at this stage. It adds build complexity with no current benefit.

3. **Domain-oriented folders (features/) instead of layer-oriented** — Organizing by feature (e.g., `indexing/`, `search/`, `metadata/`) groups related code together but makes it harder to enforce dependency rules. In Clean Architecture, the primary constraint is that inner layers must not depend on outer layers; layer-oriented structure makes violations immediately visible in import paths.

## Trade-offs

- **Deep nesting vs. flat structure:** The `src/lke/domain/...` path is deeper than a flat layout, adding a few extra directories to navigate. This is acceptable because the depth directly maps to architectural layers, making the dependency hierarchy self-documenting.

- **Layer-based vs. feature-based organization:** Layer-based organization was chosen because dependency rules are the primary architectural constraint. Feature-based organization would require additional tooling (import linters, custom rules) to enforce the same boundaries that directory structure enforces naturally in a layer-based layout.

- **`.ai/` directory overhead:** Adding a non-code directory to the repository is unconventional but provides persistent context for AI-assisted development. The overhead is negligible — it contains only Markdown files and has no impact on packaging or runtime.

## Consequences

- **Clear layer boundaries:** Import paths like `from lke.domain.entities import Document` and `from lke.infrastructure.lancedb import VectorRepository` make architectural layer membership explicit. Circular dependency detection is straightforward.

- **Standard Python packaging:** The `src/` layout is the recommended practice for modern Python packaging with `pyproject.toml`. Editable installs, namespace packages, and build backends (hatchling, setuptools) all work correctly out of the box.

- **Import paths reflect architecture:** A developer can determine a module's architectural role from its import path alone, reducing cognitive overhead when navigating the codebase.

- **`.ai/` provides project memory:** Architecture decisions, coding standards, and context documents persist across AI assistant sessions. Any AI tool can read `.ai/context/` to understand the project without re-discovery. This directory is committed to version control.

- **Test structure mirrors source:** Tests are organized by type (unit, integration, e2e) and within each type mirror the `src/` directory structure, making it easy to locate tests for any module.
