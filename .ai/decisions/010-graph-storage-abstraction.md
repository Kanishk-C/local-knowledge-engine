# ADR-010: Graph Storage Abstraction

**Status:** Accepted
**Date:** 2026-07-05
**Deciders:** Architecture Team

## Context

The knowledge graph is a planned feature for the Local Knowledge Engine that will enable relationship-based navigation of personal knowledge — traversing connections between entities (people, concepts, projects, tools) extracted from documents. This feature is **deferred to post-MVP (v0.2.0+)**, but the architecture must accommodate it without requiring invasive refactoring later.

Multiple graph storage backends are viable:

| Backend | Type | Maturity | License | Embedded? |
|---|---|---|---|---|
| DuckDB + recursive CTEs | Relational with graph queries | Stable | MIT | Yes |
| DuckDB + DuckPGQ | Graph extension for DuckDB | Community extension, pre-1.0 | MIT | Yes |
| LadybugDB (KùzuDB successor) | Embedded graph database | <1 year old | MIT | Yes |
| NetworkX | In-memory graph library | Stable | BSD | Yes (no persistence) |
| Neo4j | Client-server graph database | Stable | GPLv3 / Commercial | No (JVM server) |
| SQLite + recursive CTEs | Relational with graph queries | Stable | Public domain | Yes |

The choice of backend has significant implications for deployment complexity, performance characteristics, and long-term maintenance.

## Decision

### Define the Protocol Now, Implement Later

Define a `GraphRepository` Protocol in the domain layer in **v0.1.0**. Do **NOT** implement it in v0.1.0.

The Protocol defines the following operations:

| Method | Signature | Purpose |
|---|---|---|
| `add_entity` | `(entity: Entity) -> None` | Store an extracted entity |
| `add_relationship` | `(relationship: Relationship) -> None` | Store a relationship between two entities |
| `get_neighbors` | `(entity_id: str, depth: int = 1) -> list[Entity]` | Traverse the graph from a node |
| `get_relationships` | `(entity_id: str) -> list[Relationship]` | Get all relationships for an entity |
| `find_path` | `(source_id: str, target_id: str, max_depth: int = 3) -> list[Entity] | None` | Find a path between two entities |
| `delete_by_document` | `(document_id: str) -> None` | Remove all entities and relationships sourced from a document |

### First Implementation: DuckDB with Recursive CTEs

When graph features are implemented (v0.2.0+), the first adapter will use **DuckDB with standard SQL recursive CTEs**. This approach:

- Uses standard SQL that any relational database supports — no proprietary extensions.
- Leverages the existing DuckDB dependency (already used for metadata storage).
- Requires no additional infrastructure or dependencies.
- Is well-understood and debuggable with standard SQL tools.

The schema uses four tables:

- `entities` — extracted entities with type, name, and properties.
- `relationships` — directed edges between entities with relationship type and properties.
- `document_entities` — join table linking entities to their source documents (for `delete_by_document`).
- `documents` — already exists for document metadata.

Graph traversal uses recursive CTEs with a **maximum depth of 3** to prevent runaway queries on densely connected graphs.

### DuckPGQ Evaluation Deferred

DuckPGQ (the Property Graph Query extension for DuckDB) is a promising technology that would provide native graph query syntax (SQL/PGQ) within DuckDB. However, it is currently a community extension that has not reached v1.0. It may break on DuckDB upgrades, and its API may change.

DuckPGQ will be evaluated when it reaches v1.0 stability. If adopted, it replaces the recursive CTE implementation — a single module swap behind the `GraphRepository` Protocol.

## Alternatives Considered

### 1. DuckPGQ from Day One

Use the DuckDB Property Graph Query extension for native graph operations.

**Rejected because:**
- Community extension, not part of DuckDB core. Version compatibility is not guaranteed across DuckDB upgrades.
- Pre-1.0 software with potential breaking API changes.
- Adds a dependency on extension availability and installation mechanics.
- Recursive CTEs provide equivalent functionality for the traversal depths LKE requires (≤3 hops).

### 2. LadybugDB (KùzuDB Successor)

Use a dedicated embedded graph database.

**Rejected because:**
- Less than 1 year old. Risk of abandonment or major API changes.
- Adds another embedded database dependency alongside LanceDB and DuckDB.
- The community and ecosystem are too young to rely on for a production tool.
- Does not provide sufficient advantage over DuckDB recursive CTEs for the query patterns LKE uses.

### 3. Neo4j

Use the industry-standard graph database.

**Rejected because:**
- Requires a JVM server process — contradicts the local-first, embedded architecture.
- GPLv3 license for the community edition, which has copyleft implications.
- Massive deployment complexity increase for a knowledge management CLI tool.
- Network round-trips to a separate server process for every graph query.

### 4. NetworkX

Use Python's standard graph analysis library.

**Rejected because:**
- In-memory only — no built-in persistence. Would require serialization to/from disk.
- Memory-bound — large knowledge graphs would consume significant RAM.
- Excellent for graph algorithms (shortest path, centrality) but not a database.
- Could be used as a complementary analysis tool on top of persisted graph data.

### 5. No Abstraction, Decide Later

Skip the Protocol definition and choose a backend when graph features are built.

**Rejected because:**
- Risks coupling application logic to a specific backend during implementation.
- Without a Protocol, the first implementation becomes the de facto interface, making migration costly.
- Defining the Protocol now costs almost nothing (a single file with method signatures) and prevents architectural debt.

## Trade-offs

| Aspect | Define Protocol Now | No Protocol |
|---|---|---|
| **Upfront cost** | Minimal (one Protocol definition file) | Zero |
| **Architectural debt** | Prevented | Accumulated |
| **Implementation flexibility** | Backend is swappable via adapters | First implementation becomes the interface |
| **Premature abstraction risk** | Low (Protocol is based on well-understood graph operations) | None |
| **Code in v0.1.0** | Protocol definition with no implementation | Nothing |

Defining the Protocol now is a near-zero-cost decision that preserves maximum flexibility for the implementation phase.

## Consequences

1. **Domain layer has a `GraphRepository` Protocol** with no implementation in v0.1.0. It is a documented architectural contract.
2. **No graph features are available** in v0.1.0. Entity extraction, relationship storage, and graph traversal are post-MVP features.
3. **Post-MVP (v0.2.0+)**, the DuckDB adapter implements `GraphRepository` using the `entities`, `relationships`, `document_entities`, and `documents` tables with recursive CTEs for traversal (max depth 3).
4. **If DuckDB recursive CTE performance is insufficient** for large graphs (>100K entities), DuckPGQ or a dedicated graph database can be swapped in behind the Protocol with no changes to the application or domain layers.
5. **`delete_by_document`** ensures that re-indexing a document cleanly removes its old graph data before inserting new data, maintaining graph consistency.
6. **The Protocol is part of the public API** from v0.1.0. Future plugin authors can implement custom graph backends (e.g., a Neo4j adapter for users who run Neo4j) by satisfying the Protocol contract.
