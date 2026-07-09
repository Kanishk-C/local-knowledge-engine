# Agent Operating System (AOS)

This is the primary entry point for all AI Coding Agents working on the Local Knowledge Engine (LKE) repository.
Before modifying this repository, **you must read and understand this file**.

## 1. Canonical Engineering Documentation
Do NOT duplicate these documents in `.agent/`. Read them directly:
- **Architecture decisions:** See `.ai/decisions/`
- **Engineering standards:** See `.ai/standards/`
- **Backlog:** See `.ai/tasks/backlog.md`

## 2. Implementation Workflow
Every implementation session MUST follow:
1. Read `AGENTS.md`.
2. Read `.agent/context/project_vision.md`.
3. Read `.agent/context/mvp_scope.md`.
4. Read `.agent/context/current_task.md`.
5. Read relevant ADRs (`.ai/decisions/`).
6. Read the backlog (`.ai/tasks/backlog.md`).
7. Produce implementation plan.
8. Implement.
9. Run `make all`.
10. Perform self-review.
11. **Mandatory Documentation Sync:** Update `.ai/tasks/backlog.md`, `.agent/context/current_task.md`, and any other relevant tracking documents to reflect the tasks you have just completed. Mark finished items as COMPLETE and update the next pending steps based on the codebase's current state.
12. **STOP**. Wait for human approval before ANY git command.

## 3. Required Verification
You must ensure `make all` passes, which includes:
- Ruff (Formatting and Linting)
- MyPy (Strict typing)
- Pytest (Tests and >80% coverage)

## 4. Prohibited Behaviour
Read `.agent/rules/git_rules.md`. You MUST NEVER perform any Git restricted operations without explicit approval.
