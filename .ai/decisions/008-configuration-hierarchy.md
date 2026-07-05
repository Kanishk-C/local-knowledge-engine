# ADR-008: Configuration Hierarchy

**Status:** Accepted
**Date:** 2026-07-05
**Deciders:** Architecture Team

## Context

The Local Knowledge Engine needs a configuration system that supports:

- **Sensible defaults** — the system should work out of the box with zero configuration.
- **User customization** — users should be able to set preferences (e.g., preferred embedding model, default search result count) that apply across all their vaults.
- **Project-specific overrides** — a specific vault might use a different model or different search parameters.
- **Environment-based configuration** — for CI/CD, containers, and scripted workflows.
- **CLI argument overrides** — for one-off commands that differ from the stored configuration.

Configuration must be validated at startup. Invalid configuration must produce clear, actionable error messages — not silent fallbacks or cryptic stack traces.

## Decision

### Format: TOML

All configuration files use **TOML** format. TOML is human-readable, supports nested structures, has unambiguous type semantics, and its reader (`tomllib`) is in the Python standard library as of Python 3.11.

### 5-Level Precedence Hierarchy

Configuration is resolved through a 5-level hierarchy, with higher levels overriding lower levels:

| Priority | Source | Path / Mechanism | Purpose |
|---|---|---|---|
| **1 (highest)** | CLI arguments | `--top-k 20`, `--model nomic-embed-text` | One-off overrides for a single command |
| **2** | Environment variables | `LKE__SEARCH__TOP_K=10` | CI/CD, containers, scripted workflows |
| **3** | Project config | `{vault_root}/.lke/config.toml` | Vault-specific settings |
| **4** | User config | `~/.config/lke/config.toml` | User-wide preferences |
| **5 (lowest)** | Default config | `src/lke/defaults/config.toml` (shipped with package) | Sensible defaults for all settings |

### Environment Variable Convention

Environment variables use the `LKE__` prefix with **double-underscore nesting** to map to TOML's nested structure:

| Environment Variable | TOML Equivalent |
|---|---|
| `LKE__SEARCH__TOP_K=10` | `[search] top_k = 10` |
| `LKE__AI__EMBEDDING_MODEL="nomic-embed-text"` | `[ai] embedding_model = "nomic-embed-text"` |
| `LKE__LOGGING__LEVEL="DEBUG"` | `[logging] level = "DEBUG"` |

Double underscore is used instead of single underscore to avoid ambiguity with setting names that contain underscores (e.g., `top_k`).

### Validation with Pydantic

The `AppConfig` model is a **Pydantic `BaseSettings`** subclass with `env_nested_delimiter='__'` for automatic environment variable mapping.

Key properties:

- **Frozen after construction** — the configuration is immutable at runtime. No component can modify configuration after startup. This prevents hidden state changes and makes the system's behavior predictable.
- **Validated at startup** — all fields are validated when the model is constructed. Type errors, missing required fields, and invalid values produce clear error messages with the file path and line number of the offending value.
- **Merged in precedence order** — the configuration loader reads all levels, merges them in precedence order, and constructs a single `AppConfig` instance.

### Writing Configuration

When the system needs to write configuration (e.g., `lke config set`, `lke init`), it uses `tomlkit` instead of a plain TOML writer. `tomlkit` preserves:

- Existing comments in the file.
- Formatting and whitespace.
- Key ordering.

This ensures that user-edited configuration files are not mangled by programmatic updates.

## Alternatives Considered

### 1. YAML

**Rejected because:**
- Implicit type coercion bugs: `no` becomes `False`, `3.10` becomes `3.1`, `on` becomes `True`.
- Not in the Python standard library — requires `PyYAML` dependency.
- The "Norway problem" and similar YAML gotchas are well-documented footguns.

### 2. JSON

**Rejected because:**
- No support for comments — users cannot annotate their configuration.
- Verbose syntax (requires quoting all keys, trailing comma restrictions).
- Poor ergonomics for hand-edited configuration files.

### 3. INI (configparser)

**Rejected because:**
- No nested structures — all values are flat key-value pairs in sections.
- No typed values — everything is a string, requiring manual type conversion.
- Insufficient for the configuration complexity of LKE.

### 4. Dynaconf

**Rejected because:**
- Heavy dependency with many features the system does not need (Redis settings, Vault integration).
- Adds a learning curve for contributors who must understand Dynaconf's conventions.
- The 5-level hierarchy is straightforward to implement with Pydantic `BaseSettings`.

### 5. python-dotenv

**Rejected because:**
- Flat key-value pairs only — no nested configuration support.
- No type validation.
- Intended for environment variable loading, not structured configuration.

## Trade-offs

| Aspect | TOML + Pydantic | Dynaconf | YAML |
|---|---|---|---|
| **Read support** | `tomllib` (stdlib) | Built-in | `PyYAML` (dependency) |
| **Write support** | `tomlkit` (dependency) | Built-in | `PyYAML` (dependency) |
| **Type safety** | Unambiguous types | Unambiguous types | Implicit coercion bugs |
| **Comments** | Supported | Supported | Supported |
| **Nested structures** | Native tables | Native | Native |
| **Validation** | Pydantic (already a dependency) | Built-in validators | Manual validation |
| **Complexity** | Moderate (custom merge logic) | Low (built-in) | Moderate |
| **Dependencies** | `tomlkit` for writing only | `dynaconf` | `PyYAML` |

The primary trade-off is that TOML reading is in the standard library (`tomllib`), but writing requires the `tomlkit` dependency. This is acceptable because writing is infrequent (only during `lke init` and `lke config set`), and `tomlkit` is a focused, well-maintained library.

The 5-level hierarchy is comprehensive but requires careful implementation of the merge logic. Each level must be loaded independently, merged in order, and the merged result validated as a whole. Errors must report which source (file, environment variable, CLI argument) provided the invalid value.

## Consequences

1. **`tomllib`** (stdlib, Python 3.11+) is used for all TOML reading. No external dependency for the read path.
2. **`tomlkit`** is added as a dependency for TOML writing that preserves comments and formatting.
3. **`AppConfig`** is a Pydantic `BaseSettings` model, validated at startup. It is frozen (immutable) after construction and passed to services via dependency injection.
4. **Bad configuration produces clear, actionable error messages** — e.g., "Invalid value for `search.top_k` in `~/.config/lke/config.toml` line 12: expected integer, got string 'ten'."
5. **Environment variables** follow the `LKE__SECTION__KEY` convention with double-underscore nesting.
6. **`lke config show`** displays the resolved configuration with the source of each value (default, user, project, env, CLI) for debugging.
