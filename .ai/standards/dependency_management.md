# Dependency Management Standards

> Local Knowledge Engine (LKE) — rules for managing, adding, and auditing project dependencies.

---

## Package Manager

- **uv** is the project package manager (fast, modern, Rust-based).
- **Lockfile**: `uv.lock` provides reproducible builds with exact pinned versions.
- All developers and CI use `uv sync` to install dependencies from the lockfile.
- Do not use `pip install` directly. All dependency operations go through `uv`.

---

## Dependency Specification

All dependencies are declared in `pyproject.toml` with version bounds:

### Version Bound Strategy

| Dependency Type      | Bound Style               | Example                     | Rationale                               |
|----------------------|---------------------------|-----------------------------|------------------------------------------|
| Major dependencies   | `>=min,<max`              | `pydantic>=2.7,<3`         | Allow patches and minors, block breaking majors |
| Stable/mature libs   | `~=` (compatible release) | `loguru~=0.7`              | Allow patch updates only                 |
| Pinned (fragile)     | `==`                      | `lancedb==0.15.0`          | Only when upstream is known to break between patches |

- Always specify a lower bound. Never use bare package names without version constraints.
- Upper bounds on major versions prevent unexpected breaking changes.

---

## Dependency Groups

Organize dependencies into groups in `pyproject.toml`:

```toml
[project]
dependencies = [
    # Runtime dependencies — shipped with the application
    "typer>=0.12,<1",
    "loguru~=0.7",
    "pydantic>=2.7,<3",
    "lancedb>=0.15,<1",
    "duckdb>=1.1,<2",
    "ollama>=0.4,<1",
    "tomlkit>=0.13,<1",
    "watchdog>=5.0,<6",
    "rich>=13.0,<14",
    "jinja2>=3.1,<4",
]

[project.optional-dependencies]
dev = [
    # Development tools — not shipped
    "ruff>=0.8",
    "mypy>=1.13",
    "pre-commit>=4.0",
    "import-linter>=2.1",
]
test = [
    # Test dependencies
    "pytest>=8.3",
    "pytest-cov>=6.0",
    "coverage>=7.6",
    "hypothesis>=6.115",
]
```

### Install Commands

| Purpose             | Command                        |
|----------------------|-------------------------------|
| Runtime only         | `uv sync`                    |
| With dev tools       | `uv sync --extra dev`        |
| With test deps       | `uv sync --extra test`       |
| All extras           | `uv sync --all-extras`       |

---

## New Dependency Policy

**Every new dependency requires justification.** Before adding a package, evaluate:

### Evaluation Checklist

1. **Necessity**: Can this be accomplished with the standard library or an existing dependency?
2. **Maintenance health**: Is the package actively maintained? Check:
   - Last release date (should be within 12 months)
   - Open issue count and response time
   - Number of maintainers (bus factor > 1 preferred)
3. **License compatibility**: Must be compatible with the project license. Acceptable licenses:
   - MIT
   - Apache-2.0
   - BSD (2-clause or 3-clause)
   - ISC
   - Reject: GPL, LGPL, AGPL, proprietary, or unclear licensing.
4. **Python 3.13+ support**: Must have published wheels or confirmed compatibility with Python 3.13.
5. **Dependency footprint**: Prefer packages with few transitive dependencies. Heavy dependency trees increase risk and install time.
6. **Security track record**: Check for past CVEs or security advisories.

### Process

1. Open a discussion or issue explaining why the dependency is needed.
2. Document the evaluation in an Architecture Decision Record (ADR) in `.ai/decisions/`.
3. Get approval before adding to `pyproject.toml`.

---

## Pinning Strategy

| File              | Purpose                     | Version Style   |
|-------------------|-----------------------------|-----------------|
| `pyproject.toml`  | Declare acceptable ranges   | `>=min,<max`    |
| `uv.lock`         | Pin exact versions for builds | Exact (auto-generated) |

### CI Testing

- **Locked versions**: CI runs tests against `uv.lock` to verify reproducibility.
- **Latest versions**: A separate CI job (weekly or on-demand) runs tests with `uv sync --upgrade` to catch compatibility issues early.

---

## Security

- Run **`uv audit`** in CI to check all dependencies for known vulnerabilities.
- `uv audit` is a required CI step — builds fail if vulnerabilities are found.
- For newly disclosed vulnerabilities:
  - If a patch is available, update immediately.
  - If no patch is available, assess risk and document a mitigation plan.

---

## Core Runtime Dependencies (v0.1.0)

| Package    | Purpose                                     |
|------------|---------------------------------------------|
| `typer`    | CLI framework (command parsing, help text)  |
| `loguru`   | Structured logging                          |
| `pydantic` | Configuration validation, data models       |
| `lancedb`  | Vector database for embeddings              |
| `duckdb`   | Metadata storage and relational queries     |
| `ollama`   | Local LLM and embedding model client        |
| `tomlkit`  | TOML config file reading/writing            |
| `watchdog` | Filesystem event monitoring                 |
| `rich`     | Terminal output formatting (tables, progress) |
| `jinja2`   | Prompt templating                           |

These dependencies were selected in the project's initial architecture decisions. Each has a corresponding ADR.

---

## Updating Dependencies

### Routine Updates

- Run `uv lock --upgrade` periodically (at least monthly) to pick up patch and minor updates.
- Review the diff in `uv.lock` before committing.
- Run the full test suite after updating.

### Major Version Upgrades

- Major version bumps (e.g., Pydantic v2 → v3) require:
  - A dedicated branch
  - Full test suite verification
  - Review of the upstream changelog for breaking changes
  - An ADR documenting the migration plan if changes are significant

---

## Dependency Removal

- When a dependency is no longer used, remove it from `pyproject.toml` and regenerate `uv.lock`.
- Grep the codebase to confirm no imports remain.
- Update the corresponding ADR to mark the dependency as removed and note the reason.
