# Local Knowledge Engine (LKE) User Guide

## 1. Overview

The Local Knowledge Engine (LKE) is a CLI-based semantic search engine designed specifically for local Markdown vaults (like Obsidian). It parses your local notes, generates vector embeddings using a local LLM provider, and enables high-speed semantic search over your personal knowledge base.

LKE is built for maximum privacy and local-first workflows—there are no cloud dependencies, API keys, or external data processing involved.

**What LKE does:**
- Indexes Markdown and text files into a LanceDB vector database.
- Provides high-speed semantic search.
- Watches your file system for live changes and auto-indexes them.
- Enriches notes with AI-generated summaries and tags.
- Can automatically reorganize and physically move your notes into topical folders based on AI classification.

**What LKE does NOT do (yet):**
- Does not generate conversational answers or perform Retrieval-Augmented Generation (RAG).
- Does not serve an HTTP API.

---

## 2. Installation & Setup

### Prerequisites

LKE requires a local Python environment and a running instance of [Ollama](https://ollama.com/) to generate embeddings and run AI enrichment.

1. **Python:** Version 3.14+ (or compatible versions per your environment setup).
2. **Ollama:** Must be running locally on `http://localhost:11434`.
3. **Models:** LKE defaults to `nomic-embed-text` for embeddings and `llama3.2` for text generation/enrichment. You must pull these models before initializing LKE.

Run the following command to pull the required models:
```bash
ollama pull nomic-embed-text
ollama pull llama3.2
```

### Installation

1. Clone the repository and navigate into it:
   ```bash
   git clone <repository_url> local_knowledge_engine
   cd local_knowledge_engine
   ```
2. Install dependencies using `uv` (recommended):
   ```bash
   uv sync
   ```

### Initialization

Before you can index or search, you must initialize the LKE environment. 

Run the initialization command:
```bash
uv run lke init
```
**What happens on initialization:**
LKE verifies that Ollama is running and the specified models are available. It then provisions a hidden `.lke/` directory in your current working directory.
- `.lke/vectors.lance/` - The LanceDB database that stores your vector embeddings.
- `.lke/metadata.json` - Tracks the SHA256 hashes of your indexed files to enable high-speed incremental indexing.
- `.lke/cache/` - Stores cached vocabulary and internal states.

---

## 3. Configuration Reference

LKE can be configured using environment variables formatted as `LKE_SECTION__KEY`.

### Defaults and Overrides

| Setting | Default Value | Environment Variable | Description |
| :--- | :--- | :--- | :--- |
| **Log Level** | `INFO` | `LKE_LOGGING__LEVEL` | One of DEBUG, INFO, WARNING, ERROR, CRITICAL. |
| **Log File Path** | `None` | `LKE_LOGGING__FILE_PATH` | Path to log file (None=stdout). |
| **Log Retention** | `7 days` | `LKE_LOGGING__RETENTION` | Log file retention policy. |
| **Embeddings Model** | `nomic-embed-text` | `LKE_EMBEDDINGS__MODEL_NAME` | The model used for embeddings. |
| **Embedding Dims** | `768` | `LKE_EMBEDDINGS__EMBEDDING_DIMENSIONS` | Must strictly match the model's native dimensions. |
| **Chunk Size** | `512` | `LKE_EMBEDDINGS__CHUNK_SIZE` | Max characters per document chunk. |
| **Min Chunk Size** | `100` | `LKE_EMBEDDINGS__MIN_CHUNK_SIZE` | Minimum characters per document chunk. |
| **Chunk Overlap** | `50` | `LKE_EMBEDDINGS__CHUNK_OVERLAP` | Character overlap between chunks. |
| **Batch Size** | `32` | `LKE_EMBEDDINGS__BATCH_SIZE` | How many chunks to embed concurrently. |
| **Ollama URL** | `http://localhost:11434` | `LKE_AI_PROVIDER__BASE_URL` | Local Ollama endpoint. |
| **Ollama Timeout** | `30` | `LKE_AI_PROVIDER__TIMEOUT_SECONDS` | Timeout for AI provider API calls. |
| **Ollama Retries** | `3` | `LKE_AI_PROVIDER__MAX_RETRIES` | Max retries for AI provider API calls. |
| **Supported Exts** | `[".md", ".txt"]` | `LKE_PARSING__SUPPORTED_EXTENSIONS` | File extensions to index. |
| **Exclude Patterns** | `[".git", "node_modules"]` | `LKE_PARSING__EXCLUDE_PATTERNS` | Ignore patterns. |
| **Top K Results** | `5` | `LKE_SEARCH__TOP_K` | Number of default search results. |
| **Min Similarity** | `0.75` | `LKE_SEARCH__MIN_SIMILARITY` | Minimum semantic match score (0.0 to 1.0). |
| **Max Results** | `10` | `LKE_SEARCH__MAX_RESULTS` | Max results to ever return. |
| **Watcher Enabled**| `False` | `LKE_WATCHER__ENABLED` | Enable watcher daemon by default. |
| **Watcher Debounce** | `2.0` | `LKE_WATCHER__DEBOUNCE_SECONDS` | Seconds to wait before processing file changes. |
| **Generation Model** | `llama3.2` | `LKE_ENRICHMENT__GENERATION_MODEL` | The model used for AI enrichment. |
| **Max New Tags** | `1` | `LKE_ENRICHMENT__MAX_NEW_TAGS_PER_NOTE` | Max new tags to generate per note. |
| **Max New Folders** | `1` | `LKE_ENRICHMENT__MAX_NEW_FOLDERS_PER_NOTE` | Max new folders to generate per note. |
| **Rel Notes Thresh** | `0.55` | `LKE_ENRICHMENT__RELATED_NOTES_THRESHOLD` | Threshold for embedding similarity. |
| **Rel Notes Max** | `5` | `LKE_ENRICHMENT__RELATED_NOTES_MAX` | Max related notes to append. |
| **Auto-File Enabled**| `False` | `LKE_ENRICHMENT__AUTO_FILE_ENABLED` | Whether to automatically move notes into folders based on AI tags. |
| **Vector DB Path** | `.lke/vectors.lance` | `LKE_PATHS__VECTOR_DB` | Path to vector storage. |
| **Metadata File** | `.lke/metadata.json` | `LKE_PATHS__METADATA_FILE` | Path to state tracking file. |
| **Metadata DB** | `.lke/metadata.duckdb` | `LKE_PATHS__METADATA_DB` | Path to DuckDB (deprecated). |
| **Cache Dir** | `.lke/cache` | `LKE_PATHS__CACHE_DIR` | Path to internal cache. |

> [!WARNING]
> **Embedding Dimensions Mismatch**  
> If you change the `MODEL_NAME` to a model with a different output dimension (e.g., `all-minilm` uses 384 dimensions), you **must** update `EMBEDDING_DIMENSIONS` accordingly. If the dimensions do not match, LanceDB will throw a schema validation error during indexing.

---

## 4. Command Reference

### Global Options
These options can be passed to any command (e.g. `lke --verbose index`).
- `--verbose, -v`: Enable debug logging.
- `--json-logs`: Enable structured JSON logging.

### `lke init`
Validates the environment, verifies Ollama connectivity, checks model availability, and creates the required database tables.

### `lke index`
Parses, chunks, and embeds markdown documents found in a specific directory or file, then stores them in LanceDB.

```bash
uv run lke index [PATH]
```
_Options:_
- `[PATH]`: Directory or file to parse. Defaults to current directory (`.`).
- `--force`: Ignore previous hashes and force complete re-indexing.
- `--verbose`: Display detailed per-file output, including showing skipped files.
- `--dry-run`: Parse and chunk, but do not embed or save to the database.

### `lke search`
Queries your indexed documents using semantic similarity.

```bash
uv run lke search "your query here"
```
_Options:_
- `--top-k`: Number of results to return (default: `5`).

### `lke enrich`
Analyzes documents using the generation LLM to extract tags, write summaries, and optionally auto-file the document. 

```bash
uv run lke enrich [PATH]
```
_Options:_
- `--verbose, -v`: Show detailed progress for each file.
- `--dry-run`: Simulate enrichment without modifying files.

### `lke watch`
Runs as a foreground process, actively monitoring the specified vault directory for file creations, modifications, and deletions. Automatically indexes and enriches files as they are saved.

```bash
uv run lke watch [PATH]
```

---

## 5. Feature Deep Dives

### Incremental Indexing
To keep indexing extremely fast, LKE uses an incremental approach based on **content hashing**, rather than file modification times (which can be unreliable with sync tools).

1. **Unchanged files:** LKE calculates the SHA256 hash of the file's contents. If it matches the hash stored in `.lke/metadata.json`, the file is entirely **skipped**.
2. **Modified files:** If the hash differs, LKE removes the old chunks from LanceDB and fully re-embeds the new contents of the file.
3. **Deleted files:** LKE purges all of its orphaned chunks from the vector database.
4. **Renamed files:** LKE treats renames as a file deletion (of the old name) and a file addition (of the new name). This triggers full re-computation of embeddings.

### Watch Mode & Auto-Filing
Watch mode utilizes `watchdog` to continuously listen for filesystem events. 
- It uses a debounce timer (default 2.0 seconds) to bundle rapid saves into a single indexing/enrichment run.
- If **auto-filing** is enabled, the AI will classify your note into an appropriate folder using a dedicated folder vocabulary (which is independent of its tags), and the system will automatically create that folder and move the file there. The watcher explicitly suppresses re-indexing this self-caused move to prevent infinite loops.
- Watch mode gracefully handles Ollama downtime. If the provider is unreachable, it logs a warning, retries the operation, and if it ultimately fails, it drops that single event rather than crashing the entire watcher process. 

---

## 6. Known Limitations (Deferred)

- **DuckDB Removal:** Early plans called for DuckDB metadata tracking, but it was removed in favor of a simpler `metadata.json` + LanceDB approach.
- **Watch Mode Startup Reconciliation:** If an auto-file move crashes mid-sequence (move succeeded, but LanceDB/metadata.json re-keying failed), the file's entry becomes orphaned until manually fixed. There is no automatic startup reconciliation yet to align disk state with metadata.json.
- **Watch Mode Initial Catch-Up:** Watch mode does not perform an initial sync pass on startup. Files modified while `lke watch` wasn't running require a manual `lke index` + `lke enrich` run.
- **Empirically Tuned Relevance Threshold:** The `related_notes_threshold` for enrichment is set at 0.55, which was empirically tuned based on a 10-note sample. This may need adjustment for larger vaults.
- **Rename Handling:** Renamed files are treated as a delete followed by an add, triggering full re-embedding rather than a cheap metadata update.
- **Link Breaking:** Explicit-path embeds and relative links may break when a file is automatically moved by auto-filing. Standard `[[wikilinks]]` are safer.

---

## 7. Feature Matrix

| Feature | Status | Description |
| :--- | :--- | :--- |
| **Ollama Integration** | Available | Local embedding generation and enrichment. |
| **Vector Storage** | Available | LanceDB-backed local vector storage. |
| **Incremental Indexing** | Available | SHA256 hash-based skip logic. |
| **Semantic Search** | Available | Cosine-similarity searches over document chunks. |
| **Markdown Parsing** | Available | Parses `.md` and `.txt` files, updating frontmatter. |
| **AI Enrichment** | Available | Generates summaries, tags, and related notes. |
| **Auto-Filing** | Available | Reorganizes files into semantic folders. |
| **Watch Mode** | Available | Automatically index and enrich files when they change on disk. |
| **Generative RAG** | Planned | Use an LLM to generate conversational answers based on search results. |
| **API Endpoints** | Planned | HTTP API to interact with the engine from other apps. |

---

## 8. Architecture Overview

LKE strictly follows Clean Architecture principles, ensuring a pure domain model completely decoupled from framework or infrastructure dependencies. The `typer` CLI acts merely as a thin presentation layer, communicating with orchestrating Application Services (like the `IndexingPipeline` and `EnrichmentPipeline`). These in turn rely on Infrastructure adapters (like the `OllamaProvider`, `MarkdownFrontmatterWriter`, and `LanceDBRepository`) which conform strictly to interfaces defined in the Domain. 
