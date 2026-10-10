# Local Knowledge Engine (LKE)

A local-first journal and knowledge base for plain Markdown vaults (such as Obsidian). Nothing leaves your machine.

LKE has two layers:

- **Journal core (default, about 19 MB installed):** daily notes, quick capture, instant full-text search, and timelines for people and events through `[[links]]`. It uses only Python plus SQLite and needs no AI or background service.
- **AI layer (optional `ai` extra):** semantic search, `ask` (RAG over your notes), auto-tagging and watch mode, using a local [Ollama](https://ollama.com/).

Your notes stay ordinary `.md` files. LKE's index (`<vault>/.lke/journal.db`) is a disposable cache that rebuilds itself automatically.

## Quick Start (journal)

```bash
git clone <repository_url> local_knowledge_engine
uv tool install ./local_knowledge_engine        # or: pipx install ./local_knowledge_engine

mkdir -p ~/.config/lke
cat > ~/.config/lke/config.toml <<'TOML'
[journal]
vault_path = "~/Obsidian/MyVault"
daily_folder = "journal"
daily_format = "%Y/%Y-%m-%d"   # -> journal/2026/2026-10-10.md
open_with = "obsidian"         # print | editor | obsidian
TOML
```

```bash
lke today                         # create/open today's note
lke log "Lunch with [[Alice]], planning [[Goa trip]]"   # timestamped line in today's note
lke find dentist                  # full-text search (dent* for prefixes, --tag health)
lke who Alice                     # every note that mentions Alice, newest first (--unlinked too)
lke links --folder people         # who you mention most, and when you last did
lke day yesterday                 # read a day's entry (today, yesterday, -7, 2025-10-10)
lke onthisday                     # this date in previous years
```

## AI layer (optional)

```bash
uv tool install './local_knowledge_engine[ai]'   # adds LanceDB, Ollama client, PyTorch (several GB)
ollama pull nomic-embed-text && ollama pull llama3.2
lke init && lke index ~/Obsidian/MyVault
lke ask "When did I last talk to Alice about the trip?"
```

Use the `api` extra for `lke serve`. See the [User Guide](docs/user_guide.md) for every command and setting.
