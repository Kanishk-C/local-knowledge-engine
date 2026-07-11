# Local Knowledge Engine (LKE) User Guide

## 1. Overview

The Local Knowledge Engine (LKE) is a CLI-based semantic search engine designed specifically for local Markdown vaults (like Obsidian). It parses your local notes, generates vector embeddings using a local LLM provider, and enables high-speed semantic search over your personal knowledge base.

LKE is built for maximum privacy and local-first workflows—there are no cloud dependencies, API keys, or external data processing involved.

**What LKE does NOT do (yet):**
- Does not generate answers or perform Retrieval-Augmented Generation (RAG).
- Does not watch your file system for live changes.
- Does not serve an HTTP API.
- It is strictly a CLI utility for indexing and semantic search.

---

## 2. Installation & Setup

### Prerequisites

LKE requires a local Python environment and a running instance of [Ollama](https://ollama.com/) to generate embeddings.

1. **Python:** Version 3.10+ (managed via `uv` or standard `pip`).
2. **Ollama:** Must be running locally on `http://localhost:11434`.
3. **Embedding Model:** LKE defaults to `nomic-embed-text`. You must pull this model before initializing LKE.

Run the following command to pull the required model:
```bash
ollama pull nomic-embed-text
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
**Output:**
```text
✓ Configuration
✓ Ollama
✓ Embedding Model (nomic-embed-text)
✓ LanceDB
✓ Repository Schema
✓ Storage (.lke/vectors.lance)

╭───────────────────────────────╮
│ LKE is initialized and ready! │
╰───────────────────────────────╯
```

**What happens on initialization:**
LKE verifies that Ollama is running and the specified embedding model is available. It then provisions a hidden `.lke/` directory in your current working directory.
- `.lke/vectors.lance/` - The LanceDB database that stores your vector embeddings.
- `.lke/metadata.json` - Tracks the SHA256 hashes of your indexed files to enable high-speed incremental indexing.

---

## 3. Configuration Reference

LKE can be configured using a `lke.toml` file (if provided) or by setting environment variables formatted as `LKE_SECTION__KEY`.

### Defaults and Overrides

| Setting | Default Value | Environment Variable | Description |
| :--- | :--- | :--- | :--- |
| **Embeddings Model** | `nomic-embed-text` | `LKE_EMBEDDINGS__MODEL_NAME` | The model used via Ollama. |
| **Embedding Dims** | `768` | `LKE_EMBEDDINGS__EMBEDDING_DIMENSIONS` | Must strictly match the model's native dimensions. |
| **Chunk Size** | `512` | `LKE_EMBEDDINGS__CHUNK_SIZE` | Max characters per document chunk. |
| **Chunk Overlap** | `50` | `LKE_EMBEDDINGS__CHUNK_OVERLAP` | Character overlap between chunks. |
| **Batch Size** | `32` | `LKE_EMBEDDINGS__BATCH_SIZE` | How many chunks to embed concurrently. |
| **Ollama URL** | `http://localhost:11434` | `LKE_AI_PROVIDER__BASE_URL` | Local Ollama endpoint. |
| **Top K Results** | `5` | `LKE_SEARCH__TOP_K` | Number of default search results. |
| **Min Similarity** | `0.75` | `LKE_SEARCH__MIN_SIMILARITY` | Minimum semantic match score (0.0 to 1.0). |

> [!WARNING]
> **Embedding Dimensions Mismatch**  
> If you change the `MODEL_NAME` to a model with a different output dimension (e.g., `all-minilm` uses 384 dimensions), you **must** update `EMBEDDING_DIMENSIONS` accordingly. If the dimensions do not match, LanceDB will throw a schema validation error during indexing.

---

## 4. Command Reference

### `lke init`
Validates the environment, verifies Ollama connectivity, checks model availability, and creates the required database tables.

```bash
uv run lke init
```
_Options:_
- `--help`: Show help and exit.

### `lke index`
Parses, chunks, and embeds markdown documents found in a specific directory or file, then stores them in LanceDB.

```bash
uv run lke index [PATH]
```
_Example Invocation:_
```bash
uv run lke index --verbose /path/to/my/vault
```
_Example Output:_
```text
Parsed /path/to/my/vault/doc1.md
Skipped /path/to/my/vault/doc2.md (content unchanged)
Indexing Vault ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 2/2 documents 0:00:00

      Index Complete      
Metric             ┃ Value
━━━━━━━━━━━━━━━━━━━╇━━━━━━
Documents Indexed  │ 2    
Chunks Generated   │ 5    
Embeddings Created │ 5    
Duration           │ 0.6 s
Failures           │ 0    
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
_Example Invocation:_
```bash
LKE_SEARCH__MIN_SIMILARITY=0.5 uv run lke search "local embeddings"
```
_Example Output:_
```text
╭──────────────────────────────────────────────────────────────────────────────╮
│                                                                              │
│  67%                                                                         │
│                                                                              │
│  Source                                                                      │
│  /path/to/my/vault/doc2.md                                                   │
│                                                                              │
│  Preview                                                                     │
│  Ollama provides local embeddings.                                           │
│                                                                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```
_Options:_
- `--top-k`: Number of results to return (default: `5`).

---

## 5. How Incremental Indexing Works

To keep indexing extremely fast, LKE uses an incremental approach based on **content hashing**, rather than file modification times (which can be unreliable with sync tools).

When you run `lke index`:
1. **Unchanged files:** LKE calculates the SHA256 hash of the file's contents. If it matches the hash stored in `.lke/metadata.json`, the file is entirely **skipped**.
2. **Modified files:** If the hash differs, LKE removes the old chunks from LanceDB and fully re-embeds the new contents of the file.
3. **Deleted files:** If a file exists in the metadata but is no longer on disk, LKE purges all of its orphaned chunks from the vector database.
4. **Renamed files:** LKE treats renames as a file deletion (of the old name) and a file addition (of the new name). **Note:** This means renaming a file will trigger a full re-computation of its embeddings.

By adding the `--verbose` flag, LKE will explicitly tell you which files were skipped due to unchanged contents.

---

## 6. Feature Matrix

| Feature | Status | Description |
| :--- | :--- | :--- |
| **Ollama Integration** | Available | Complete local embedding generation using `nomic-embed-text`. |
| **Vector Storage** | Available | LanceDB-backed local vector storage. |
| **Incremental Indexing** | Available | SHA256 hash-based skip logic to safely re-run index operations. |
| **Semantic Search** | Available | Cosine-similarity searches over document chunks. |
| **Markdown Parsing** | Available | Recursively reads `.md` and `.txt` files. |
| **Watch Mode** | Planned | Automatically index files when they change on disk. |
| **Generative RAG** | Planned | Use an LLM to generate conversational answers based on search results. |
| **DuckDB Analytics** | Planned | Relational database to perform SQL queries over vault metadata. |
| **API Endpoints** | Planned | HTTP API to interact with the engine from other apps. |

---

## 7. Troubleshooting

### "Model is not pulled" during `lke init`
**Symptom:** `✗ Ollama - Reason: Model 'nomic-embed-text' is not pulled.`  
**Cause:** The configured model has not been downloaded to your local Ollama instance.  
**Fix:** Run `ollama pull nomic-embed-text` in your terminal. If using a different model, pull that one instead.

### "No matching documents were found" during `lke search`
**Symptom:** The search command runs successfully but returns a prompt stating no documents matched.  
**Cause:** By default, LKE requires a strict 75% semantic match (`min_similarity = 0.75`). Short queries or dissimilar content may fall below this threshold.  
**Fix:** Lower the similarity threshold temporarily using an environment variable:
`LKE_SEARCH__MIN_SIMILARITY=0.5 uv run lke search "your query"`

### Schema dimension mismatch errors
**Symptom:** Indexing crashes with a LanceDB/PyArrow schema error mentioning vector dimensions.  
**Cause:** You changed `LKE_EMBEDDINGS__MODEL_NAME` to a model with a different output dimension (e.g. `all-minilm`), but LanceDB was initialized with the default 768 dimensions.  
**Fix:** Set `LKE_EMBEDDINGS__EMBEDDING_DIMENSIONS=384` (or whatever matches your model). Note: If you change dimensions, you **must delete the `.lke` directory** and run `lke init` and `lke index` again from scratch, as LanceDB cannot alter vector dimensions after the table is created.

---

## 8. Architecture Overview

LKE strictly follows Clean Architecture principles, ensuring a pure domain model completely decoupled from framework or infrastructure dependencies. The `typer` CLI acts merely as a thin presentation layer, communicating with orchestrating Application Services (like the `IndexingPipeline`). These in turn rely on Infrastructure adapters (like the `OllamaProvider` and `LanceDBRepository`) which conform strictly to interfaces defined in the Domain. For full technical details on this architecture, please refer to the engineering documentation in the `.ai/` and `.agent/` folders.
