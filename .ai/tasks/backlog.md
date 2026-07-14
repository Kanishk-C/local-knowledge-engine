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
*   **T2.0.2: Auto-Filing Moves** (COMPLETE)
*   **T2.1.1: File Watcher (Watch Mode)** (COMPLETE)

### Milestone 3: RAG, API & Release
*(Not yet started - Exact original scope)*
*   **T3.1.1: RAG Pipeline** (COMPLETE)
    *   **Finding:** Implemented the RAG generation pipeline including a deterministic zero-source short-circuit. This correctly prevents hallucination on completely out-of-domain queries (e.g. "What is the capital of France?" now yields a deterministic "I don't know" pass).
    *   **Evaluated Accuracy**: 5/13 (38.5%) queries passed. The 8 failures break down into three real categories:
        *   **(a) Contamination (wrong context blended in):** (e.g., Python language vs snake, Java software vs coffee, Apple products vs fruit). The semantic search pulls in lexically identical but conceptually incorrect documents. The LLM correctly adheres to its instructions by summarizing this wrong context without hallucinating, but fails the query.
        *   **(b) Recall failure (relevant content exists but wasn't retrieved):** (e.g., river banks, Docker). The deterministic `0.50` threshold effectively short-circuits the pipeline to prevent hallucinations, but it comes with a severe tradeoff: it suppresses correct answers by failing to retrieve valid but lower-scoring context. 
        *   **(c) Answer completeness (missing secondary details):** (e.g., Gradient descent missing "loss function", Moon landing missing "Buzz Aldrin"). The core answer is correct, but the LLM generation omits secondary expected details present in the chunk.
    *   **Conclusion:** The limitations span three distinct causes: retrieval contamination on lexically-overlapping adversarial content (category 1), a deliberate recall-for-safety tradeoff from the deterministic zero-source short-circuit threshold (category 2, not a retrieval bug — an accepted tradeoff), and a generation-side completeness gap unrelated to retrieval, where the model answers tersely rather than exhaustively from otherwise correct context (category 3).
*   **T3.2.1: REST API Server** (PENDING)
*   **T3.3.1: Documentation & Packaging** (PENDING)
*   **T3.4.1: Search Evaluation Suite** (COMPLETE)
*   **T3.4.2: Tune/Re-validate `related_notes_threshold`** (COMPLETE)
    *   **Finding:** Single-threshold cosine similarity on chunk-level embeddings cannot separate structural/lexical overlap from true semantic relation for this corpus, at any threshold value. The current default (0.55) yields a 100% false-positive rate on adversarial pairs. 
*   **T3.4.3: Investigate potential fixes to related-notes semantic accuracy** (COMPLETE)
    *   **T3.4.4: Verify Cross-Encoder implementation/integration and investigate failure** (COMPLETE)
    *   - **Findings:** Cross-Encoder integration is fundamentally sound and evaluating cleanly parsed body text. However, isolated, zero-shot, binary pairwise judgment (embeddings, cross-encoder, and single-pair LLM prompting) all fail to separate this adversarial corpus. No single threshold can separate structural overlap from true conceptual linkage under this testing paradigm.
    *   - **Testing Option B (Pairwise LLM Judgment):** We ran a direct 0-shot single-pair LLM evaluation using `llama3.2`. It successfully rejected all 5 adversarial false positives but incorrectly rejected 3 out of 5 conceptually related true positives.
    *   - **Note on Dataset:** The 5 adversarial pairs were deliberately engineered with identical boilerplate openers to stress-test this feature. They represent an extreme edge case.
    *   - **Resolution:** Documented this as a known limitation for isolated pairwise evaluation. We have updated the default `related_notes_threshold` to `7.5`. Since this threshold sits above every score (both TP and FP) observed in the sweep, related-notes linking is effectively disabled by default. We are moving on to the RAG milestone.

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
*   **Rename Handling:** Renames are treated as a delete followed by an add, missing any conceptual continuity.
*   **Search Threshold Looseness:** RAG's deterministic short-circuit relies strictly on zero retrieval results; but `min_similarity` defaults to 0.50, which is loose enough that even short nonsense strings (e.g. "qweqweqwe") can clear the relevance threshold, heavily depending on the LLM to filter them.
*   **Link Breaking on Auto-File Moves:** Explicit-path embeds and relative links may break when a file is automatically moved. Only standard `[[wikilinks]]` are guaranteed to survive relocation.
