# Knowledge Engine — Engineering Backlog (v0.1.0)

**Status:** APPROVED
**Blueprint Version:** 1.0

This document is the canonical engineering work queue for implementing v0.1.0 of the Knowledge Engine. It transforms the Project Blueprint v1.0 into actionable, independently verifiable tasks.

---

## 1. Milestone Overview

| Milestone | Name | Focus | Status |
|-----------|------|-------|--------|
| **M0** | Foundation | Scaffolding, Domain, Config, Logging, Interfaces | COMPLETE |
| **M1** | Parse + Embed + Search | Parsers, Ollama, LanceDB, Application Services | COMPLETE |
| **M2** | Enrichment + Watch Mode | Tagging, Summarization, File Watcher, Resilience | COMPLETE |
| **M3** | RAG, API & Release | RAG, API Server, CI/CD, Docs, Packaging, Evals | PENDING |

---

## 2. Epic Breakdown

### M0: Foundation
*   **E0.1:** Project Scaffolding & Tooling
*   **E0.2:** Core Domain Models & Exceptions
*   **E0.3:** Domain Ports & Services
*   **E0.4:** Cross-Cutting Concerns (Logging, Config, DI)

### M1: Parse + Embed + Search
*   **E1.1:** Parsing Engine
*   **E1.2:** AI Provider Integration
*   **E1.3:** Storage Adapters
*   **E1.4:** Application Orchestration
*   **E1.5:** CLI Core Commands

### M2: Enrichment + Watch Mode
*   **E2.0:** Enrichment Pipeline (Tagging, Summary, Folders, Related Notes)
*   **E2.1:** File Watcher & Incremental Indexing (Depends on E2.0)
*   **E2.2:** Resiliency & State Management

### M3: RAG, API & Release
*   **E3.1:** RAG Pipeline & Generation Service
*   **E3.2:** REST API Server (FastAPI)
*   **E3.3:** Documentation & Packaging
*   **E3.4:** Search Evaluation Suite

---

## 3. Complete Engineering Backlog

### Milestone 0: Foundation
(All Tasks E0.1 - E0.4 COMPLETE)

### Milestone 1: Parse + Embed + Search
*   **T1.1.1: Markdown & Obsidian Parsers** (COMPLETE)
*   **T1.2.1: Ollama Provider & Capability Detection** (COMPLETE)
*   **T1.3.1: LanceDB Vector Repository** (COMPLETE)
*   **T1.3.2: DuckDB Document Repository** (CANCELLED - Option B Selected: Replaced with JSON-based `_MetadataStore`)
*   **T1.4.1: Ingestion Service (The Pipeline)** (COMPLETE)
*   **T1.4.2: Search Service** (COMPLETE)
*   **T1.5.1: Init, Index, and Search CLI Commands** (COMPLETE)

### Milestone 2: Enrichment + Watch Mode
*   **T2.0.1: Enrichment Pipeline Core** (COMPLETE)
    *   Implemented `EnrichmentPipeline` with vocabulary service (JSON-based) and LLM prompting for tags/summaries.
*   **T2.0.2: Auto-Filing Moves** (COMPLETE)
    *   Implemented `MarkdownFrontmatterWriter` to rewrite frontmatter and physically move files to folder structures based on inferred topic tags.
*   **T2.1.1: File Watcher (Watch Mode)** (COMPLETE)
    *   Implemented `WatcherService` using `watchdog` to continuously monitor the vault.
    *   Includes debounce timer, suppression of self-writes (via `FileWriteStarting` and `_IgnoreCache`), and proper `Deleted` + `Created` handling for renamed files.
    *   Integrated into CLI via `lke watch`.

### Milestone 3: RAG, API & Release
*(Not yet started - Exact original scope)*
*   **T3.1.1: RAG Pipeline** (PENDING)
*   **T3.2.1: REST API Server** (PENDING)
*   **T3.3.1: Documentation & Packaging** (PENDING)
*   **T3.4.1: Search Evaluation Suite** (COMPLETE)
    *   Implemented `EvalService` and CLI command `lke eval`.
    *   Built a realistic 32-note evaluation corpus and 12-query dataset testing homonyms, ambiguity, and phrasing overlap.
    *   Verified the `SearchService` achieves 1.0 Recall@5 on the expanded dataset.

---

## 4. History / Changelog (Resolved Bugs & Tech Debt)
*   **Ollama Health Check Bug:** Fixed an issue where the test mock returned `{"status": "ok"}` instead of mirroring the real client's response shape, leading to failures in `lke init`.
*   **LanceDB Init Bug:** Fixed `lke init` failing to properly initialize LanceDB schemas and tables on completely fresh runs.
*   **Empty AI Summary Bug (Fast-Follow):** Fixed an issue where Ollama occasionally returned an empty string for summaries. Added a single retry, and if it still fails, the frontmatter field is omitted entirely rather than persisting an empty string.

---

## 5. Known Limitations & Gaps (Deferred)
*   **DuckDB Removal (Option B):** We removed DuckDB in favor of a simpler LanceDB + JSON metadata approach.
*   **Watch Mode Startup Reconciliation:** If an auto-file move crashes mid-sequence (move succeeded, but LanceDB/metadata.json re-keying failed), the file's entry becomes orphaned until manually fixed. There is no automatic startup reconciliation yet to align disk state with metadata.json.
*   **Watch Mode Initial Catch-Up:** Watch mode does not perform an initial sync pass on startup. Files modified while `lke watch` wasn't running require a manual `lke index` + `lke enrich` run.
*   **Rename Handling:** Renamed files are treated as delete+add by the watcher, meaning a rename triggers full re-embedding rather than a cheap metadata update.
*   **Link Breaking on Auto-File Moves:** Explicit-path embeds and relative links may break when a file is automatically moved. Only standard `[[wikilinks]]` are guaranteed to survive relocation.
*   **Empirically Tuned Relevance Threshold:** The `related_notes_threshold` defaults to 0.55. This was based on a small 10-note sample vault and manual spot-checking, rather than a rigorous, balanced dataset. It may fail to generalise to real, large vaults. (Note: The T3.4.1 eval suite currently tests SearchService retrieval, not EnrichmentPipeline's related_notes_threshold. They are different mechanisms.)
