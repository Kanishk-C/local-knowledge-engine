# Local Knowledge Engine (LKE) User Guide

Local Knowledge Engine (LKE) is an AI-powered semantic search and Retrieval-Augmented Generation (RAG) tool designed specifically for local markdown vaults. It works offline, keeping your knowledge completely private.

## Quick Start

LKE is a local-first Python CLI application. The recommended way to install and run it globally without polluting your system Python is via `uv` or `pipx`.

```bash
# Clone the repository
git clone <repository_url> local_knowledge_engine
cd local_knowledge_engine

# Install globally using uv (recommended)
uv tool install .

# Or install globally using pipx
pipx install .
```

Initialize your vault (creates `.lke/` directory and verifies dependencies like Ollama):
```bash
lke init
```

Index your markdown files:
```bash
lke index
```

Ask a question:
```bash
lke ask "What is my vault about?"
```

---

## Configuration

LKE is configured via a `config.json` file inside your `.lke/` directory. If it doesn't exist, LKE relies on strict defaults. 

Below is the exhaustive list of configuration properties, directly reflecting the current system:

| Section | Field | Type | Default | Description |
|---|---|---|---|---|
| **logging** | `level` | string | `"INFO"` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| **logging** | `file_path` | string / null | `null` | Path to log file (`null` prints to stdout). |
| **logging** | `retention` | string | `"7 days"` | Log file retention policy. |
| **embeddings** | `model_name` | string | `"nomic-embed-text"` | Ollama embedding model to use. |
| **embeddings** | `embedding_dimensions` | int | `768` | Dimensions of the selected embedding model. |
| **embeddings** | `chunk_size` | int | `512` | Characters per semantic chunk. |
| **embeddings** | `min_chunk_size` | int | `100` | Minimum characters to retain a chunk. |
| **embeddings** | `chunk_overlap` | int | `50` | Overlap between sequential chunks. |
| **embeddings** | `batch_size` | int | `32` | Number of chunks to embed concurrently. |
| **ai_provider** | `base_url` | string | `"http://localhost:11434"` | Ollama API endpoint. |
| **ai_provider** | `timeout_seconds` | int | `30` | Request timeout for Ollama calls. |
| **ai_provider** | `max_retries` | int | `3` | Maximum retry attempts for failed AI calls. |
| **parsing** | `supported_extensions` | list[str] | `[".md", ".txt"]` | File types tracked by LKE. |
| **parsing** | `exclude_patterns` | list[str] | `[".git", "node_modules"]` | Directory patterns to ignore. |
| **search** | `top_k` | int | `5` | Maximum results returned during semantic search. |
| **search** | `min_similarity` | float | `0.50` | Relevance threshold for search results (see Limitations). |
| **search** | `max_results` | int | `10` | Hard cap on total search results queried. |
| **enrichment**| `generation_model` | string | `"llama3.2"` | Model used for tags/folders generation. |
| **enrichment**| `max_new_tags_per_note`| int | `1` | Max new tags to suggest per note. |
| **enrichment**| `max_new_folders_per_note`| int | `1` | Max new folders to suggest per note. |
| **enrichment**| `related_notes_threshold`| float | `7.5` | Threshold for cross-encoder related note links. |
| **enrichment**| `related_notes_max` | int | `5` | Maximum related notes to link. |
| **enrichment**| `auto_file_enabled` | bool | `false` | If true, LKE will automatically move files into folders. |
| **rag** | `top_k` | int | `3` | Maximum contexts injected into the LLM prompt. |
| **rag** | `generation_model` | string | `"llama3.2"` | Model used for RAG synthesis. |
| **rag** | `system_prompt` | string | *See models.py* | Instructions enforcing grounded answers. |
| **watcher** | `enabled` | bool | `false` | Whether filesystem watching is active. |
| **watcher** | `debounce_seconds` | float | `1.0` | Debounce window for rapid filesystem events. |
| **api** | `host` | string | `"127.0.0.1"` | Host address for the API server. |
| **api** | `port` | int | `8000` | Port for the API server. |
| **paths** | `vector_db` | string | `".lke/vectors.lance"` | LanceDB vector database location. |
| **paths** | `metadata_file` | string | `".lke/metadata.json"` | JSON metadata tracking location. |
| **paths** | `cache_dir` | string | `".lke/cache"` | Caching directory. |

---

## CLI Command Reference

All commands support `--verbose` (`-v`), `--json-logs`, and `--help`.

### `lke init`
Initialize and validate the LKE environment. 
Ensures Ollama is reachable and required models are pulled.

### `lke index [PATH]`
Parse and embed documents into the vault.
- `[PATH]`: Directory to index (default: `.`)
- `--verbose`: Display detailed per-file progress.
- `--dry-run`: Execute without writing to the database.

### `lke search <query>`
Search indexed documents using semantic similarity.
- `<query>`: The semantic search query (required).
- `--top-k`: Number of results to return (default: `5`).

### `lke ask <query>`
Ask a question and get a synthesized answer based on your vault.
- `<query>`: The natural language question to ask (required).

### `lke enrich [PATH]`
Enrich documents with AI metadata (tags, folders, summary).
- `[PATH]`: Directory to enrich (default: `.`)
- `--verbose`: Display detailed per-file progress.
- `--dry-run`: Simulate enrichment without modifying files.

### `lke watch [PATH]`
Watch a vault for changes and process them automatically.
- `[PATH]`: Directory to watch for changes (default: `.`)
- `--verbose`: Display detailed per-file progress.

### `lke eval`
Evaluate search and retrieval quality against the adversarial test corpus.
- `--dataset`, `-d`: Path to evaluation dataset YAML.
- `--corpus`, `-c`: Path to evaluation corpus directory (default: `tests/eval/corpus`).
- `--threshold`, `-t`: Minimum required Mean Recall@K for the evaluation to pass (default: `0.5`).
- `--mode`, `-m`: Evaluation mode: `search`, `related-notes`, or `rag` (default: `search`).
- `--verbose`, `-v`: Print detailed results per query.

### `lke serve`
Start the REST API server locally on `127.0.0.1:8000`.

---

## API Reference

LKE provides a local stateless REST API to integrate vault searching into bespoke UIs, tools, or scripts. The API server runs at `http://127.0.0.1:8000` by default.

### `POST /api/search`
Perform a semantic search over your indexed documents.

**Request Schema:**
```json
{
  "query": "string (required) - The semantic search query.",
  "top_k": "integer (optional) - Number of results to return. Default is 5."
}
```

**Example Request:**
```bash
curl -X POST http://127.0.0.1:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "quantum computing", "top_k": 2}'
```

**Example Response:**
```json
{
  "results": [
    {
      "chunk_id": "/path/to/vault/gpu_arch.md:0",
      "document_id": "/path/to/vault/gpu_arch.md",
      "content": "# GPU Architecture\nGraphics Processing Units (GPUs) are designed for parallel processing...",
      "score": 0.5389868449966139,
      "metadata": {
        "heading_level": 1,
        "token_count": 55,
        "section_index": 0,
        "is_split": false,
        "source_path": "/path/to/vault/gpu_arch.md",
        "heading_path": [
          "GPU Architecture"
        ],
        "start_offset": 0,
        "end_offset": 217
      }
    }
  ]
}
```

### `POST /api/ask`
Submit a natural language question and receive a RAG-synthesized answer grounded strictly in your vault context.

**Request Schema:**
```json
{
  "query": "string (required) - The natural language question to ask."
}
```

**Example Request:**
```bash
curl -X POST http://127.0.0.1:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What is java?"}'
```

**Example Response:**
```json
{
  "answer": "Java is a robust, highly structured object-oriented programming language consumed daily by millions of developers to keep complex enterprise codebases running smoothly.",
  "sources": [
    {
      "chunk_id": "/path/to/vault/java_lang.md:0",
      "document_id": "/path/to/vault/java_lang.md",
      "content": "# Java\nJava is consumed daily by millions of developers. It is robust, highly structured, and provides the necessary object-oriented syntax...",
      "score": 0.6444283801421665,
      "metadata": {
        "heading_level": 1,
        "token_count": 83,
        "section_index": 0,
        "is_split": false,
        "source_path": "/path/to/vault/java_lang.md",
        "heading_path": [
          "Java"
        ],
        "start_offset": 0,
        "end_offset": 330
      }
    }
  ]
}
```

---

## Known Limitations

This project has been extensively verified against an adversarial evaluation corpus. Users should be fully aware of the following hard limits in the current system:

1. **RAG Deterministic Short-Circuit Scope:** 
   LKE features a deterministic safety short-circuit that returns "I don't know" *only* when the vector search yields strictly zero results. However, because `min_similarity` defaults to a loose `0.50`, even short nonsense strings (e.g. `"qweqweqwe"`) can clear the threshold. Consequently, the true zero-source case is exceedingly rare. Any low-relevance-but-present sources are passed to the LLM, meaning you still heavily depend on the LLM to follow the system prompt and filter out hallucinations. This has been proven unreliable in some cases.
2. **RAG Baseline Accuracy:** 
   In the adversarial eval corpus, RAG baseline accuracy is currently 5/13 (38.5%). Failures fall into three categories: 
   - *Contamination:* Wrong context blended in (e.g. mixing up `java-software` and `java-coffee`).
   - *Recall Failure:* Relevant content exists but isn't retrieved (suppressed by strict thresholds).
   - *Answer Completeness:* Correct context is fetched, but the model answers tersely rather than exhaustively.
3. **Related Notes Disabled by Default:** 
   The related-notes feature (using cross-encoders) is effectively disabled by default. The threshold (`7.5`) was tuned specifically to completely eliminate false positives in an adversarial environment, at the accepted cost of virtually destroying recall.
4. **Watch Mode Has No Initial Catch-Up Pass:**
   Watch mode does not perform an initial sync pass on startup. Files modified while `lke watch` wasn't running require a manual `lke index` + `lke enrich` run.
5. **Watch Mode Startup Reconciliation:**
   If an auto-file move crashes mid-sequence (move succeeded, but database re-keying failed), the file's entry becomes orphaned until manually fixed. There is no automatic startup reconciliation.
6. **Rename Handling:** 
   Renamed files are treated by the watcher purely as a `delete` followed by an `add`, meaning any rename triggers full re-embedding rather than a cheap metadata pointer update.
