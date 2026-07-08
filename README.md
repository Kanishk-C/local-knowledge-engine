# Local Knowledge Engine (LKE)

A Local-First AI Knowledge Engine for understanding, organizing, indexing, searching, linking, documenting, and maintaining personal knowledge stored locally.

## Project Vision

Build an AI Operating System for knowledge management that runs entirely on the user's machine. The first client is Obsidian, but the long-term goal is a reusable platform. 

## Features (MVP Scope v0.1.0)
- Watch local files
- Parse Markdown and Obsidian formats (wikilinks, frontmatter, callouts)
- Generate vector embeddings via local models (`nomic-embed-text`)
- Persist metadata in DuckDB and embeddings in LanceDB
- Semantic search via Typer CLI

## Architecture Summary
LKE strictly adheres to Clean Architecture, with Domain, Application, Infrastructure, and CLI layers. The `src/lke` directory matches these layers. Strict Dependency Inversion is enforced. See `.ai/decisions/` and `.ai/standards/` for architectural documentation.

## Repository Structure
```
.ai/               # Engineering Memory (Decisions, Context, Standards, Backlog)
src/lke/
  ├── domain/      # Pure business logic, models, and interfaces (protocols)
  ├── application/ # Orchestration services
  ├── infrastructure/ # Adapters for DBs, AI, Parsing
  └── cli/         # Typer entrypoint
tests/             # Unit, Integration, E2E tests
```

## Development Setup

**Prerequisites:** Python 3.13+, `uv` installed, `make` installed.

1. Clone the repository
2. Install dependencies: `uv sync`
3. Run verification: `make all` (Formats, lints, typechecks, tests)

## Continuous Integration

Every push and pull request is automatically validated by our GitHub Actions pipeline, which runs:
- `uv run ruff format --check .` (Formatting)
- `uv run ruff check .` (Linting)
- `uv run mypy src tests` (Type checking)
- `uv run pytest --cov=src --cov-report=xml --cov-fail-under=80` (Tests & Coverage)

You can run these checks locally via the `make all` command. The pipeline acts as the quality gate for the repository and all checks must pass before a pull request can be merged.
## Quick Start
*(Placeholder for CLI commands when implemented)*
```bash
lke init /path/to/vault
lke index
lke search "My query"
lke watch
```

## Technology Stack
- **Language**: Python 3.13+
- **CLI**: Typer + Rich
- **Vector DB**: LanceDB
- **Metadata DB**: DuckDB
- **AI Runtime**: Ollama
- **Configuration**: TOML + Pydantic
- **Testing**: Pytest

## Roadmap
- Phase 0: Foundation (Complete)
- Phase 1: Parse + Embed + Search (Current)
- Phase 2: Watch Mode + Resilience
- Phase 3: Release v0.1.0

## License
MIT License. See [LICENSE](LICENSE) for details.
