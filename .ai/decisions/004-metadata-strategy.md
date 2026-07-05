# ADR-004: Metadata Strategy

**Status:** Accepted
**Date:** 2026-07-05
**Deciders:** Architecture Team

## Context

LKE generates metadata for documents during indexing — tags, summaries, topic classifications, and processing state. This metadata must be stored and surfaced in a way that satisfies several competing constraints:

1. **Obsidian compatibility:** The first client is Obsidian, which reads metadata from YAML frontmatter in Markdown files. For LKE-generated metadata to be visible in Obsidian (e.g., in search, Dataview queries, graph view), it must be written to frontmatter.

2. **User data safety:** Users maintain their own frontmatter fields (tags, aliases, custom properties). LKE must never overwrite, modify, or delete user-authored metadata. Corruption of user files is unacceptable.

3. **Separation of concerns:** Some metadata is user-facing (tags, summaries) and benefits from being in the document itself. Other metadata is system-internal (content hashes, embedding IDs, processing timestamps) and has no business in user files.

4. **Self-write detection:** If LKE writes to a file that is being watched for changes, the file watcher must not re-trigger processing for LKE's own writes.

## Decision

### Two-Tier Metadata Storage

**Tier 1 — User-visible metadata in YAML frontmatter:**

LKE writes user-facing metadata directly to YAML frontmatter in Markdown files, using a consistent `lke_` prefix to namespace all generated fields:

```yaml
---
title: My Document
tags: [personal, important]          # User-authored — NEVER touched
lke_tags: [knowledge-management, pkm]  # LKE-generated
lke_summary: "Overview of PKM strategies and tools"
lke_topics: [productivity, note-taking]
---
```

**Tier 2 — Internal metadata in DuckDB:**

System-internal metadata is stored exclusively in DuckDB:

- Content hash (SHA-256)
- Processing status (`PENDING`, `PROCESSING`, `COMPLETE`, `PARTIAL`, `ERROR`)
- Error messages and error category
- Last processed timestamp
- Embedding chunk count and IDs
- Source-specific configuration

### Protected Fields

User-authored frontmatter fields are never overwritten. A configurable `protected_fields` list defines fields that LKE must not modify. By default, this includes:

- `title`, `tags`, `aliases`, `cssclasses`, `publish`, `date`, `created`, `modified`
- Any field not prefixed with `lke_`

The protection rule is simple: **LKE only writes fields prefixed with `lke_`**. All other fields are read-only.

### Atomic Writes

All frontmatter modifications use atomic write operations:

1. Read the original file and parse frontmatter.
2. Compute the updated frontmatter (adding/updating only `lke_` fields).
3. Write the complete file to a temporary file in the same directory.
4. Rename the temporary file to the original filename (atomic on POSIX systems).

This ensures that a crash or interruption during write cannot leave a file in a corrupted state — the file either has the old content or the new content, never a partial write.

### Self-Write Detection

When LKE modifies a file's frontmatter, the file watcher must not re-trigger processing. Detection uses content hashing:

1. Before writing, LKE records the expected content hash of the new file.
2. When the file watcher detects a change, it computes the content hash.
3. If the hash matches the expected hash from a recent LKE write, the event is suppressed.

## Alternatives Considered

1. **Sidecar files (`.lke.yaml`)** — Store all LKE metadata in a companion file next to each document (e.g., `note.md` → `note.lke.yaml`). This is the safest option — LKE never touches user files. However, sidecar files are invisible to Obsidian (they don't appear in search, Dataview, or graph view), create file clutter (doubling the number of files in a vault), and complicate backup/sync (users must know to include `.lke.yaml` files).

2. **Frontmatter without prefix** — Write LKE metadata using standard field names (`tags`, `summary`) instead of prefixed names. This maximizes Obsidian compatibility (native tag support) but creates an unacceptable collision risk. If a user has a `summary` field and LKE overwrites it, user data is lost.

3. **All metadata in DuckDB only** — Store everything in the database and never modify user files. This is the safest approach for file integrity, but Obsidian cannot query DuckDB. Users would see no benefit from LKE's metadata generation unless they use the CLI or a future Obsidian plugin.

4. **Obsidian plugin to read sidecar files** — Combine sidecar storage with an Obsidian plugin that reads `.lke.yaml` files and surfaces metadata in the UI. This adds a client-side dependency (users must install and maintain the plugin), couples LKE to Obsidian's plugin API (which changes between versions), and delays the time to value — metadata is invisible until the plugin is built and installed.

## Trade-offs

- **Frontmatter modification carries corruption risk:** Writing to user files is inherently riskier than writing only to a database. A bug in the YAML serializer, an unexpected frontmatter format, or a race condition with another tool could corrupt a file. This risk is mitigated by atomic writes (no partial writes), content hash verification (detect unexpected changes), and the `lke_` prefix (isolate LKE fields from user fields). The risk is further reduced by the fact that LKE only appends/updates fields — it never removes or restructures existing frontmatter.

- **`lke_` prefix reduces Obsidian native integration:** Obsidian's built-in tag system reads from the `tags` field, not `lke_tags`. Users must use Dataview or custom queries to access `lke_`-prefixed fields. This is a deliberate trade-off — the prefix guarantees safety at the cost of some native integration. A future Obsidian plugin could bridge this gap.

- **Two storage locations for metadata:** Splitting metadata between frontmatter and DuckDB means there is no single source of truth for all document metadata. This is managed by clear ownership: frontmatter owns user-visible metadata, DuckDB owns system-internal metadata. The `lke_` prefix makes the boundary unambiguous.

## Consequences

- **`OutputWriter` must implement atomic writes:** The infrastructure layer's file writer must use the temp-file-then-rename pattern for all frontmatter modifications. This is a hard requirement, not an optimization.

- **File watcher must detect self-writes:** Without self-write detection, modifying a file's frontmatter triggers re-indexing, which modifies the frontmatter again, creating an infinite loop. The content hash mechanism prevents this.

- **Protected fields list is configurable per source:** Different knowledge base tools use different frontmatter conventions. The `protected_fields` list can be customized per source type in the TOML configuration, allowing users to add tool-specific fields that LKE should never touch.

- **YAML frontmatter parser must be robust:** The parser must handle all valid YAML frontmatter formats, including multiline strings, nested objects, and non-standard delimiters. It must preserve formatting, comments, and field order as much as possible to minimize diff noise in version-controlled vaults.

- **Future Obsidian plugin opportunity:** The `lke_` prefix creates a clean integration point for a future Obsidian plugin that reads `lke_`-prefixed fields and surfaces them in the native UI (e.g., showing `lke_tags` alongside user tags, displaying `lke_summary` in a sidebar panel).
