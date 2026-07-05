# Commit and Branching Standards

> Local Knowledge Engine (LKE) — conventions for commits, branches, and release management.

---

## Commit Messages

### Format: Conventional Commits

All commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type       | Purpose                                              | Example                                         |
|------------|------------------------------------------------------|-------------------------------------------------|
| `feat`     | New feature or capability                            | `feat(parser): add Obsidian wikilink support`    |
| `fix`      | Bug fix                                              | `fix(search): handle empty query gracefully`     |
| `docs`     | Documentation changes only                           | `docs: add architecture rules document`          |
| `refactor` | Code restructuring without behavior change           | `refactor(domain): extract DocumentId value object` |
| `test`     | Adding or modifying tests                            | `test(index): add unit tests for dedup logic`    |
| `chore`    | Maintenance (deps, config, tooling, CI)              | `chore: update ruff to 0.8.2`                   |
| `perf`     | Performance improvement                              | `perf(embed): batch embedding requests`          |
| `ci`       | CI/CD pipeline configuration                         | `ci: add integration test job`                   |

### Rules

- **Subject line**: Imperative mood, lowercase, no period at the end. Max 72 characters.
  - Good: `feat(parser): add frontmatter extraction`
  - Bad: `Added frontmatter extraction.`
- **Scope**: Optional but encouraged. Use the module or layer name (`parser`, `search`, `cli`, `domain`, `infra`).
- **Body**: Optional. Use for explaining *why* (not *what* — the diff shows what). Wrap at 72 characters.
- **Footer**: Use for breaking changes and issue references:
  - `BREAKING CHANGE: renamed SearchResult.score to SearchResult.similarity`
  - `Closes #42`
  - `Refs #15`

### Breaking Changes

Breaking changes must be indicated by either:

1. An exclamation mark after the type/scope: `feat(search)!: change result format`
2. A `BREAKING CHANGE:` footer with a description of the change

### Examples

```
feat(parser): add Obsidian wikilink support

Parse [[wikilinks]] and [[wikilinks|display text]] in markdown
documents. Wikilinks are resolved to document IDs during indexing.

Closes #23
```

```
fix(search): return empty list instead of raising on no results

Previously, searching with no matching documents raised a
NoResultsError. This was inconsistent with standard search behavior.
Now returns an empty list.
```

```
refactor(domain)!: rename Document.content to Document.body

BREAKING CHANGE: Document.content has been renamed to Document.body
to avoid confusion with the content_hash field. All references updated.
```

---

## Branch Strategy

### Trunk-Based Development

- **Main branch**: `main` — always deployable, always green.
- Development happens on short-lived feature branches that merge back to `main` quickly.

### Branch Naming

| Branch Type      | Pattern                       | Example                         |
|------------------|-------------------------------|---------------------------------|
| Feature          | `feat/<short-description>`    | `feat/obsidian-wikilinks`       |
| Bug fix          | `fix/<short-description>`     | `fix/empty-query-crash`         |
| Documentation    | `docs/<short-description>`    | `docs/architecture-rules`       |
| Refactoring      | `refactor/<short-description>`| `refactor/extract-value-objects`|
| Chore/Maintenance| `chore/<short-description>`   | `chore/update-dependencies`     |

### Branch Rules

- Branches are **short-lived**: target less than **1 week** from creation to merge.
- Long-lived branches accumulate merge conflicts and integration risk. If a feature takes longer than a week, break it into smaller incremental changes.
- Keep branches focused on a single change. Don't mix features, fixes, and refactors in one branch.
- Delete branches after merging.

---

## Pull Requests

### Requirements

- **Required for all changes** to `main`. No direct pushes.
- Every PR must have:
  - A clear title following Conventional Commits format
  - A description explaining *what* and *why*
  - All CI checks passing

### Review Policy

- **Self-review at minimum**: Before requesting merge, review your own diff as if you were a reviewer.
- **Peer review preferred**: For non-trivial changes (new features, architecture changes, complex bug fixes), request a peer review.
- Trivial changes (typo fixes, comment updates, dependency bumps) may be self-reviewed and merged.

### Merge Strategy

- **Squash merge** to `main`. This keeps the main branch history clean with one commit per logical change.
- The squash commit message must follow Conventional Commits format.
- Do not use merge commits or rebase-and-merge for feature branches.

---

## Tags and Releases

### Versioning: Semantic Versioning (SemVer)

Format: `vMAJOR.MINOR.PATCH`

| Component | Increment When                                    | Example          |
|-----------|---------------------------------------------------|------------------|
| MAJOR     | Incompatible API/CLI changes                      | `v1.0.0`         |
| MINOR     | New functionality, backward compatible            | `v0.2.0`         |
| PATCH     | Bug fixes, backward compatible                    | `v0.1.1`         |

### Pre-Release Tags

For versions not yet ready for general use:

```
v0.1.0-alpha.1    # Early development, unstable
v0.1.0-beta.1     # Feature complete, testing
v0.1.0-rc.1       # Release candidate
```

### Tagging Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md` — move items from `[Unreleased]` to the new version section
3. Commit: `chore: release v0.1.0`
4. Tag: `git tag v0.1.0`
5. Push tag: `git push origin v0.1.0`

---

## Protected Branch

### `main` Branch Protection

- **CI must pass** before merge (lint, type check, unit tests, integration tests).
- No force pushes.
- No direct commits — all changes go through pull requests.
- Branch must be up to date with `main` before merging (no stale merges).
