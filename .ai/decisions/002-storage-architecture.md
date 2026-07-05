# ADR-002: Storage Architecture

**Status:** Accepted
**Date:** 2026-07-05
**Deciders:** Architecture Team

## Context

LKE requires persistent storage for three categories of data:

1. **Vector embeddings** — high-dimensional vectors (768+ floats per chunk) with approximate nearest neighbor (ANN) search, metadata filtering, and efficient batch insertion.
2. **Document metadata** — relational data including file paths, content hashes, processing state, timestamps, and tags. Requires joins, aggregates, and complex filters.
3. **Future knowledge graph** — relationships between documents, concepts, and entities. Requires recursive traversal and path queries.

All storage must be fully local, embedded (no server processes), zero-configuration, and performant on consumer hardware. The system must support a single user indexing tens of thousands of documents.

## Decision

Use two embedded databases, each chosen for its strength:

- **LanceDB** for vector embeddings and chunk data. LanceDB provides native ANN search (IVF-PQ indexing), columnar storage optimized for high-dimensional vectors, metadata filtering during search, and single-directory persistence. It operates as an embedded library with no server process.

- **DuckDB** for document metadata, processing state, and future knowledge graph. DuckDB provides full SQL with analytical query performance, recursive CTEs for graph traversal, JSON/struct column types for flexible metadata, and single-file persistence. It operates as an embedded library with no server process.

Both databases are accessed exclusively through port/adapter interfaces defined in the domain layer:

- `VectorRepository` — wraps LanceDB, handles embedding storage and similarity search.
- `DocumentRepository` — wraps DuckDB, handles document metadata and processing state.
- `GraphRepository` (future) — wraps DuckDB tables using recursive CTEs, with an optional migration path to DuckPGQ for property graph queries.

## Alternatives Considered

1. **LanceDB alone** — LanceDB handles vectors well and supports basic metadata columns, but it lacks relational query capabilities. Joins, aggregates, window functions, and complex filtering on metadata are awkward or impossible. Document lifecycle management (status tracking, batch queries by state) would require workarounds.

2. **DuckDB alone** — DuckDB is an excellent analytical SQL database but has no native vector similarity search. The `vss` extension exists but is experimental, with limited ANN algorithm support and no production track record for high-dimensional embedding search.

3. **ChromaDB** — A popular vector database for AI applications, but it loads all data into RAM, has heavy Python dependencies (including hnswlib, onnxruntime), and its persistence model has historically been unreliable. Not suitable for a lightweight, local-first tool.

4. **SQLite + sqlite-vec** — SQLite is the gold standard for embedded databases, but `sqlite-vec` only supports brute-force vector search (no ANN indexing). This is acceptable for small collections but does not scale to tens of thousands of documents with sub-second search requirements.

5. **Single SQLite for everything** — Provides no vector search capability at all. Would require an external library for similarity computation, defeating the purpose of an integrated storage layer.

6. **FAISS** — Facebook's vector similarity library is fast and well-tested, but it is a library, not a database. It has no built-in persistence (vectors must be serialized/deserialized manually), no metadata filtering, and no transactional guarantees. Managing FAISS indices alongside a metadata database adds significant operational complexity.

## Trade-offs

- **Two databases vs. one:** Operating two storage engines adds initialization logic (two connections, two health checks) and requires a migration strategy for each. However, each database excels at its purpose — LanceDB at vector search, DuckDB at relational queries — and neither can adequately replace the other. The port/adapter pattern isolates each database to a single infrastructure module, so the rest of the application is unaware of the dual-database architecture.

- **Operational complexity:** Two databases mean two files to back up, two schemas to migrate, and two potential points of failure. This is mitigated by the fact that both are embedded, single-file databases with no configuration — the operational overhead is closer to "two files" than "two servers."

- **Consistency between databases:** There is no cross-database transaction. A document could theoretically exist in DuckDB but not LanceDB (or vice versa) if a crash occurs mid-pipeline. This is acceptable because the pipeline is idempotent — re-indexing a document will reconcile both stores.

## Consequences

- **`VectorRepository` adapter wraps LanceDB:** All vector operations (store, search, delete) go through a single adapter module in `infrastructure/`. Swapping LanceDB for another vector store requires changing only this module.

- **`DocumentRepository` adapter wraps DuckDB:** All document metadata operations go through a single adapter module. The full power of SQL is available for status queries, batch operations, and reporting.

- **Future `GraphRepository` adapter can use DuckDB tables:** DuckDB's recursive CTEs support graph traversal (e.g., "find all documents linked to X within 3 hops"). If graph query requirements grow beyond what recursive CTEs can express, migration to DuckPGQ (DuckDB's property graph extension) is a natural evolution within the same database.

- **Schema migration strategy needed for both:** Both databases will evolve as features are added. A lightweight migration system (versioned SQL scripts for DuckDB, schema evolution for LanceDB) must be implemented before v1.0.

- **No cross-database joins:** Queries that combine vector similarity with complex metadata filtering must be implemented as two-step operations — search vectors in LanceDB, then enrich/filter results in DuckDB. This is acceptable for the expected query patterns.
