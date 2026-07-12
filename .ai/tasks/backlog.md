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
*   **T3.4.2: Tune/Re-validate `related_notes_threshold`** (PENDING)
    *   Extended the eval harness to also test note-to-note relatedness (the EnrichmentPipeline logic).
    *   Ran the `tests/eval/corpus` against a swept threshold (0.40 to 0.80).
    *   **Finding:** Single-threshold cosine similarity on chunk-level embeddings cannot separate structural/lexical overlap from true semantic relation for this corpus, at any threshold value. The current default (0.55) yields a 100% false-positive rate on adversarial pairs. 
*   **T3.4.3: Scope related-notes semantic accuracy fix** (COMPLETE)
    *   *Task:* Evaluate options to fix the 100% false-positive rate on homonyms/adversarial pairs before proceeding with implementation.
    *   *Finding:* We fixed the corrupted vocabulary (purging garbage tags like "fix"). The generated tags are now much cleaner (e.g., "python", "java", "machine-learning"). However, the LLM still hallucinates existing tags onto unrelated documents (e.g., applying "python" and "java" to both apple_company.md and apple_fruit.md). Because the LLM assigns overlapping tags to completely unrelated documents, the **Option B (Tag-overlap gating)** still FAILS to separate adversarial pairs.
    *   *Option A:* Document-level pooled embeddings (average chunks). Tradeoff: No extra inference cost, scales trivially (O(1) after embedding), but risks washing out small but highly relevant shared concepts in longer documents.
    *   *Option B:* LLM-based reranking. Use chunk-level cosine similarity to fetch top N candidates, then run a fast LLM to judge semantic relatedness for each pair. Tradeoff: Highly precise, but introduces O(N) LLM calls *per document*, scaling poorly with vault size and candidate count. This adds massive latency and cost on top of the base tagging/summary generation.
    *   *Option C:* Cross-encoder reranking. Same flow as Option B but uses a local cross-encoder model. Tradeoff: No network latency and likely faster than an LLM, but requires downloading and managing a secondary local model for inference.
    *   *Recommendation:* **Option B (LLM reranking)** is the most robust approach for precision, but its true cost is O(candidates) LLM calls, which could severely bottleneck ingestion. **Option C (Cross-encoder)** may actually be the superior production choice to balance precision with acceptable local performance. We should present this scoping to the user to choose the implementation path.

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
*   **Related-Notes Linking False Positives (CRITICAL):** Evaluation (T3.4.2) proves the `related_notes_threshold` using chunk-level cosine similarity has a 100% false-positive rate on homonyms/ambiguous pairs. **Recommendation for Fallback:** We should implement a temporary conservative fallback (e.g. require at least 1 exact tag match alongside the threshold) to prevent actively writing incorrect links into users' notes in production until the T3.4.3 fix lands.
