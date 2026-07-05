# Definition of Done

> Local Knowledge Engine (LKE) — a task is complete **only** when ALL of the following criteria are satisfied.

---

## Checklist

### Code Quality

- [ ] **1. Code runs without errors.** The application starts, the modified feature works, and no runtime exceptions are introduced.
- [ ] **2. Type checking passes.** `mypy --strict` reports zero errors on all changed and new files.
- [ ] **3. Linting passes.** `ruff check` reports zero warnings. `ruff format --check` confirms formatting compliance.

### Testing

- [ ] **4. Unit tests written.** All new domain and application logic has corresponding unit tests. Tests follow the naming convention `test_{method}_{scenario}_{expected_result}`.
- [ ] **5. All existing tests pass.** No regressions. Both unit and integration test suites are green.
- [ ] **6. Code coverage ≥ 80%.** Coverage on changed files meets the 80% threshold, measured by coverage.py. Coverage is meaningful — tests verify behavior, not just execute lines.

### Documentation

- [ ] **7. Public APIs have docstrings.** All new or modified public classes, methods, and functions have Google-style docstrings with `Args`, `Returns`, and `Raises` sections where applicable.
- [ ] **8. No untracked TODOs.** No `TODO`, `FIXME`, or `HACK` comments exist without a linked issue number (e.g., `# TODO(#42): optimize embedding batch size`).

### Architecture

- [ ] **9. Dependency rules respected.** No layer violations. Domain does not import from application/infrastructure/CLI. Application does not import from infrastructure/CLI. Verified by import-linter or manual review.

### Version Control

- [ ] **10. Conventional Commit message.** Commit message follows the Conventional Commits specification:
  - `feat:` — new feature
  - `fix:` — bug fix
  - `docs:` — documentation only
  - `refactor:` — code restructure without behavior change
  - `test:` — adding or modifying tests
  - `chore:` — maintenance (deps, CI config, tooling)
  - `perf:` — performance improvement
  - `ci:` — CI/CD configuration
  - Scope is optional but encouraged: `feat(parser): add Obsidian wikilink support`

- [ ] **11. CHANGELOG updated.** If the change is user-facing (new feature, bug fix, breaking change), add an entry to `CHANGELOG.md` under the `[Unreleased]` section.

### Architecture Documentation

- [ ] **12. Architecture docs updated.** If interfaces (Protocols), layer boundaries, or public APIs changed, update the relevant documentation in `.ai/` or `docs/`.

### Review

- [ ] **13. Code reviewed.** At minimum, a thorough self-review has been performed. Peer review is preferred for non-trivial changes. Review checks:
  - Correctness of logic
  - Adherence to coding standards
  - Test quality and coverage
  - Architectural compliance

### Integration

- [ ] **14. Integration tests pass.** If infrastructure adapters were modified (DB adapters, filesystem, Ollama client), integration tests for those adapters pass.

### CI

- [ ] **15. Clean CI pipeline.** No new warnings in the CI pipeline. All jobs (lint, type check, unit tests, integration tests) are green.

---

## When to Apply

This checklist applies to **every task, PR, or code change** regardless of size. For trivial changes (typo fixes, comment updates), some items may be not applicable — but the checklist must still be reviewed and inapplicable items explicitly acknowledged.

---

## Quick Reference

| #  | Criterion                           | Tool / Method                |
|----|-------------------------------------|------------------------------|
| 1  | Code runs                          | Manual verification          |
| 2  | Type check                         | `mypy --strict`              |
| 3  | Lint + format                      | `ruff check` + `ruff format` |
| 4  | Unit tests written                 | pytest                       |
| 5  | Existing tests pass                | `pytest`                     |
| 6  | Coverage ≥ 80%                     | `pytest --cov`               |
| 7  | Docstrings                         | Manual review / ruff rules   |
| 8  | No untracked TODOs                 | `grep -rn "TODO\|FIXME\|HACK"` |
| 9  | Dependency rules                   | import-linter / manual review |
| 10 | Conventional Commit                | Commit message review        |
| 11 | CHANGELOG                          | Manual                       |
| 12 | Architecture docs                  | Manual                       |
| 13 | Code review                        | Self-review / peer review    |
| 14 | Integration tests                  | `pytest -m integration`      |
| 15 | Clean CI                           | CI pipeline dashboard        |
