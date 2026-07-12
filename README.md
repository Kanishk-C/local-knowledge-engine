# Local Knowledge Engine (LKE)

Local Knowledge Engine (LKE) is an AI-powered semantic search engine designed specifically for local Markdown vaults (like Obsidian). It parses your local notes, generates vector embeddings using a local LLM provider, and enables high-speed semantic search over your personal knowledge base—completely offline and private.

## Quick Start

1. **Prerequisites:** Python 3.14+ and a running [Ollama](https://ollama.com/) instance (`http://localhost:11434`).
2. **Pull Models:**
   ```bash
   ollama pull nomic-embed-text
   ollama pull llama3.2
   ```
3. **Install & Initialize:**
   ```bash
   git clone <repository_url> local_knowledge_engine
   cd local_knowledge_engine
   uv sync
   uv run lke init
   ```
4. **Index & Search:**
   ```bash
   uv run lke index /path/to/your/markdown/vault
   uv run lke search "your search query"
   ```

For advanced features like AI enrichment (auto-tagging, summaries), watch mode, and configuration details, please see the full [User Guide](docs/user_guide.md).
